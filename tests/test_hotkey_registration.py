"""Hotkeys are registered by their name string, not by the binding tuple.

`hotkey_bindings` maps an id to (mods, keysym, command, name). The registration loop iterated
`.items()` and passed the value straight to the registrar, which parses a string - so the first
v1 run that reached it died with "'tuple' object has no attribute 'split'".
"""
from __future__ import annotations

import queue

import pytest

try:
    import sdl2  # noqa: F401
except (ImportError, RuntimeError) as exc:      # pragma: no cover - environment dependent
    pytest.skip(f"pysdl2/SDL2 is unusable here: {exc}", allow_module_level=True)

from hotkeys import build_bindings
from startup_linux import _register_hotkeys


class _State:
    def __init__(self, bindings):
        self.hotkey_bindings = bindings
        self.tray_commands = queue.Queue()


def test_every_binding_is_registered_as_a_string():
    st = _State(build_bindings({"window": "Ctrl+Alt+5"}))
    seen = []

    def register(combo, callback):
        seen.append(combo)
        callback("pressed")

    registered = _register_hotkeys(st, register)

    assert seen, "nothing was registered"
    assert all(isinstance(combo, str) for combo in seen), (
        f"the registrar parses a string; it was handed {[type(c).__name__ for c in seen]}")
    assert "Ctrl+Alt+5" in seen
    assert registered == seen


def test_the_callback_carries_the_command_not_the_id():
    st = _State(build_bindings({"window": "Ctrl+Alt+5"}))
    fired = []

    def register(combo, callback):
        if combo == "Ctrl+Alt+5":
            callback("pressed")

    _register_hotkeys(st, register)
    assert st.tray_commands.get_nowait() == "window", (
        "the queue must receive the command name; the id would be silently ignored by the loop")


def test_a_bad_binding_does_not_stop_the_others():
    st = _State(build_bindings({}))
    calls = []

    def register(combo, callback):
        calls.append(combo)
        if len(calls) == 1:
            raise ValueError("nope")

    registered = _register_hotkeys(st, register)
    assert len(calls) > 1, "one failure must not end the loop"
    assert len(registered) == len(calls) - 1
