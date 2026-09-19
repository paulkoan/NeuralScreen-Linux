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
    """`stats()` from a prefetching source, or None for a plain one."""
    fn = getattr(capture, "stats", None)
    return fn() if fn is not None else None


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
                 worker_cwd: Path | None = None, capture=None, display=None,
                 work_scale: float = 1.0, motion_small: bool = False,
                 bypass: bool = False, send_ahead: int = 1,
                 frame_timeout: float = 60.0, writev: bool = False):
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

        # Injected sources let the tests drive the loop without a screen or a GPU.
        self.capture = capture if capture is not None else Capture(monitor_idx=monitor)
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

        self.worker = Worker(
            self.width, self.height, self.work_w, self.work_h, self.params,
            warmup=self.warmup, cmd=worker_cmd, cwd=worker_cwd,
            full_w=self.width if self.nr_small else 0,
            full_h=self.height if self.nr_small else 0,
            nr_small=self.nr_small,
            motion_small=self.motion_small,
            bypass=self.bypass,
            writev=self.writev)

        if display is not None:
            self.display = display
        else:
            self.display = Display(self.width, self.height,
                                   fullscreen=fullscreen, headless=headless)

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

    def process_one(self, index: int, timeout: float = 60.0,
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

        reset = index == 0
        self._timed("send", self.worker.send, index, frame, self.zero_motion,
                    reset, pts=index)
        result = self._timed("recv", self.worker.recv, index, timeout)
        if result is None:
            self.frames_skipped += 1
            return None
        self.frames_done += 1
        if present and self.display is not None:
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
        out = {**stamps, "total": total,
               "fps": (1.0 / total) if total > 0 else 0.0,
               "count": len(self.timings["recv"])}
        # A breakdown OF the capture leg, so deliberately excluded from the
        # total above: adding them would count the grab twice.
        if self.capture_split["wait"]:
            out["capture_wait"] = mean(self.capture_split["wait"])
            out["capture_read"] = mean(self.capture_split["read"])
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

        try:
            if self.send_ahead > 1:
                pair_before, last_after, index = self._pipelined_loop(
                    frames, on_frame, keep_inputs=bool(save_before or save_after))
            else:
                pair_before, last_after, index = self._serial_loop(frames, on_frame)
        finally:
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
            _save_rgba(save_before, pair_before)
        if save_after and last_after is not None:
            _save_rgba(save_after, last_after)

        return {
            "frames_attempted": index,
            "frames_done": self.frames_done,
            "frames_skipped": self.frames_skipped,
            # How many frames were allowed in flight, so a summary says which
            # loop produced it, and how many times the worker went silent.
            "send_ahead": self.send_ahead,
            "stalls": self.stalls,
            "seconds": round(elapsed, 3),
            "fps": round(self.frames_done / elapsed, 2) if elapsed > 0 else 0.0,
            "worker_exit": self.worker.proc.returncode if self.worker.proc else None,
            "before": pair_before,
            "after": last_after,
            "timing": self.timing_summary(),
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
        while frames == 0 or index < frames:
            self._check_alive()
            if "quit" in self.display.poll_events():
                break
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
            self._timed("display", self.display.show, after)
        return sent_index, input_frame, after

    def _consume(self, window, pair: list, on_frame) -> None:
        """Take one result and keep the counters, the pair and the callback in step.

        One implementation for the window path and the drain path: two copies of
        this is how the counters and the pair got out of step before.
        """
        sent_index, input_frame, after = self._take_oldest(window)
        if after is None:
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

            self._timed("send", self.worker.send, index, frame, self.zero_motion,
                        index == 0, pts=index)
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


def _save_rgba(path: str, frame: np.ndarray) -> None:
    """Write an RGBA array out as a PNG (via pygame, so there is no cv2 dep)."""
    import pygame
    surface = pygame.image.frombuffer(
        frame.tobytes(), (frame.shape[1], frame.shape[0]), "RGBA")
    pygame.image.save(surface, path)


def run(frames: int = 0, monitor: int = 0, fullscreen: bool = True,
        headless: bool = False, save_before: str | None = None,
        save_after: str | None = None) -> dict:
    """Convenience wrapper used by __main__ and the integration tests."""
    pipe = Pipeline(monitor=monitor, fullscreen=fullscreen, headless=headless)
    return pipe.run(frames=frames, save_before=save_before, save_after=save_after)