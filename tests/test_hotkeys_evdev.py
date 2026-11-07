"""The evdev hotkey backend: parsing, matching, and the modifier edge cases.

The bug this backend exists to fix was Ctrl+Alt+1 registering and never firing. The risk in the
replacement is subtler: a matcher that fires on the wrong modifier combination, or that misses a
press because it tracked the wrong side of a modifier key. Neither needs a device to test.
"""
from __future__ import annotations

import struct

import pytest

from hotkeys_evdev import (EV_KEY, EV_SYN, KEY_PRESSED, KEY_RELEASED, KEY_REPEAT,
                           HotkeyMatcher, parse_combo)

CTRL, ALT, SHIFT, META = 29, 56, 42, 125
RCTRL, RALT, RSHIFT = 97, 100, 54
KEY_1, KEY_Q, KEY_F1 = 2, 16, 59


def test_a_combo_parses_into_modifiers_and_a_key():
    assert parse_combo("Ctrl+Alt+1") == (frozenset({"Ctrl", "Alt"}), KEY_1)
    assert parse_combo("Ctrl+Alt+Q") == (frozenset({"Ctrl", "Alt"}), KEY_Q)
    assert parse_combo("F1") == (frozenset(), KEY_F1)


def test_a_bad_combo_says_what_is_wrong():
    with pytest.raises(ValueError, match="unknown key"):
        parse_combo("Ctrl+Alt+Banana")
    with pytest.raises(ValueError, match="unknown modifier"):
        parse_combo("Hyper+1")
    with pytest.raises(ValueError, match="empty"):
        parse_combo("   ")


def _press(m, *codes):
    for code in codes:
        m.feed(EV_KEY, code, KEY_PRESSED)


def _release(m, *codes):
    for code in codes:
        m.feed(EV_KEY, code, KEY_RELEASED)


def test_the_combo_fires_when_it_is_held_down():
    m = HotkeyMatcher()
    fired = []
    m.register("Ctrl+Alt+1", lambda combo: fired.append(combo))
    _press(m, CTRL, ALT)
    assert m.feed(EV_KEY, KEY_1, KEY_PRESSED) == ["Ctrl+Alt+1"]
    assert fired == ["Ctrl+Alt+1"]


def test_the_key_alone_does_not_fire():
    m = HotkeyMatcher()
    m.register("Ctrl+Alt+1", lambda combo: None)
    assert m.feed(EV_KEY, KEY_1, KEY_PRESSED) == []


def test_an_extra_modifier_does_not_fire():
    """Ctrl+Alt+Shift+1 is a different combination, and acting on it would surprise."""
    m = HotkeyMatcher()
    m.register("Ctrl+Alt+1", lambda combo: None)
    _press(m, CTRL, ALT, SHIFT)
    assert m.feed(EV_KEY, KEY_1, KEY_PRESSED) == []


def test_the_either_side_modifiers_are_the_same_modifier():
    m = HotkeyMatcher()
    m.register("Ctrl+Alt+1", lambda combo: None)
    _press(m, RCTRL, RALT)
    assert m.feed(EV_KEY, KEY_1, KEY_PRESSED) == ["Ctrl+Alt+1"]


def test_releasing_one_ctrl_while_the_other_is_held_keeps_ctrl():
    """The classic modifier-tracking bug: both sides map to one modifier."""
    m = HotkeyMatcher()
    m.register("Ctrl+Alt+1", lambda combo: None)
    _press(m, CTRL, RCTRL, ALT)
    _release(m, RCTRL)
    assert m.feed(EV_KEY, KEY_1, KEY_PRESSED) == ["Ctrl+Alt+1"], (
        "the left Ctrl is still down, so Ctrl is still held")


def test_releasing_the_last_ctrl_clears_it():
    m = HotkeyMatcher()
    m.register("Ctrl+Alt+1", lambda combo: None)
    _press(m, CTRL, ALT)
    _release(m, CTRL)
    assert m.feed(EV_KEY, KEY_1, KEY_PRESSED) == []


def test_an_auto_repeat_does_not_toggle_again():
    """Holding the key must not flip the enhancement back and forth at the repeat rate."""
    m = HotkeyMatcher()
    fired = []
    m.register("Ctrl+Alt+1", lambda combo: fired.append(combo))
    _press(m, CTRL, ALT)
    m.feed(EV_KEY, KEY_1, KEY_PRESSED)
    for _ in range(5):
        m.feed(EV_KEY, KEY_1, KEY_REPEAT)
    assert fired == ["Ctrl+Alt+1"]


def test_only_key_events_are_considered():
    m = HotkeyMatcher()
    m.register("Ctrl+Alt+1", lambda combo: None)
    _press(m, CTRL, ALT)
    assert m.feed(EV_SYN, KEY_1, KEY_PRESSED) == []


def test_two_bindings_do_not_cross_fire():
    m = HotkeyMatcher()
    fired = []
    m.register("Ctrl+Alt+1", lambda combo: fired.append("toggle"))
    m.register("Ctrl+Alt+Q", lambda combo: fired.append("quit"))
    _press(m, CTRL, ALT)
    m.feed(EV_KEY, KEY_Q, KEY_PRESSED)
    assert fired == ["quit"]


def test_poll_with_no_devices_is_quiet():
    from hotkeys_evdev import EvdevHotkeys
    reader = EvdevHotkeys()
    assert reader.poll() == []


def test_an_input_event_is_24_bytes():
    """The parser slices the read buffer by this size; a wrong size desynchronises everything."""
    from hotkeys_evdev import _INPUT_EVENT
    assert _INPUT_EVENT.size == 24
    packed = _INPUT_EVENT.pack(1, 2, EV_KEY, KEY_1, KEY_PRESSED)
    assert len(packed) == 24
    assert _INPUT_EVENT.unpack(packed)[2:] == (EV_KEY, KEY_1, KEY_PRESSED)


def test_missing_device_nodes_name_the_group_to_join(monkeypatch):
    """A silent no-op shortcut is worse than a message that says what to do."""
    import hotkeys_evdev
    monkeypatch.setattr(hotkeys_evdev.glob, "glob", lambda pattern: [])
    reader = hotkeys_evdev.EvdevHotkeys()
    with pytest.raises(RuntimeError, match="input group"):
        reader.open_devices()
