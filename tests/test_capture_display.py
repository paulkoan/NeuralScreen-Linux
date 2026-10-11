"""M1 — capture and display against a real (virtual) video driver.

These run under Xvfb so they exercise the actual mss and SDL2 code paths rather
than fakes. Everything here is skipped if no X server can be started.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


# --- capture --------------------------------------------------------------

def test_capture_reports_a_resolution(xvfb_display):
    from minimal.capture import Capture
    with Capture(monitor_idx=0) as cap:
        assert cap.width > 0 and cap.height > 0
        assert cap.resolution == (cap.width, cap.height)


def test_capture_returns_rgba_uint8(xvfb_display):
    from minimal.capture import Capture
    with Capture(monitor_idx=0) as cap:
        frame = cap.grab()
    assert frame.dtype == np.uint8, f"expected uint8, got {frame.dtype}"
    assert frame.ndim == 3
    assert frame.shape[2] == 4, f"expected 4 channels, got {frame.shape[2]}"
    assert frame.shape[:2] == (cap.height, cap.width)


def test_capture_consecutive_frames_have_the_same_shape(xvfb_display):
    from minimal.capture import Capture
    with Capture(monitor_idx=0) as cap:
        a, b = cap.grab(), cap.grab()
    assert a.shape == b.shape


def test_capture_rejects_a_missing_monitor(xvfb_display):
    from minimal.capture import Capture, CaptureError
    with pytest.raises(CaptureError, match="does not exist"):
        Capture(monitor_idx=99)


def test_list_monitors(xvfb_display):
    from minimal.capture import list_monitors
    monitors = list_monitors()
    assert len(monitors) >= 1
    idx, desc = monitors[0]
    assert idx == 0
    assert "x" in desc


# --- display --------------------------------------------------------------

def test_display_headless_presents_without_a_window(xvfb_display):
    from minimal.display import Display
    frame = np.zeros((120, 160, 4), dtype=np.uint8)
    frame[..., 3] = 255
    with Display(160, 120, headless=True) as d:
        d.show(frame)
        d.show(frame)
        assert d.frames_shown == 2


def test_display_rejects_a_wrong_size(xvfb_display):
    from minimal.display import Display
    with Display(160, 120, headless=True) as d:
        with pytest.raises(ValueError, match="the window is"):
            d.show(np.zeros((100, 100, 4), dtype=np.uint8))


def test_display_rejects_a_wrong_dtype(xvfb_display):
    from minimal.display import Display
    with Display(160, 120, headless=True) as d:
        with pytest.raises(ValueError, match="expected uint8"):
            d.show(np.zeros((120, 160, 4), dtype=np.float32))


def test_display_can_be_created_twice_in_a_row(xvfb_display):
    """SDL subsystems must survive create/close/create."""
    from minimal.display import Display
    frame = np.zeros((60, 80, 4), dtype=np.uint8)
    for _ in range(2):
        with Display(80, 60, headless=True) as d:
            d.show(frame)
            assert d.frames_shown == 1


def test_display_paints_black_before_the_first_frame(xvfb_display, monkeypatch):
    """The window must not show an undefined surface while it waits for frame 0.

    It is created before the worker has answered anything, and with the native worker
    the first reply is behind a model load and the JIT of 249 PTX kernels. What the
    driver's buffer holds in the meantime is not ours to choose — a solid colour across a
    fullscreen window is exactly what a broken pipeline looks like — so it is cleared and
    presented once at creation.
    """
    from minimal import display as display_module
    from minimal.display import Display

    presented = []
    original = display_module.sdl2.SDL_RenderPresent

    def counting(renderer):
        presented.append(renderer)
        return original(renderer)

    monkeypatch.setattr(display_module.sdl2, "SDL_RenderPresent", counting)
    with Display(80, 60) as d:            # not headless: a real (virtual) window
        assert len(presented) == 1, "the window was not painted at creation"
        assert d.frames_shown == 0, "painting the window is not showing a frame"
        d.show(np.zeros((60, 80, 4), dtype=np.uint8))
        assert len(presented) == 2


def test_display_polls_without_events(xvfb_display):
    from minimal.display import Display
    with Display(80, 60, headless=True) as d:
        assert d.poll_events() == []