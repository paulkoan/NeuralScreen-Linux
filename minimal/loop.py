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
from minimal.worker import Worker, work_size

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
                 worker_cwd: Path | None = None, capture=None, display=None):
        self.params = dict(params or DEFAULT_PARAMS)
        self.warmup = warmup
        self.headless = headless

        # Injected sources let the tests drive the loop without a screen or a GPU.
        self.capture = capture if capture is not None else Capture(monitor_idx=monitor)
        self.width, self.height = self.capture.resolution
        self.work_w, self.work_h = work_size(self.width, self.height)

        self.worker = Worker(
            self.width, self.height, self.work_w, self.work_h, self.params,
            warmup=self.warmup, cmd=worker_cmd, cwd=worker_cwd)

        if display is not None:
            self.display = display
        else:
            self.display = Display(self.width, self.height,
                                   fullscreen=fullscreen, headless=headless)

        # One zero motion field at work resolution, reused for every frame.
        # (H, W, 2) float16 — two channels, the same layout the pipe expects.
        self.zero_motion = np.zeros((self.work_h, self.work_w, 2), dtype=np.float16)
        self.frames_done = 0
        self.frames_skipped = 0

    # -- one iteration -----------------------------------------------------

    def process_one(self, index: int, timeout: float = 60.0) -> np.ndarray | None:
        """Grab, send, receive one frame. Returns the processed RGBA or None
        if the worker returned no pixels (a skipped evaluation)."""
        frame = self.capture.grab()
        if frame.shape[:2] != (self.height, self.width):
            raise RuntimeError(
                f"capture returned {frame.shape[:2]}, expected "
                f"{(self.height, self.width)} — the screen changed size")

        reset = index == 0
        self.worker.send(index, frame, self.zero_motion, reset, pts=index)
        result = self.worker.recv(index, timeout)
        if result is None:
            self.frames_skipped += 1
            return None
        self.frames_done += 1
        return result

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

                before = self.capture.grab()

                self.worker.send(index, before, self.zero_motion, index == 0, pts=index)
                after = self.worker.recv(index, 60.0)
                if after is None:
                    self.frames_skipped += 1
                else:
                    pair_before = before
                    last_after = after
                    self.frames_done += 1
                    self.display.show(after)
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