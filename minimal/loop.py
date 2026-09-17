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
from pathlib import Path

import numpy as np

from minimal.capture import Capture
from minimal.display import Display
from minimal.worker import FLOW_H, FLOW_W, Worker, work_size

# The profile the MVP runs with, from settings_io.PROFILES["Natural"].
# Duplicated rather than imported so the MVP does not pull in the whole
# settings subsystem (config files, presets, i18n).
DEFAULT_PARAMS = {
    "profile": 1, "preset": 0, "style": 1, "auto_mask": 0, "ui_correction": 0,
    "intensity": 1.00, "local_tone": 1.00, "local_structure": 1.00,
    "skin_structure": -1.0,
}


class Pipeline:
    """Capture a frame, run it through the worker, put the result on screen."""

    def __init__(self, *, monitor: int = 0, params: dict | None = None,
                 fullscreen: bool = False, headless: bool = False,
                 warmup: int = 2, worker_cmd: list[str] | None = None,
                 worker_cwd: Path | None = None, capture=None, display=None,
                 work_scale: float = 1.0, motion_small: bool = False,
                 bypass: bool = False):
        self.params = dict(params or DEFAULT_PARAMS)
        self.warmup = warmup
        self.headless = headless
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
            bypass=self.bypass)

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

    def run(self, frames: int = 0, save_before: str | None = None,
            save_after: str | None = None, on_frame=None) -> dict:
        """Run the loop. frames=0 means until quit/EOF.

        Returns a summary dict — the caller (or a test) can assert on it.
        """
        self.worker.start()
        started = time.monotonic()
        index = 0
        # The pair kept for --save-before/--save-after must come from ONE
        # iteration. Saving the first input against the last output measures
        # whatever moved on screen in between as if it were the pass: on the
        # synthetic test card, whose only moving part is a bar, that inflated the
        # reported difference from 15.8/255 to 48.7/255 — a 3x overstatement of
        # the thing being measured.
        pair_before = None
        last_after = None

        try:
            while frames == 0 or index < frames:
                if not self.worker.is_alive():
                    raise RuntimeError(
                        "the worker died during the run; last stderr:\n  "
                        + "\n  ".join(self.worker.logs[-15:] or ["(no output)"]))

                if "quit" in self.display.poll_events():
                    break

                after = self.process_one(index, present=True)
                if after is not None:
                    # process_one keeps the input it fed for this iteration, so
                    # the saved pair can never straddle two frames.
                    pair_before = self.last_input
                    last_after = after
                    if on_frame is not None:
                        on_frame(index, after)
                index += 1
        finally:
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
            "seconds": round(elapsed, 3),
            "fps": round(self.frames_done / elapsed, 2) if elapsed > 0 else 0.0,
            "worker_exit": self.worker.proc.returncode if self.worker.proc else None,
            "before": pair_before,
            "after": last_after,
            "timing": self.timing_summary(),
        }

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