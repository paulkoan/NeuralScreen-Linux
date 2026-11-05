"""Global hotkeys by reading kernel input events — the backend that works on Wayland.

WHY THIS EXISTS

`hotkeys_linux.py` grabs keys with XGrabKey. On a Wayland session that cannot work: the
compositor delivers keys to the Wayland client, and nothing reaches XWayland. So a shortcut that
fires on X11 registers happily and then never fires once a Wayland-native window has focus —
which is exactly what happened to Ctrl+Alt+1.

The two "proper" Wayland routes are the GlobalShortcuts portal (a per-shortcut confirmation
dialog, and a D-Bus client this project does not have) and KDE's KGlobalAccel (KDE only, also
D-Bus). Reading /dev/input/event* needs neither: the kernel delivers every keypress to whoever
can read the device, whatever the compositor does with it.

WHAT IT COSTS

Read access to /dev/input/event*. On Arch that is the `input` group:

    sudo usermod -aG input "$USER"      # then log out and back in

That is a one-off, and it is the same grant every global-hotkey tool on Linux uses. Without it
this module raises a message naming the group rather than failing silently.

WHAT IT DOES NOT DO

It reads *all* keyboards and matches on the key, not on where the event went, so a shortcut fires
whether the game, the output window or nothing at all has focus. That is the point. It also means
the keys still reach the focused application — this only watches, it never grabs or consumes.
"""

from __future__ import annotations

import fcntl
import glob
import os
import select
import struct
import sys
from typing import Callable

# ---------------------------------------------------------------------------
# Kernel constants (linux/input-event-codes.h, linux/input.h)
# ---------------------------------------------------------------------------

EV_SYN = 0x00
EV_KEY = 0x01

# value: the press state of a key
KEY_RELEASED = 0
KEY_PRESSED = 1
KEY_REPEAT = 2

# Modifier keycodes. Left and right are separate codes but one logical modifier.
MODIFIER_CODES: dict[str, set[int]] = {
    "Shift": {42, 54},
    "Ctrl": {29, 97},
    "Alt": {56, 100},
    "Meta": {125, 126},
    "Super": {125, 126},
}
_CODE_TO_MOD: dict[int, str] = {
    code: name for name, codes in MODIFIER_CODES.items() for code in codes
    if name != "Super"          # Super is an alias of Meta, not a second modifier
}

# The keys a binding may name. Digits use the top row, which is what a laptop has.
_KEY_CODES: dict[str, int] = {
    "Escape": 1, "Esc": 1,
    "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9, "9": 10, "0": 11,
    "Minus": 12, "Equal": 13, "Backspace": 14, "Tab": 15,
    "Q": 16, "W": 17, "E": 18, "R": 19, "T": 20, "Y": 21, "U": 22, "I": 23, "O": 24, "P": 25,
    "A": 30, "S": 31, "D": 32, "F": 33, "G": 34, "H": 35, "J": 36, "K": 37, "L": 38,
    "Z": 44, "X": 45, "C": 46, "V": 47, "B": 48, "N": 49, "M": 50,
    "Space": 57,
    "F1": 59, "F2": 60, "F3": 61, "F4": 62, "F5": 63, "F6": 64,
    "F7": 65, "F8": 66, "F9": 67, "F10": 68, "F11": 87, "F12": 88,
    "Home": 102, "Up": 103, "PageUp": 104, "Left": 105,
    "Right": 106, "End": 107, "Down": 108, "PageDown": 109,
    "Insert": 110, "Delete": 111,
}

_INPUT_EVENT = struct.Struct("<qqHHi")   # timeval(16) + type(2) + code(2) + value(4)


def _ioc(direction: int, kind: str, number: int, size: int) -> int:
    return (direction << 30) | (size << 16) | (ord(kind) << 8) | number


_IOC_READ = 2
_EVIOCGNAME = _ioc(_IOC_READ, "E", 0x06, 64)          # char[64]
_EVIOCGBIT_KEY = _ioc(_IOC_READ, "E", 0x20 + EV_KEY, 96)   # EV_KEY bitset, 96 bytes


# ---------------------------------------------------------------------------
# Combo parsing and matching — pure, so it is testable without any device
# ---------------------------------------------------------------------------

def parse_combo(combo: str) -> tuple[frozenset[str], int]:
    """'Ctrl+Alt+1' -> ({'Ctrl', 'Alt'}, keycode).

    Raises ValueError naming the offender, because a binding that silently fails to parse is a
    shortcut that silently does nothing.
    """
    parts = [p.strip() for p in combo.split("+") if p.strip()]
    if not parts:
        raise ValueError(f"empty key combination: {combo!r}")
    mods = frozenset(p for p in parts[:-1])
    unknown = mods - set(MODIFIER_CODES)
    if unknown:
        raise ValueError(
            f"unknown modifier(s) {sorted(unknown)} in {combo!r}; "
            f"known: {sorted(set(MODIFIER_CODES) - {'Super'})}")
    key = parts[-1]
    code = _KEY_CODES.get(key)
    if code is None:
        raise ValueError(
            f"unknown key {key!r} in {combo!r}; known: {', '.join(sorted(_KEY_CODES))}")
    return mods, code


class HotkeyMatcher:
    """Turns a stream of key events into fired combos. Holds no file descriptors."""

    def __init__(self) -> None:
        self.bindings: dict[tuple[frozenset[str], int], tuple[str, Callable]] = {}
        self.pressed_mods: set[str] = set()
        self.pressed_keys: set[int] = set()

    def register(self, combo: str, callback: Callable) -> None:
        mods, code = parse_combo(combo)
        self.bindings[(mods, code)] = (combo, callback)

    def clear(self) -> None:
        self.bindings.clear()
        self.pressed_mods.clear()
        self.pressed_keys.clear()

    def feed(self, event_type: int, code: int, value: int) -> list[str]:
        """Feed one input event; returns the combos that fired because of it."""
        if event_type != EV_KEY:
            return []

        if value == KEY_RELEASED:
            self.pressed_keys.discard(code)
            mod = _CODE_TO_MOD.get(code)
            if mod is not None:
                # Only clear the modifier once *both* sides are up: releasing the right Ctrl
                # while the left is still held must not drop "Ctrl".
                still_down = self.pressed_keys & MODIFIER_CODES[mod]
                if not still_down:
                    self.pressed_mods.discard(mod)
            return []

        # Press or repeat. A repeat must not re-fire a toggle.
        if value == KEY_REPEAT:
            return []
        self.pressed_keys.add(code)

        mod = _CODE_TO_MOD.get(code)
        if mod is not None:
            self.pressed_mods.add(mod)
            return []

        fired = []
        for (mods, key_code), (combo, callback) in self.bindings.items():
            if key_code != code:
                continue
            if mods != frozenset(self.pressed_mods):
                # An exact match: Ctrl+Alt+1 must not fire while Shift is also down.
                continue
            fired.append(combo)
            callback(combo)
        return fired


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------

class EvdevHotkeys:
    """Watches every readable keyboard and feeds its events to a HotkeyMatcher."""

    def __init__(self, matcher: HotkeyMatcher | None = None, log=print) -> None:
        self.matcher = matcher or HotkeyMatcher()
        self.log = log
        self.devices: list[tuple[int, str]] = []
        self.queued: list[str] = []

    # -- discovery ---------------------------------------------------------

    @staticmethod
    def _device_is_keyboard(fd: int) -> bool:
        """True when the device reports ordinary letter keys.

        A power button, a lid switch and a mouse all appear as /dev/input/event*, and reading
        them costs a thread each and yields nothing. Letters are the cheapest confident test.
        """
        try:
            bits = bytearray(96)
            fcntl.ioctl(fd, _EVIOCGBIT_KEY, bits, True)
        except OSError:
            return False
        # A(30), Z(44), Space(57) must all be present.
        for code in (30, 44, 57):
            if not bits[code // 8] & (1 << (code % 8)):
                return False
        return True

    @staticmethod
    def _device_name(fd: int) -> str:
        try:
            name = fcntl.ioctl(fd, _EVIOCGNAME, b"\0" * 64)
            return name.split(b"\0", 1)[0].decode("utf-8", "replace")
        except OSError:
            return "?"

    def open_devices(self) -> None:
        """Open every keyboard we may read. Raises RuntimeError when none can be opened."""
        refused = []
        for path in sorted(glob.glob("/dev/input/event*")):
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            except OSError as exc:
                refused.append(f"{path} ({exc.strerror})")
                continue
            if not self._device_is_keyboard(fd):
                os.close(fd)
                continue
            self.devices.append((fd, self._device_name(fd)))
        if not self.devices:
            detail = ("; ".join(refused) if refused
                      else "no /dev/input/event* present")
            raise RuntimeError(
                "no readable keyboard in /dev/input. Either the device node is absent "
                f"({detail}), or this user cannot read it — global hotkeys need the input "
                "group:\n    sudo usermod -aG input \"$USER\"   # then log out and back in")

    # -- polling -----------------------------------------------------------

    def poll(self, block: bool = False) -> list[str]:
        """Drain ready devices; returns combos fired since the last call."""
        if not self.devices:
            return []
        ready, _, _ = select.select([fd for fd, _ in self.devices], [], [],
                                    0.05 if block else 0)
        fired: list[str] = []
        for fd in ready:
            try:
                data = os.read(fd, _INPUT_EVENT.size * 64)
            except BlockingIOError:
                continue
            except OSError as exc:
                self.log(f"hotkeys: read failed on a device ({exc}); dropping it")
                self._drop(fd)
                continue
            for offset in range(0, len(data) - _INPUT_EVENT.size + 1, _INPUT_EVENT.size):
                _sec, _usec, etype, code, value = _INPUT_EVENT.unpack_from(data, offset)
                fired.extend(self.matcher.feed(etype, code, value))
        self.queued.extend(fired)
        return fired

    def _drop(self, fd: int) -> None:
        self.devices = [(f, name) for f, name in self.devices if f != fd]
        try:
            os.close(fd)
        except OSError:
            pass

    def close(self) -> None:
        for fd, _name in self.devices:
            try:
                os.close(fd)
            except OSError:
                pass
        self.devices = []


# ---------------------------------------------------------------------------
# Module-level API, mirroring hotkeys_linux so the caller does not care which
# ---------------------------------------------------------------------------

_mine: EvdevHotkeys | None = None


def register_global_hotkey(combo: str, callback: Callable) -> None:
    """Register a global hotkey. Same signature as the X11 backend."""
    global _mine
    if _mine is None:
        _mine = EvdevHotkeys()
        _mine.open_devices()
        names = ", ".join(name for _fd, name in _mine.devices)
        print(f"hotkeys: reading {len(_mine.devices)} keyboard(s) via evdev: {names}",
              file=sys.stderr)
    _mine.matcher.register(combo, callback)


def poll_events(block: bool = False) -> list[str]:
    """Called from the frame loop. Returns anything that fired."""
    return _mine.poll(block=block) if _mine is not None else []


def unregister_all() -> None:
    global _mine
    if _mine is not None:
        _mine.close()
        _mine.matcher.clear()
        _mine = None
