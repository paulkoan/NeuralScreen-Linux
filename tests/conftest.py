"""Shared fixtures for the MVP tests.

Everything here runs with no GPU and no Wine: a synthetic capture source, a
headless SDL2 display, and the mock worker from tests/mock_worker.py speaking
the real binary protocol.
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

MOCK_WORKER = REPO / "tests" / "mock_worker.py"


class FakeCapture:
    """A capture source that generates a deterministic pattern.

    Same interface as minimal.capture.Capture: .resolution, .grab(), .close().
    Frames deliberately contain no 0/255 saturation so the mock worker's
    brightness offset cannot clip and hide a difference.
    """

    def __init__(self, width: int = 320, height: int = 180):
        self.width, self.height = width, height
        self.grabs = 0
        self.closed = False
        # A gradient that changes with each grab, so consecutive frames differ.
        xs = np.linspace(32, 200, width, dtype=np.uint8)
        ys = np.linspace(32, 200, height, dtype=np.uint8)
        self._base = np.empty((height, width, 4), dtype=np.uint8)
        self._base[..., 0] = xs[None, :]      # R varies along x
        self._base[..., 1] = ys[:, None]      # G varies along y
        self._base[..., 2] = 64               # B constant
        self._base[..., 3] = 255              # A opaque

    @property
    def resolution(self) -> tuple[int, int]:
        return self.width, self.height

    def grab(self) -> np.ndarray:
        frame = self._base.copy()
        frame[..., 2] = (64 + self.grabs * 3) % 200  # B changes every frame
        self.grabs += 1
        return frame

    def close(self) -> None:
        self.closed = True


class FakeDisplay:
    """Records what it was asked to show; never touches SDL2."""

    def __init__(self):
        self.frames: list[np.ndarray] = []
        self.closed = False
        self.quit_after: int | None = None

    def show(self, frame: np.ndarray) -> None:
        self.frames.append(frame.copy())

    def poll_events(self) -> list[str]:
        if self.quit_after is not None and len(self.frames) >= self.quit_after:
            return ["quit"]
        return []

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_capture():
    return FakeCapture()


@pytest.fixture
def fake_display():
    return FakeDisplay()


@pytest.fixture
def mock_worker_cmd():
    """A command that runs the mock worker instead of the Wine worker."""
    return [sys.executable, str(MOCK_WORKER)]


@pytest.fixture(scope="session")
def xvfb_display():
    """Start Xvfb for the tests that need a real video driver.

    SDL2 needs a video driver even for a hidden window, so the capture and
    display tests run against a virtual X server. Skipped if Xvfb is missing.
    """
    if os.environ.get("NS_TEST_DISPLAY"):
        yield os.environ["NS_TEST_DISPLAY"]
        return

    import shutil
    import subprocess
    import time
    if shutil.which("Xvfb") is None:
        pytest.skip("Xvfb not installed")

    display = ":97"
    proc = subprocess.Popen(
        ["Xvfb", display, "-screen", "0", "1024x768x24"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    if proc.poll() is not None:
        pytest.skip("Xvfb failed to start")

    old = os.environ.get("DISPLAY")
    os.environ["DISPLAY"] = display
    try:
        yield display
    finally:
        os.environ["DISPLAY"] = old if old is not None else ""
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()