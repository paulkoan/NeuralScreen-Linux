"""Backend choice: which hotkey mechanism a session gets, and what happens when it cannot work.

The failure this fixes was silent — XGrabKey registered on Wayland and never fired. So the
interesting cases here are the ones the old code had no answer for: a Wayland session, a backend
that raises, and no backend at all.
"""
from __future__ import annotations

import queue

import pytest

from hotkeys_backend import DEFAULT_BINDINGS, install, on_wayland, uninstall


class _FakePipe:
    def __init__(self):
        self.commands = queue.Queue()
        self.hotkey_poll = None


class _FakeBackend:
    """Records what was asked of it, and can be told to refuse."""

    def __init__(self, name, fail=False):
        self.name = name
        self.fail = fail
        self.registered = []
        self.unregistered = 0

    def register_global_hotkey(self, combo, callback):
        if self.fail:
            raise RuntimeError(f"{self.name} cannot register {combo}")
        self.registered.append((combo, callback))

    def poll_events(self, block=False):
        return []

    def unregister_all(self):
        self.unregistered += 1


def test_wayland_is_detected_both_ways():
    assert on_wayland({"WAYLAND_DISPLAY": "wayland-0"}) is True
    assert on_wayland({"XDG_SESSION_TYPE": "wayland"}) is True
    assert on_wayland({"XDG_SESSION_TYPE": "Wayland"}) is True
    assert on_wayland({"DISPLAY": ":0"}) is False
    assert on_wayland({}) is False


def test_wayland_prefers_evdev():
    """The X11 grab cannot see a Wayland window's keys; evdev is not affected by the compositor."""
    pipe = _FakePipe()
    backends = {"evdev": _FakeBackend("evdev"), "x11": _FakeBackend("x11")}
    took = install(pipe, env={"WAYLAND_DISPLAY": "wayland-0"}, log=lambda *a, **k: None,
                   backends=backends)
    assert took == "evdev"
    assert backends["x11"].registered == []
    assert {c for c, _ in backends["evdev"].registered} == {c for c, _ in DEFAULT_BINDINGS}
    assert pipe.hotkey_poll is not None


def test_x11_prefers_the_grab():
    pipe = _FakePipe()
    backends = {"evdev": _FakeBackend("evdev"), "x11": _FakeBackend("x11")}
    took = install(pipe, env={"DISPLAY": ":0"}, log=lambda *a, **k: None, backends=backends)
    assert took == "x11"
    assert backends["evdev"].registered == []


def test_a_refusing_backend_falls_through_to_the_other():
    """No input-group membership is the realistic case: evdev refuses, the grab still works."""
    pipe = _FakePipe()
    backends = {"evdev": _FakeBackend("evdev", fail=True), "x11": _FakeBackend("x11")}
    took = install(pipe, env={"WAYLAND_DISPLAY": "wayland-0"}, log=lambda *a, **k: None,
                   backends=backends)
    assert took == "x11"


def test_no_backend_at_all_is_reported_and_survived():
    """A run without hotkeys is still a run: F1/Space and the A/B timer do not depend on them."""
    pipe = _FakePipe()
    said = []
    took = install(pipe, env={}, log=lambda msg, **k: said.append(msg),
                   backends={"evdev": _FakeBackend("evdev", fail=True),
                             "x11": _FakeBackend("x11", fail=True)})
    assert took is None
    assert pipe.hotkey_poll is None
    assert any("none of the backends" in m for m in said), said


def test_nothing_here_raises():
    pipe = _FakePipe()
    install(pipe, env={"WAYLAND_DISPLAY": "1"}, log=lambda *a, **k: None,
            backends={"evdev": _FakeBackend("evdev", fail=True)})


def test_the_command_is_carried_not_the_combo():
    """The loop dispatches on "toggle"/"quit"; a combo string would be ignored in silence."""
    pipe = _FakePipe()
    backend = _FakeBackend("x11")
    install(pipe, env={"DISPLAY": ":0"}, log=lambda *a, **k: None, backends={"x11": backend})
    for combo, callback in backend.registered:
        callback(combo)
    queued = {pipe.commands.get_nowait() for _ in range(pipe.commands.qsize())}
    assert queued == {"toggle", "quit"}


def test_uninstall_releases_every_backend():
    a, b = _FakeBackend("evdev"), _FakeBackend("x11")
    uninstall(backends={"evdev": a, "x11": b})
    assert a.unregistered == 1 and b.unregistered == 1


def test_uninstall_survives_a_backend_that_raises():
    class Rude(_FakeBackend):
        def unregister_all(self):
            raise RuntimeError("already gone")

    uninstall(backends={"evdev": Rude("evdev")})


def test_the_cli_uses_the_chooser():
    source = open("minimal/__main__.py", encoding="utf-8").read()
    assert "hotkeys_backend.install(pipe)" in source
    assert "from hotkeys_linux import poll_x11_events" not in source, (
        "the X11-only path must not be the one the caller reaches for")
