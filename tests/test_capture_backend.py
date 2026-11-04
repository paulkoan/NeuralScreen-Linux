"""The app's Wayland capture: the portal path, not a pip package that is not installed.

`ScreenCapture` demanded `pipewire-capture` on Wayland and raised if it was missing, so v1 could
not start at all on the box - while the MVP had been capturing through xdg-desktop-portal for
weeks. These tests pin the fallback and the window-mode branch that goes with it.
"""
from __future__ import annotations

import sys
import types

import numpy as np
import pytest

import capture_linux


class _FakePortal:
    """Stands in for minimal.capture_wayland.PortalCapture."""

    made: list[dict] = []

    def __init__(self, monitor_idx=0, *, source=None, **kwargs):
        self.monitor_idx = monitor_idx
        self.source = source
        self.closed = False
        _FakePortal.made.append({"monitor_idx": monitor_idx, "source": source, **kwargs})

    @property
    def resolution(self):
        return (2560, 1440)

    def grab(self):
        return np.zeros((1440, 2560, 4), dtype=np.uint8)

    def close(self):
        self.closed = True


@pytest.fixture
def wayland_without_pipewire(monkeypatch):
    monkeypatch.setattr(capture_linux, "_is_wayland", lambda: True)
    monkeypatch.setattr(capture_linux, "_HAS_PIPEWIRE", False)
    _FakePortal.made.clear()
    module = types.ModuleType("minimal.capture_wayland")
    module.PortalCapture = _FakePortal
    monkeypatch.setitem(sys.modules, "minimal.capture_wayland", module)
    return _FakePortal


def test_wayland_falls_back_to_the_portal(wayland_without_pipewire):
    cap = capture_linux.ScreenCapture(0)
    assert isinstance(cap._backend, _FakePortal)
    assert cap.resolution == (2560, 1440)
    assert cap.grab().shape == (1440, 2560, 4)


def test_the_default_source_is_a_whole_screen(wayland_without_pipewire):
    from minimal.portal import SOURCE_MONITOR
    capture_linux.ScreenCapture(0)
    assert _FakePortal.made[-1]["source"] == SOURCE_MONITOR


def test_a_window_source_is_passed_through(wayland_without_pipewire):
    from minimal.portal import SOURCE_WINDOW
    capture_linux.ScreenCapture(0, source=SOURCE_WINDOW)
    assert _FakePortal.made[-1]["source"] == SOURCE_WINDOW


def test_close_reaches_the_backend(wayland_without_pipewire):
    cap = capture_linux.ScreenCapture(0)
    backend = cap._backend
    cap.close()
    assert backend.closed


def test_window_mode_recreates_the_capture_instead_of_refusing():
    """The old branch refused window mode whenever capture_in_worker was off - which v1 always is."""
    source = (capture_linux.__file__ and
              open(capture_linux.__file__, encoding="utf-8").read())
    assert "PortalCapture" in source

    pipeline = open("pipeline_linux.py", encoding="utf-8").read()
    assert "SOURCE_WINDOW if hwnd else SOURCE_MONITOR" in pipeline, (
        "window mode must recreate the portal capture with the window source")
    # and the refusal must still exist for the Wine/DDA path, after the portal branch
    assert pipeline.index("SOURCE_WINDOW if hwnd else SOURCE_MONITOR") < pipeline.index(
        "window mode needs capture in the worker")


def test_a_window_request_carries_the_size(wayland_without_pipewire):
    """A window stream reports 0x0, so the pipeline has to name the size it wants."""
    from minimal.portal import SOURCE_WINDOW
    capture_linux.ScreenCapture(0, source=SOURCE_WINDOW, width=2560, height=1440)
    made = _FakePortal.made[-1]
    assert made["source"] == SOURCE_WINDOW
    assert made["width"] == 2560 and made["height"] == 1440


def test_the_v1_config_asks_for_a_window():
    """A monitor request offers screen/workspace/region and no window at all."""
    import json
    from pathlib import Path
    cfg = json.loads((Path(__file__).resolve().parent.parent / "config.v1.json").read_text())
    assert cfg["capture_source"] == "window"
