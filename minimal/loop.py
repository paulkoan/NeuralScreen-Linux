"""The MVP pipeline: capture -> worker (NR pass) -> display.

One frame at a time, strictly paired (send, then wait for that index back).
Pipelining would need a second frame slot in shared memory; the MVP keeps the
simple invariant that the worker is never handed a new frame while it still
owns the previous one.

Motion vectors are zero for now. NGX wants a motion field; feeding it zeros
means "nothing moved", which is correct for a static desktop and correct enough
to prove the pass runs. Real optical flow is a later milestone.
"""

from __future__ import annotations

import queue
import time
from collections import deque
from pathlib import Path

import numpy as np

from minimal.capture import Capture
from minimal.display import Display
from minimal.worker import FLOW_H, FLOW_W, Worker, work_size, worker_timeline

# The profile the MVP runs with, from settings_io.PROFILES["Natural"].
# Duplicated rather than imported so the MVP does not pull in the whole
# settings subsystem (config files, presets, i18n).
DEFAULT_PARAMS = {
    "profile": 1, "preset": 0, "style": 1, "auto_mask": 0, "ui_correction": 0,
    "intensity": 1.00, "local_tone": 1.00, "local_structure": 1.00,
    "skin_structure": -1.0,
}


def _prefetch_stats(capture):
    """`stats()` from the prefetch wrapper, or None for a plain source.

    Duck-typing on a `stats` method was wrong, and it cost a queue run its exit status. The video
    source has stats of its own - frames decoded, loops made - so the summary read them as a drain
    report and died on the missing key at the last line of a run that had already done all 120
    frames and shut its worker down cleanly. Only the wrapper has a drain to report.
    """
    from minimal.prefetch import Prefetch
    if isinstance(capture, Prefetch):
        return capture.stats()
    return None


def _source_stats(capture):
    """The frame source's own report, if it has one: which clip, decoded how many times.

    This is what makes a run's record self-describing. A timing from a file source means nothing
    without knowing which file and how far into it the run got, and a run that looped twice is not
    comparable to one that did not loop at all.
    """
    from minimal.prefetch import Prefetch
    inner = getattr(capture, "source", None) if isinstance(capture, Prefetch) else capture
    fn = getattr(inner, "stats", None)
    return fn() if callable(fn) else None


def _capture_cpu_summary(before: float | None, after: float | None,
                         wall: float, *, supported: bool,
                         pid: int | None = None) -> dict | None:
    """The capture chain's CPU over the run.

    Three outcomes, deliberately distinct:

      None                the source cannot report its own CPU at all. A
                          synthetic source has no chain to measure, and a line
                          about it every run would be noise.
      share is None       the source CAN report it and the reading failed. That
                          is a bug, and saying so is the point: the first
                          version simply omitted the line, which looked exactly
                          like "the chain used no CPU" and cost a round trip to
                          notice.
      otherwise           seconds used, wall clock, and the share of a core.

    No fabricated zeroes anywhere: a zero would read as "the chain did nothing",
    which is the opposite of the case worth knowing about.
    """
    if not supported:
        return None
    if before is None or after is None:
        return {"seconds": None, "wall": wall, "share": None, "pid": pid,
                "reason": "the source reports its own CPU but the reading "
                          "failed — check /proc/<pid>/stat for the pid above"}
    from minimal.cpu import cpu_share

    return {"seconds": after - before, "wall": wall, "pid": pid,
            "share": cpu_share(before, after, wall)}


class Pipeline:
    """Capture a frame, run it through the worker, put the result on screen."""

    def __init__(self, *, monitor: int = 0, params: dict | None = None,
                 fullscreen: bool = False, headless: bool = False,
                 warmup: int = 2, worker_cmd: list[str] | None = None,
                 worker_env_extra: dict | None = None,
                 indicator: bool | None = None,
                 report_diff: bool = False, save_diff: str | None = None,
                 diff_gain: float = 8.0, ab_alternate: float = 0.0,
                 report_gpu: bool = False,
                 worker_cwd: Path | None = None, capture=None, display=None,
                 work_scale: float = 1.0, motion_small: bool = False,
                 no_motion: bool = False, shm: bool = False,
                 motion_guides: bool = False,
                 want_pixels: bool = True,
                 bypass: bool = False, send_ahead: int = 1,
                 frame_timeout: float = 60.0, writev: bool = False,
                 worker_log: bool = False):
        self.params = dict(params or DEFAULT_PARAMS)
        self.warmup = warmup
        self.headless = headless
        # How many frames may be in flight. 1 is the shape the MVP has always
        # had: send a frame, then wait for that frame's result, so every frame
        # pays the worker's whole per-frame time plus the round trip. Measured
        # against the worker fed with no client at all (42.5fps at 1440p against
        # the pipeline's 9.1), the serialisation is most of what the client costs.
        self.send_ahead = max(1, int(send_ahead))
        # How long to wait for a reply before calling it a stall. Not a hang:
        # the run stops and says so.
        self.frame_timeout = float(frame_timeout)
        #: How many times the worker went silent past frame_timeout this run.
        #:
        #: Counted rather than recovered, deliberately. The worker answers in
        #: order, so once a reply is missing every later reply is unattributable:
        #: pairing them anyway would show one frame's result against another
        #: frame's input and call it a measurement. Round 29 caught the worker
        #: stalling for eighteen seconds mid-run, so it does happen.
        self.stalls = 0
        # One scatter-gather write per frame instead of four. See Worker.writev.
        self.writev = bool(writev)
        # Send the motion field at the optical-flow size and let the worker
        # upscale it. Cuts the inbound bytes per frame by nearly half, at no
        # cost to what the network receives — our field is all zeros either way.
        self.motion_small = bool(motion_small)
        self.no_motion = bool(no_motion)
        # Estimate the motion field instead of sending zeros. The estimator is guides.py's
        # TemporalGuideGenerator (DIS optical flow on a downscaled gray frame, with a noise
        # floor so capture jitter does not become motion); it was written and then never
        # wired in, so every measurement so far sent a field of zeros and the port's own
        # reprojection was the identity. A real field is bytes that must go out, so this
        # also turns the no-motion default off for this run.
        self.motion_guides = bool(motion_guides)
        self.guides = None
        if self.motion_guides:
            self.no_motion = False
        self.shm = bool(shm)
        # Whether the caller can use the pixels at all. The worker's reply carries a 14.7MB
        # readback and a 14.7MB write-back when this is set, and 12.8ms of its 37ms frame at
        # 1440p was going into publishing a picture nobody had asked for: minimal never set
        # the wire's WantPixels flag, so every benchmark paid for a channel it ignored. Only
        # ask when something consumes the result - a display to draw or a PNG to write.
        self.want_pixels = bool(want_pixels)

        # Injected sources let the tests drive the loop without a screen or a GPU.
        self.capture = capture if capture is not None else Capture(monitor_idx=monitor)
        #: Whether the source hands us BGRA. It is a property of the source, not
        #: a choice here: mss and PipeWire deliver BGRA, while the synthetic card
        #: and a decoded image are RGBA. The channel order travels with the frame
        #: on the wire (FRAME_FLAG_COLOR_BGRA) and the port's expand shader does
        #: the swizzle on the GPU, so there is no per-frame CPU swap to pay for.
        #: A source that says nothing is RGBA, the historical behaviour.
        self.bgra = bool(getattr(self.capture, "bgra", False))
        self.width, self.height = self.capture.resolution
        # work_scale is the product's own performance dial: the network works on
        # a fraction of the frame and the result is scaled back to full, so the
        # output stays full size while the neural cost drops with the square of
        # the scale. At 1.0 it works at full resolution.
        self.work_scale = float(work_scale)
        self.work_w, self.work_h = work_size(self.width, self.height, work_scale)
        # A scale below 1 only means anything with the product's nr_small mode:
        # the network is handed a scaled-down frame and its result is scaled
        # back to full size. The distinction matters — shrinking the *work* size
        # while still feeding the network full-res pixels is a no-op, which is
        # the trap the upstream comment records ("handing it the full screen ...
        # is why work_scale never bought anything").
        self.nr_small = self.work_scale < 1.0
        # NR OFF: the worker skips NGX. Where --param intensity=0 may still run
        # the network at zero strength, this does not run it at all, so the
        # difference between the two is what the network actually costs.
        self.bypass = bool(bypass)
        # Split by mode. A bypassed frame runs no network, so its frame time is a different
        # animal from an enhanced frame's; averaging them yields a rate that describes neither.
        # That is how a summary read "26.45 fps steady" off a pipeline that cannot do 26 fps with
        # the pass on - half the frames were skipping it.
        self.enhanced_frames = 0
        self.enhanced_seconds = 0.0
        self.bypassed_frames = 0
        self.bypassed_seconds = 0.0
        # Commands from the global hotkeys (or anything else) are drained between frames. A
        # command rather than a shared flag so a toggle cannot be missed or applied twice.
        self.commands: queue.Queue = queue.Queue()
        self.report_diff = bool(report_diff)
        self.save_diff = save_diff
        self.diff_gain = float(diff_gain)
        # Flip the pass on and off every N seconds. The alternative is a keypress, and a global
        # one does not reach a Wayland-native window; a timer needs nothing from the user and
        # the badge says which half you are looking at.
        self.ab_alternate = max(0.0, float(ab_alternate))
        self._next_flip = 0.0
        # Sampled for the life of the run: the worker's timings say how long a frame took, this
        # says whether the GPU was busy while it took it.
        self.report_gpu = bool(report_gpu)
        self.gpu: "GpuSampler | None" = None
        self.running = True
        # Set by --hotkeys: polled between frames, so the window does not need focus.
        self.hotkey_poll = None

        self.worker = Worker(
            self.width, self.height, self.work_w, self.work_h, self.params,
            warmup=self.warmup, cmd=worker_cmd, cwd=worker_cwd,
            full_w=self.width if self.nr_small else 0,
            full_h=self.height if self.nr_small else 0,
            nr_small=self.nr_small,
            motion_small=self.motion_small,
            no_motion=self.no_motion,
            shm=self.shm,
            bypass=self.bypass,
            writev=self.writev,
            extra_env=worker_env_extra,
            echo_logs=worker_log)

        if display is not None:
            self.display = display
        else:
            self.display = Display(
                self.width, self.height, fullscreen=fullscreen, headless=headless,
                # On unless asked off, and never in a headless run: there is no window to
                # draw it in, and a badge would be a per-frame cost for nothing.
                indicator=(not headless) if indicator is None else bool(indicator))

        # One zero motion field, reused for every frame.
        # (H, W, 2) float16 — two channels, the same layout the pipe expects.
        #
        # The MVP has no real motion vectors (the upstream host derives them
        # from the game; a stream cannot supply them), so it sends zeros. At the
        # work resolution that is half the inbound bytes of every frame — 3.7 MB
        # of the 7.4 MB at 720p — spent on zeroes. MOTS sends the field at the
        # optical-flow size instead and the worker upscales it on the GPU, which
        # takes the same zeroes down to 0.23 MB.
        if self.motion_small:
            self.zero_motion = np.zeros((FLOW_H, FLOW_W, 2), dtype=np.float16)
        else:
            self.zero_motion = np.zeros((self.work_h, self.work_w, 2), dtype=np.float16)
        if self.motion_guides:
            # Imported here, not at module scope: guides pulls in cv2, and the synthetic and
            # mock paths must keep working on a machine where OpenCV is not installed.
            import guides as guides_module
            self.guides = guides_module.TemporalGuideGenerator(
                self.work_w, self.work_h, emit_small=self.motion_small)
        #: Split of the capture leg, when the source can tell us (the portal
        #: can: how long the frame took to arrive, then how long it took to
        #: copy). Not part of the total — they are a breakdown OF capture.
        self.capture_split: dict[str, list[float]] = {"wait": [], "read": []}
        self.frames_done = 0
        self.frames_skipped = 0
        # Per-stage times in seconds, one entry per completed frame.
        #
        # The whole reason this exists: "4.2 fps" says nothing about what to fix.
        # Measured at 1280x720 the loop spends ~67ms/frame with the effect dialled
        # to zero and ~97ms with it on, which points at the worker but cannot
        # separate capture, the pipe write, the worker's own work and the display
        # upload from one another. Any optimisation before that split is a guess.
        self.timings: dict[str, list[float]] = {
            "capture": [], "send": [], "recv": [], "display": [],
        }
        #: The frame the last process_one fed the worker (for a matched pair).
        self.last_input: np.ndarray | None = None

    # -- one iteration -----------------------------------------------------

    def _timed(self, name: str, fn, *args, **kwargs):
        t0 = time.monotonic()
        try:
            return fn(*args, **kwargs)
        finally:
            self.timings[name].append(time.monotonic() - t0)

    def _guide_motion(self, frame: np.ndarray, index: int) -> tuple[np.ndarray, bool]:
        """The motion field to send with this frame, and whether it resets history.

        Without an estimator that is one reused zero field, and only frame 0 resets. With
        `motion_guides` the field is estimated per frame: current-to-previous flow at the
        optical-flow size, zeroed below the estimator's noise floor, and a scene cut also
        asks the worker to reset. The returned buffer is reused by the next call, which is
        safe because send copies it before the next frame is captured.
        """
        if self.guides is None:
            return self.zero_motion, index == 0
        guide = self.guides.process(frame)
        return guide.motion, bool(index == 0 or guide.reset)

    def _drain_commands(self) -> None:
        """Apply whatever the hotkeys queued since the last frame."""
        while True:
            try:
                command = self.commands.get_nowait()
            except queue.Empty:
                return
            if command == "toggle":
                self.bypass = not self.bypass
                # The worker builds the frame flag from its own copy, so both move together.
                self.worker.bypass = self.bypass
                print(f"[nr] enhancement {'off' if self.bypass else 'on'}",
                      flush=True)
            elif command == "quit":
                self.running = False
                print("[main] quit from the hotkey", flush=True)

    def process_one(self, index: int, timeout: float = 60.0,
                    present: bool = True) -> np.ndarray | None:
        """Time one frame and book it against the mode it ran in.

        An A/B run alternates, and a bypassed frame does no neural work at all, so its frame time
        is not comparable to an enhanced frame's. Reporting their average describes neither mode -
        and it reads as though the pipeline can sustain a rate it cannot: with the pass on it is
        ~40ms a frame, and a run that mixed in bypassed frames summarised as 26 fps.
        """
        started = time.monotonic()
        try:
            return self._one_frame(index, timeout=timeout, present=present)
        finally:
            took = time.monotonic() - started
            if self.bypass:
                self.bypassed_frames += 1
                self.bypassed_seconds += took
            else:
                self.enhanced_frames += 1
                self.enhanced_seconds += took

    def mode_split(self) -> dict:
        """The two modes separately: counts, seconds, and the rate of each."""
        def rate(frames: int, seconds: float) -> float:
            return round(frames / seconds, 2) if seconds > 0 else 0.0

        return {
            "alternate": self.ab_alternate,
            "enhanced_frames": self.enhanced_frames,
            "enhanced_seconds": round(self.enhanced_seconds, 3),
            "enhanced_fps": rate(self.enhanced_frames, self.enhanced_seconds),
            "bypassed_frames": self.bypassed_frames,
            "bypassed_seconds": round(self.bypassed_seconds, 3),
            "bypassed_fps": rate(self.bypassed_frames, self.bypassed_seconds),
        }

    def _one_frame(self, index: int, timeout: float = 60.0,
                   present: bool = True) -> np.ndarray | None:
        """Grab, send, present, receive one frame.

        Returns the processed RGBA, or None if the worker returned no pixels
        (a skipped evaluation). `self.last_input` holds the frame this call fed
        the worker, so a caller can keep a matched before/after pair without
        re-implementing the grab.

        This is the only implementation of a frame step. `run` delegates to it:
        the two used to be separate copies of the same sequence, which is how an
        earlier matched-pair fix landed in one and not the other.
        """
        frame = self._timed("capture", self.capture.grab)
        # The portal splits its own grab into "waiting for the frame" and
        # "copying it". A capture leg of 325ms means opposite things in the two
        # cases, so if the source can tell us, record it.
        if getattr(self.capture, "last_wait", None) is not None:
            self.capture_split["wait"].append(self.capture.last_wait)
            self.capture_split["read"].append(self.capture.last_read)
        if frame.shape[:2] != (self.height, self.width):
            raise RuntimeError(
                f"capture returned {frame.shape[:2]}, expected "
                f"{(self.height, self.width)} — the screen changed size")
        self.last_input = frame

        motion, reset = self._guide_motion(frame, index)
        self._timed("send", self.worker.send, index, frame, motion,
                    reset, pts=index, want_pixels=self.want_pixels,
                    bgra=self.bgra)
        result = self._timed("recv", self.worker.recv, index, timeout)
        if result is None:
            if not self.want_pixels:
                # See _consume: a bare reply from a run that asked for no pixels is a
                # completed frame, and calling it skipped would report an idle worker.
                self.frames_done += 1
                return None
            self.frames_skipped += 1
            return None
        self.frames_done += 1
        if present and self.display is not None:
            # The badge follows the same flag the frame was built with, so it cannot disagree
            # with the picture it is drawn on.
            setter = getattr(self.display, "set_enhanced", None)
            if setter is not None:
                setter(not self.bypass)
            self._timed("display", self.display.show, result)
        return result

    def timing_summary(self) -> dict:
        """Mean seconds per stage, plus the total and the implied frame rate.

        Includes 'send' and 'recv' separately because they are different things:
        send is our own byte traffic into the worker, recv is us waiting for the
        worker to finish (its processing plus the pixels coming back).
        """
        def mean(xs: list[float]) -> float:
            return sum(xs) / len(xs) if xs else 0.0

        stamps = {k: mean(v) for k, v in self.timings.items()}
        total = sum(stamps.values())
        # The mean total is dominated by frame 0: the first frame pays the PTX
        # JIT warm-up and one multi-second frame divided by thirty looks like a
        # 3x slower pipeline. The median frame is what the steady state costs, so
        # report both, and the rate the median implies beside the mean's rate.
        series = list(self.timings.values())
        n = max((len(v) for v in series), default=0)
        frame_totals = [sum(v[i] for v in series if i < len(v))
                        for i in range(n)]
        ordered_totals = sorted(frame_totals)
        total_median = (ordered_totals[len(ordered_totals) // 2]
                        if ordered_totals else 0.0)
        out = {**stamps, "total": total,
               "fps": (1.0 / total) if total > 0 else 0.0,
               "total_median": total_median,
               "steady_fps": (1.0 / total_median) if total_median > 0 else 0.0,
               "count": len(self.timings["recv"])}
        # The spread, which the mean hides. A stage that costs the same on every
        # frame is structural — something is pacing at a fixed interval. A stage
        # that is small most frames and huge occasionally is our process being
        # descheduled, and those two need opposite fixes. `send` is the one to
        # look at first: it is 38-50ms a frame at EVERY frame size (38.4ms for a
        # 128KB frame) while the worker's own timestamps say it delivered that
        # same frame in 0.17ms.
        for name, values in self.timings.items():
            if len(values) >= 5:
                ordered = sorted(values)
                out[f"{name}_min"] = ordered[0]
                out[f"{name}_median"] = ordered[len(ordered) // 2]
                out[f"{name}_max"] = ordered[-1]
                # WHICH frame carried the maximum, because it decides what the
                # maximum means. Every variant shows one ~1.16s block in `send`;
                # if that block is frame 0 it is the worker's own D3D12/NGX
                # startup (about 1.05s), during which it is not reading its pipe
                # yet and our first write simply waits — a one-off at launch, not
                # a per-frame cost. If it lands anywhere else it is a real stall.
                out[f"{name}_max_at"] = values.index(ordered[-1])
        # A breakdown OF the capture leg, so deliberately excluded from the
        # total above: adding them would count the grab twice.
        if self.capture_split["wait"]:
            out["capture_wait"] = mean(self.capture_split["wait"])
            out["capture_read"] = mean(self.capture_split["read"])
        # What the kernel granted for the frame pipe. It decides what `read` means, so it
        # belongs next to it rather than being inferred from it.
        pipe_bytes = getattr(getattr(self, "capture", None), "pipe_bytes", 0)
        if pipe_bytes:
            out["capture_pipe_bytes"] = pipe_bytes
        return out

    def _capture_cpu(self) -> float | None:
        """The capture chain's CPU time, if the source can report it."""
        fn = getattr(self.capture, "cpu_seconds", None)
        return fn() if fn is not None else None

    def _capture_cpu_supported(self) -> bool:
        """Whether the source has a CPU reading at all, which is not the same
        as the reading working — see _capture_cpu_summary."""
        return getattr(self.capture, "cpu_seconds", None) is not None

    def _capture_cpu_pid(self) -> int | None:
        return getattr(self.capture, "pipeline_pid", None)

    def run(self, frames: int = 0, save_before: str | None = None,
            save_after: str | None = None, on_frame=None) -> dict:
        """Run the loop. frames=0 means until quit/EOF.

        Returns a summary dict — the caller (or a test) can assert on it.
        """
        self.worker.start()
        if self.report_gpu:
            from minimal.gpustat import GpuSampler
            self.gpu = GpuSampler().start()
        started = time.monotonic()
        # The capture chain's own CPU, sampled around the loop. It is invisible
        # in the grab time — the pipeline's copies and conversions happen while
        # the worker waits — and it is where the portal's ~47ms went at 1440p.
        capture_cpu0 = self._capture_cpu()
        capture_cpu_supported = self._capture_cpu_supported()
        pid0 = self._capture_cpu_pid()
        # The pair kept for --save-before/--save-after must come from ONE
        # iteration. Saving the first input against the last output measures
        # whatever moved on screen in between as if it were the pass: on the
        # synthetic test card, whose only moving part is a bar, that inflated the
        # reported difference from 15.8/255 to 48.7/255 — a 3x overstatement of
        # the thing being measured. Both loops below return a matched pair.
        pair_before = None
        last_after = None

        if not self.bypass:
            # The window is up before the worker has answered anything, and its first
            # answer is behind whatever the worker does at startup — with the native
            # worker, a model load and the JIT of 249 PTX kernels. A black window and a
            # silent console for twenty seconds looks like a hang, and on the box it was
            # reported as one. Here rather than in a loop, because both loops drive
            # frames and only one of them would say it.
            print("frame 0 is the worker's warm-up: the window stays black until its "
                  "first answer lands", flush=True)

        try:
            if self.send_ahead > 1:
                pair_before, last_after, index = self._pipelined_loop(
                    frames, on_frame, keep_inputs=bool(save_before or save_after))
            else:
                pair_before, last_after, index = self._serial_loop(frames, on_frame)
        finally:
            if self.gpu is not None:
                self.gpu.stop()
            # Sample the capture's CPU before close(): close() drops the
            # pipeline handle, and taking the end reading after it reported
            # "pid None" and a failed reading on every run — the measurement
            # was being taken after the thing it measures was gone.
            capture_cpu1 = self._capture_cpu()
            self.worker.stop()
            self.capture.close()
            self.display.close()

        elapsed = time.monotonic() - started

        if save_before and pair_before is not None:
            _save_rgba(save_before, pair_before, bgra=self.bgra)
        if (self.report_diff or self.save_diff) and self.bypass:
            # The A/B timer leaves the pass off half the time. Reporting a diff from that half
            # says "MAD 0.000" and reads as "the pass does nothing" when it says no such thing.
            print("diff: skipped - the last frame was the bypass half of the A/B; quit while the "
                  "badge reads ON, or run with --ab-alternate 0", flush=True)
        if ((self.report_diff or self.save_diff) and pair_before is not None
                and last_after is not None and not self.bypass):
            # The matched pair: both from one iteration, so the number is the pass's effect and
            # not whatever moved on screen between two frames.
            metrics = diff_metrics(pair_before, last_after)
            r, g, b = metrics["mad_rgb"]
            print(f"diff: MAD {metrics['mad']:.3f} (R {r:.3f} G {g:.3f} B {b:.3f})  "
                  f"max {metrics['max']}  PSNR {metrics['psnr']:.2f} dB  "
                  f">{2}: {100 * metrics['over_2']:.2f}%  >8: {100 * metrics['over_8']:.2f}%",
                  flush=True)
            if self.save_diff:
                _save_rgba(self.save_diff, amplified_diff(pair_before, last_after,
                                                          self.diff_gain))
                print(f"  diff   -> {self.save_diff} (amplified x{self.diff_gain:g})",
                      flush=True)
        if save_after and last_after is not None:
            # The worker always answers in RGBA, whatever went in.
            _save_rgba(save_after, last_after, bgra=False)

        timing = self.timing_summary()
        return {
            "frames_attempted": index,
            "frames_done": self.frames_done,
            "frames_skipped": self.frames_skipped,
            # An A/B run mixes two modes; these are that split, so a summary can report the rate
            # of each instead of an average of both.
            "modes": self.mode_split(),
            # How many frames were allowed in flight, so a summary says which
            # loop produced it, and how many times the worker went silent.
            "send_ahead": self.send_ahead,
            "stalls": self.stalls,
            "seconds": round(elapsed, 3),
            "fps": round(self.frames_done / elapsed, 2) if elapsed > 0 else 0.0,
            "steady_fps": round(timing.get("steady_fps", 0.0), 2),
            "worker_exit": self.worker.proc.returncode if self.worker.proc else None,
            "before": pair_before,
            "after": last_after,
            "timing": timing,
            # The worker's OWN clock, parsed from the lines it stamps as it
            # delivers frames. It is the one number in a run that does not depend
            # on our timing at all, so it is reported next to ours: if the two
            # disagree, everything else in the summary is suspect. It also names
            # a stall — the 30-frame runs that took 12.5s while the 60 and 90
            # frame runs took under 2s were the worker stalling in NGX init, not
            # processing slowly.
            "worker_clock": worker_timeline(self.worker.logs),
            # Only a prefetching source has anything to say here.
            "prefetch": _prefetch_stats(self.capture),
            # What the frame source replayed, when it is a source that can say (the video file).
            "source": _source_stats(self.capture),
            # The capture chain's own CPU over the run. Not part of the frame
            # time — it is work that happens while the worker waits, and at
            # 2560x1440 that is where the portal's extra ~47ms of `send` went.
            "capture_cpu": _capture_cpu_summary(
                capture_cpu0, capture_cpu1, elapsed,
                supported=capture_cpu_supported, pid=pid0),
        }

    # -- the two loops -----------------------------------------------------

    def _check_alive(self) -> None:
        if not self.worker.is_alive():
            raise RuntimeError(
                "the worker died during the run; last stderr:\n  "
                + "\n  ".join(self.worker.logs[-15:] or ["(no output)"]))

    def _serial_loop(self, frames: int, on_frame):
        """One frame in flight: send it, then wait for that frame's result.

        The shape the MVP has always had, and the reason every frame carries the
        worker's whole per-frame time plus a round trip.
        """
        index = 0
        pair_before = last_after = None
        while (frames == 0 or index < frames) and self.running:
            self._check_alive()
            if self.hotkey_poll is not None:
                try:
                    self.hotkey_poll(block=False)
                except Exception:
                    pass
            self._drain_commands()
            if not self.running:
                break
            events = self.display.poll_events()
            if "quit" in events:
                break
            if "toggle" in events:
                self.commands.put("toggle")
                self._drain_commands()
            if self.ab_alternate:
                now = time.monotonic()
                if self._next_flip == 0.0:
                    self._next_flip = now + self.ab_alternate
                elif now >= self._next_flip:
                    self._next_flip = now + self.ab_alternate
                    self.bypass = not self.bypass
                    self.worker.bypass = self.bypass
                    print(f"[nr] A/B: enhancement {'off' if self.bypass else 'on'}",
                          flush=True)
            after = self.process_one(index, present=True)
            if after is not None:
                # process_one keeps the input it fed for this iteration, so the
                # saved pair can never straddle two frames.
                pair_before = self.last_input
                last_after = after
                if on_frame is not None:
                    on_frame(index, after)
            index += 1
        return pair_before, last_after, index

    def _take_oldest(self, window):
        """Wait for the oldest in-flight frame's result, check it, show it.

        Returns (sent_index, input_frame, after); `after` is None when the worker
        skipped the frame and `input_frame` is None unless the caller is keeping
        inputs for a saved pair.
        """
        sent_index, input_frame = window.popleft()
        try:
            got_index, after = self._timed("recv", self.worker.recv_any,
                                           self.frame_timeout)
        except TimeoutError as exc:
            self.stalls += 1
            raise RuntimeError(
                f"the worker stalled: no reply in {self.frame_timeout:.0f}s for "
                f"frame {sent_index}, with {len(window) + 1} frame(s) in flight "
                f"({self.stalls} stall(s) this run). Stopping rather than "
                f"continuing: the worker answers in order, so every reply after a "
                f"missing one is unattributable, and showing one frame's result "
                f"against another frame's input is worse than stopping.") from exc

        if got_index != sent_index:
            raise RuntimeError(
                f"the worker answered frame {got_index} while frame {sent_index} "
                f"was the oldest in flight — replies come in order, so the run "
                f"has lost its pairing and nothing after this would be a "
                f"measurement")
        if after is None:
            return sent_index, input_frame, None
        if self.display is not None:
            setter = getattr(self.display, "set_enhanced", None)
            if setter is not None:
                setter(not self.bypass)
            self._timed("display", self.display.show, after)
        return sent_index, input_frame, after

    def _consume(self, window, pair: list, on_frame) -> None:
        """Take one result and keep the counters, the pair and the callback in step.

        One implementation for the window path and the drain path: two copies of
        this is how the counters and the pair got out of step before.
        """
        sent_index, input_frame, after = self._take_oldest(window)
        if after is None:
            if not self.want_pixels:
                # A bare reply: the worker ran the frame and published nothing because
                # nothing asked for pixels. That is a completed frame, not a skipped
                # evaluation - counting it as skipped reported an idle worker.
                self.frames_done += 1
                return
            self.frames_skipped += 1
            return
        self.frames_done += 1
        if input_frame is not None:
            pair[0], pair[1] = input_frame, after
        if on_frame is not None:
            on_frame(sent_index, after)

    def _pipelined_loop(self, frames: int, on_frame, keep_inputs: bool):
        """Keep `send_ahead` frames in flight instead of one.

        The worker answers in order — it finishes writing a frame's reply before
        reading the next frame — so a reply pairs with the oldest send, and a
        deque of what was sent is the entire bookkeeping. One wait per frame once
        the window is full, instead of one wait inside every frame.

        keep_inputs retains each in-flight input so a saved before/after pair
        still comes from a single iteration. At 1440p that is 14.7MB per frame in
        flight, so it stays off unless something is going to save a pair.
        """
        index = 0
        window: deque = deque()
        pair: list = [None, None]
        while frames == 0 or index < frames:
            self._check_alive()
            if "quit" in self.display.poll_events():
                break

            frame = self._timed("capture", self.capture.grab)
            if getattr(self.capture, "last_wait", None) is not None:
                self.capture_split["wait"].append(self.capture.last_wait)
                self.capture_split["read"].append(self.capture.last_read)
            if frame.shape[:2] != (self.height, self.width):
                raise RuntimeError(
                    f"capture returned {frame.shape[:2]}, expected "
                    f"{(self.height, self.width)} — the screen changed size")
            self.last_input = frame

            motion, reset = self._guide_motion(frame, index)
            self._timed("send", self.worker.send, index, frame, motion,
                        reset, pts=index, want_pixels=self.want_pixels,
                        bgra=self.bgra)
            window.append((index, frame if keep_inputs else None))
            index += 1

            while len(window) >= self.send_ahead:
                self._consume(window, pair, on_frame)

        # Drain what is still in flight: frames_done should count every frame the
        # worker answered, not only the ones the window happened to wait for.
        while window:
            self._consume(window, pair, on_frame)
        return pair[0], pair[1], index

    def close(self) -> None:
        try:
            self.worker.stop(timeout=5)
        except Exception:
            pass


def _to_rgba(frame: np.ndarray, *, bgra: bool = False) -> np.ndarray:
    """The frame's bytes in RGBA order, without copying when they already are.

    The capture leg no longer swaps channels (that was 6.9ms of a 29ms 1440p
    frame); the port swizzles on the GPU. A file still has to be written in
    RGBA, so this is the one place the order is converted: at save time, on the
    frame being saved, not on every frame in the loop.
    """
    if not bgra:
        return frame
    return frame[:, :, [2, 1, 0, 3]]


def diff_metrics(before: np.ndarray, after: np.ndarray) -> dict:
    """How far the pass moved the picture, in the terms that decide whether it is visible.

    MAD is the average absolute change per channel: a pass that changes nothing has 0. The
    "over" counts say how much of the frame moved by more than a step or two, which is closer to
    what an eye notices than a mean is - a small mean over a large area of subtle change and a
    small mean over a few strongly changed pixels are very different pictures.
    """
    a = before[..., :3].astype(np.int16)
    b = after[..., :3].astype(np.int16)
    delta = np.abs(b - a)
    per_channel = [float(delta[..., i].mean()) for i in range(3)]
    total = delta.size
    return {
        "mad": float(delta.mean()),
        "mad_rgb": per_channel,
        "max": int(delta.max()),
        "over_2": float((delta.max(axis=2) > 2).sum()) / (before.shape[0] * before.shape[1]),
        "over_8": float((delta.max(axis=2) > 8).sum()) / (before.shape[0] * before.shape[1]),
        "psnr": float("inf") if delta.max() == 0 else float(
            20 * np.log10(255.0 / np.sqrt(float((delta.astype(np.float64) ** 2).mean())))),
    }


def amplified_diff(before: np.ndarray, after: np.ndarray, gain: float = 8.0) -> np.ndarray:
    """A picture of the difference: mid-grey where nothing moved, brighter/darker where it did.

    Useful precisely because the pass is subtle on real content - a 1-2 level change is invisible
    in the frames themselves and unmissable here.
    """
    a = before[..., :3].astype(np.float32)
    b = after[..., :3].astype(np.float32)
    shifted = 128.0 + (b - a) * float(gain)
    out = np.empty((*shifted.shape[:2], 4), dtype=np.uint8)
    out[..., :3] = np.clip(shifted, 0, 255).astype(np.uint8)
    out[..., 3] = 255
    return out


def _save_rgba(path: str, frame: np.ndarray, *, bgra: bool = False) -> None:
    """Write an RGBA array out as a PNG (via pygame, so there is no cv2 dep)."""
    import pygame
    rgba = _to_rgba(frame, bgra=bgra)
    surface = pygame.image.frombuffer(
        rgba.tobytes(), (rgba.shape[1], rgba.shape[0]), "RGBA")
    pygame.image.save(surface, path)


def run(frames: int = 0, monitor: int = 0, fullscreen: bool = True,
        headless: bool = False, save_before: str | None = None,
        save_after: str | None = None) -> dict:
    """Convenience wrapper used by __main__ and the integration tests."""
    pipe = Pipeline(monitor=monitor, fullscreen=fullscreen, headless=headless)
    return pipe.run(frames=frames, save_before=save_before, save_after=save_after)