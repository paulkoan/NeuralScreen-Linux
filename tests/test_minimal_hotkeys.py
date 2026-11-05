"""v1's hotkeys: the loop owns the state, the X11 callback only queues.

Two properties matter. The toggle must move the worker's copy of the flag as well as the loop's,
or the frame is built from one and reported from the other. And the callback must not touch state
directly: it runs on the X11 poll, outside the frame the loop is building.
"""
from __future__ import annotations

import numpy as np
import pytest

from minimal.loop import Pipeline
from minimal.worker import FLOW_H, FLOW_W
from tests.conftest import FakeDisplay

REPO = __import__("pathlib").Path(__file__).resolve().parent.parent


class _Capture:
    bgra = False

    def __init__(self, width=64, height=48):
        self.width, self.height = width, height

    @property
    def resolution(self):
        return self.width, self.height

    def grab(self):
        return np.zeros((self.height, self.width, 4), np.uint8)

    def close(self):
        pass


def _pipeline(**kwargs):
    return Pipeline(capture=_Capture(), display=FakeDisplay(), headless=True,
                    worker_cmd=["true"], worker_cwd=REPO, want_pixels=False, **kwargs)


def test_a_toggle_flips_both_copies_of_the_flag():
    pipe = _pipeline()
    assert pipe.bypass is False and pipe.worker.bypass is False
    pipe.commands.put("toggle")
    pipe._drain_commands()
    assert pipe.bypass is True, "the loop's copy must flip"
    assert pipe.worker.bypass is True, "the worker builds the frame flag from its own copy"


def test_two_toggles_are_back_where_they_started():
    pipe = _pipeline()
    for _ in range(2):
        pipe.commands.put("toggle")
        pipe._drain_commands()
    assert pipe.bypass is False and pipe.worker.bypass is False


def test_quit_stops_the_loop():
    pipe = _pipeline()
    pipe.commands.put("quit")
    pipe._drain_commands()
    assert pipe.running is False


def test_an_unknown_command_is_ignored():
    pipe = _pipeline()
    pipe.commands.put("nonsense")
    pipe._drain_commands()
    assert pipe.running is True and pipe.bypass is False


def test_the_worker_sends_its_own_bypass_flag():
    """The frame's flag is built by Worker.send from `self.bypass`, so the toggle must set that."""
    source = (REPO / "minimal" / "worker.py").read_text()
    assert "bypass=self.bypass" in source


def test_the_cli_offers_the_flag():
    source = (REPO / "minimal" / "__main__.py").read_text()
    assert '"--hotkeys"' in source
    # The bindings moved to hotkeys_backend, which owns both the list and the backend choice.
    assert "hotkeys_backend.install(pipe)" in source
    backend = (REPO / "hotkeys_backend.py").read_text()
    assert "Ctrl+Alt+1" in backend and "Ctrl+Alt+Q" in backend
    assert "pipe.commands.put" in backend, "the callbacks must only enqueue"
