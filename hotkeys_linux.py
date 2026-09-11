"""
hotkeys_linux.py — X11 global hotkeys for NeuralScreen.

Replaces Windows RegisterHotKey with XGrabKey via ctypes/libX11.

Key combinations like ``Num1`` or ``Ctrl+Alt+Q`` are mapped to X11
keysyms and modifiers, then grabbed globally through XGrabKey so the
application receives key events even when unfocused.

Limitations
-----------
- **Wayland**: The X11 XGrabKey API does not work under Wayland.
  There is no portable Wayland equivalent for global hotkeys; compositor-
  specific solutions (e.g. sway-mode, KDE DBus) would be needed.
- **Permissions**: XGrabKey requires access to the X11 display.  On
  modern systems $DISPLAY and $XAUTHORITY must be set correctly.

Usage
-----
    def on_activate(key_name):
        print(f"Hotkey {key_name} triggered!")

    register_global_hotkey("Num1", on_activate)
    register_global_hotkey("Ctrl+Alt+Q", on_activate)

    # In your event loop:
    from hotkeys_linux import poll_x11_events
    while running:
        poll_x11_events(block=False)

    # Cleanup
    unregister_all()
"""

from __future__ import annotations

import os
import sys
import time
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Keysym table — maps human-readable names to X11 keysym codes
# ---------------------------------------------------------------------------

# Keypad keys
KP_KEYS: dict[str, int] = {
    "Num0": 0xFFB0, "Num1": 0xFFB1, "Num2": 0xFFB2, "Num3": 0xFFB3,
    "Num4": 0xFFB4, "Num5": 0xFFB5, "Num6": 0xFFB6, "Num7": 0xFFB7,
    "Num8": 0xFFB8, "Num9": 0xFFB9,
    "NumLock": 0xFF7F,
    "NumDivide": 0xFFAF, "NumMultiply": 0xFFAA,
    "NumSubtract": 0xFFAD, "NumAdd": 0xFFAB,
    "NumEnter": 0xFF8D, "NumDecimal": 0xFFAE,
}

# Alphanumeric and function keys
BASIC_KEYS: dict[str, int] = {
    "BackSpace": 0xFF08, "Tab": 0xFF09, "Return": 0xFF0D,
    "Escape": 0xFF1B,
    "F1": 0xFFBE, "F2": 0xFFBF, "F3": 0xFFC0, "F4": 0xFFC1,
    "F5": 0xFFC2, "F6": 0xFFC3, "F7": 0xFFC4, "F8": 0xFFC5,
    "F9": 0xFFC6, "F10": 0xFFC7, "F11": 0xFFC8, "F12": 0xFFC9,
    "F13": 0xFFCA, "F14": 0xFFCB, "F15": 0xFFCC, "F16": 0xFFCD,
    "F17": 0xFFCE, "F18": 0xFFCF, "F19": 0xFFD0, "F20": 0xFFD1,
    "F21": 0xFFD2, "F22": 0xFFD3, "F23": 0xFFD4, "F24": 0xFFD5,
    "Print": 0xFF61, "ScrollLock": 0xFF14, "Pause": 0xFF13,
    "Insert": 0xFF63, "Delete": 0xFF66, "Home": 0xFF50,
    "End": 0xFF57, "PageUp": 0xFF55, "PageDown": 0xFF56,
    "Left": 0xFF51, "Up": 0xFF52, "Right": 0xFF53, "Down": 0xFF54,
    "Space": 0x0020,
    "A": 0x0041, "B": 0x0042, "C": 0x0043, "D": 0x0044,
    "E": 0x0045, "F": 0x0046, "G": 0x0047, "H": 0x0048,
    "I": 0x0049, "J": 0x004A, "K": 0x004B, "L": 0x004C,
    "M": 0x004D, "N": 0x004E, "O": 0x004F, "P": 0x0050,
    "Q": 0x0051, "R": 0x0052, "S": 0x0053, "T": 0x0054,
    "U": 0x0055, "V": 0x0056, "W": 0x0057, "X": 0x0058,
    "Y": 0x0059, "Z": 0x005A,
    "0": 0x0030, "1": 0x0031, "2": 0x0032, "3": 0x0033,
    "4": 0x0034, "5": 0x0035, "6": 0x0036, "7": 0x0037,
    "8": 0x0038, "9": 0x0039,
    "Grave": 0x0060, "Minus": 0x002D, "Equal": 0x003D,
    "BracketLeft": 0x005B, "BracketRight": 0x005D,
    "Semicolon": 0x003B, "Quote": 0x0027, "Comma": 0x002C,
    "Period": 0x002E, "Slash": 0x002F, "Backslash": 0x005C,
}

# Merge all key names into one lookup
ALL_KEYS: dict[str, int] = {}
ALL_KEYS.update(KP_KEYS)
ALL_KEYS.update(BASIC_KEYS)

# ---------------------------------------------------------------------------
# Modifier mapping
# ---------------------------------------------------------------------------

MOD_MAP: dict[str, int] = {
    "Ctrl":    1 << 2,   # ControlMask
    "Alt":     1 << 3,   # Mod1Mask
    "Shift":   1 << 0,   # ShiftMask
    "Meta":    1 << 6,   # Mod4Mask (common for Super/Windows key)
    "Super":   1 << 6,   # Mod4Mask
}

def _parse_key_combo(combo: str) -> tuple[int, int]:
    """Parse ``'Ctrl+Alt+Q'`` → ``(keysym, modmask)``.

    The last token before '+' is the key name; everything before is a
    modifier.  Raises ``ValueError`` on unknown key or modifier.
    """
    parts = combo.split("+")
    if len(parts) < 1:
        raise ValueError(f"Empty key combo: {combo!r}")

    key_name = parts[-1]
    mods = parts[:-1]

    keysym = ALL_KEYS.get(key_name)
    if keysym is None:
        raise ValueError(
            f"Unknown key: {key_name!r}.  Known keys: "
            f"{', '.join(sorted(ALL_KEYS.keys()))}"
        )

    modmask = 0
    for m in mods:
        bit = MOD_MAP.get(m)
        if bit is None:
            raise ValueError(
                f"Unknown modifier: {m!r}.  Known: {', '.join(MOD_MAP)}"
            )
        modmask |= bit

    return keysym, modmask


# ---------------------------------------------------------------------------
# X11 ctypes setup
# ---------------------------------------------------------------------------

import ctypes
import ctypes.util

_LIBX11_PATH = ctypes.util.find_library("X11")
if _LIBX11_PATH is None:
    raise RuntimeError(
        "libX11 not found. Install: sudo apt install libx11-dev"
    )

_lib = ctypes.CDLL(_LIBX11_PATH, use_errno=True)

# --- function signatures ---

_lib.XOpenDisplay.restype = ctypes.c_void_p
_lib.XOpenDisplay.argtypes = [ctypes.c_char_p]

_lib.XDefaultRootWindow.restype = ctypes.c_ulong
_lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]

_lib.XInternAtom.restype = ctypes.c_ulong
_lib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]

_lib.XGrabKey.argtypes = [
    ctypes.c_void_p,     # Display *
    ctypes.c_int,         # keycode
    ctypes.c_uint,        # modifiers
    ctypes.c_ulong,       # grab_window
    ctypes.c_int,         # owner_events
    ctypes.c_int,         # pointer_mode
    ctypes.c_int,         # keyboard_mode
]
_lib.XGrabKey.restype = ctypes.c_int

_lib.XUngrabKey.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_uint,
    ctypes.c_ulong,
]
_lib.XUngrabKey.restype = ctypes.c_int

_lib.XKeysymToKeycode.restype = ctypes.c_ubyte  # KeyCode is unsigned byte
_lib.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]

_lib.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_lib.XNextEvent.restype = ctypes.c_int

_lib.XPending.argtypes = [ctypes.c_void_p]
_lib.XPending.restype = ctypes.c_int

_lib.XCloseDisplay.argtypes = [ctypes.c_void_p]
_lib.XCloseDisplay.restype = ctypes.c_int

_lib.XFlush.argtypes = [ctypes.c_void_p]
_lib.XFlush.restype = ctypes.c_int

_lib.XFree.argtypes = [ctypes.c_void_p]
_lib.XFree.restype = ctypes.c_int

# --- X11 constants ---
GrabModeAsync = 1
KeyPressMask = 1 << 0
KeyReleaseMask = 1 << 1

# ---------------------------------------------------------------------------
# Event structure (XKeyPressedEvent / XKeyEvent subset)
# ---------------------------------------------------------------------------

class XKeyEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("window", ctypes.c_ulong),
        ("root", ctypes.c_ulong),
        ("subwindow", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("x_root", ctypes.c_int),
        ("y_root", ctypes.c_int),
        ("state", ctypes.c_uint),
        ("keycode", ctypes.c_ubyte),
        ("same_screen", ctypes.c_int),
    ]


class XEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("xkey", XKeyEvent),
        # We only care about key events; the rest of the union is ignored
        ("pad", ctypes.c_char * 24 * 8),
    ]


# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

_display: Optional[ctypes.c_void_p] = None
_registered: list[tuple[int, int, str, Callable]] = []
_running = False


def _ensure_display() -> ctypes.c_void_p:
    """Open (or return cached) X11 display connection."""
    global _display
    if _display is not None:
        return _display
    display_name = os.environ.get("DISPLAY")
    _display = _lib.XOpenDisplay(
        ctypes.c_char_p(display_name.encode() if display_name else None)
    )
    if not _display:
        raise RuntimeError(
            f"Cannot open X11 display ({display_name or 'unset'}). "
            "Set $DISPLAY and $XAUTHORITY, or run under X11."
        )
    return _display


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register_global_hotkey(key_combo: str, callback: Callable) -> None:
    """Register a global hotkey.

    Args:
        key_combo: e.g. ``'Num1'``, ``'Ctrl+Alt+Q'``, ``'Shift+F5'``.
        callback: Called with the key_combo string when the hotkey fires.
    """
    keysym, modmask = _parse_key_combo(key_combo)

    disp = _ensure_display()
    root = _lib.XDefaultRootWindow(disp)
    keycode = _lib.XKeysymToKeycode(disp, keysym)

    if keycode == 0:
        raise ValueError(f"No keycode for keysym 0x{keysym:04X} ({key_combo})")

    # Grab with and without NumLock / CapsLock / ScrollLock to catch
    # all modifier states (common pattern for robust global hotkeys).
    for extra in (0,
                  1 << 1,    # LockMask (CapsLock)
                  1 << 4,    # Mod2Mask (NumLock on many systems)
                  1 << 5,    # Mod3Mask
                  1 << 6,    # Mod4Mask (Super/Win)
                  ):
        # Skip the extra if it's already part of the user's specified modifiers
        if extra & modmask:
            continue

        full_mask = modmask | extra
        _lib.XGrabKey(
            disp,
            keycode,
            full_mask,
            root,
            1,  # owner_events = True (let the app also receive normal input)
            GrabModeAsync,
            GrabModeAsync,
        )

    _lib.XFlush(disp)

    _registered.append((keycode, modmask, key_combo, callback))


def unregister_all() -> None:
    """Remove all registered global hotkeys.

    Safe to call even when no hotkeys are registered.
    """
    global _display
    if _display is None:
        return

    root = _lib.XDefaultRootWindow(_display)

    # Collect unique (keycode, base_modmask) pairs
    ungrab_set: set[tuple[int, int]] = set()
    for kc, modmask, _, _ in _registered:
        ungrab_set.add((kc, modmask))

    for kc, modmask in ungrab_set:
        for extra in (0, 1 << 1, 1 << 4, 1 << 5, 1 << 6):
            if extra & modmask:
                continue
            _lib.XUngrabKey(_display, kc, modmask | extra, root)

    _lib.XFlush(_display)
    _registered.clear()


def poll_x11_events(block: bool = True) -> None:
    """Check X11 event queue and dispatch any pending hotkey presses.

    Call this from your main loop (e.g. every frame).  When *block* is
    True (default) the call blocks until at least one event arrives.

    Only processes KeyPress events for grabbed keys; all other events
    are discarded.
    """
    disp = _ensure_display()

    if block:
        event = XEvent()
        _lib.XNextEvent(disp, ctypes.byref(event))
        _handle_one_event(event)
    else:
        while _lib.XPending(disp):
            event = XEvent()
            _lib.XNextEvent(disp, ctypes.byref(event))
            _handle_one_event(event)


# ---------------------------------------------------------------------------
# Internal event dispatch
# ---------------------------------------------------------------------------

def _keycode_to_combo(keycode: int, state: int) -> Optional[str]:
    """Return the key combo string for a keycode + modifier state, or None."""
    for kc, modmask, combo, _ in _registered:
        if kc == keycode and (state & modmask) == modmask:
            return combo
    return None


def _handle_one_event(event: XEvent) -> None:
    """Dispatch a single X11 event if it matches a registered hotkey."""
    # KeyPress = 2
    if event.type != 2:
        return

    xke = event.xkey
    combo = _keycode_to_combo(xke.keycode, xke.state)
    if combo is None:
        return

    for kc, modmask, c, cb in _registered:
        if c == combo:
            try:
                cb(combo)
            except Exception:
                import traceback
                traceback.print_exc()
            break


# ---------------------------------------------------------------------------
# CLI test mode
# ---------------------------------------------------------------------------

def _test() -> None:
    """Print available keys and modifiers, register a few hotkeys, then wait."""
    print("=== hotkeys_linux.py self-test ===")
    print()
    print(f"Display: {os.environ.get('DISPLAY', 'unset')}")
    print(f"libX11:  {_LIBX11_PATH}")
    print()

    # Validate parsing
    test_combos = ["Num1", "Num2", "Ctrl+Alt+Q", "Shift+F5", "Ctrl+Space"]
    print("--- Key combo parsing ---")
    for combo in test_combos:
        try:
            ks, mm = _parse_key_combo(combo)
            print(f"  {combo:20s} → keysym=0x{ks:04X}  modmask=0x{mm:04X}")
        except ValueError as e:
            print(f"  {combo:20s} → ERROR: {e}")

    print()
    print("--- Registering test hotkeys ---")
    _callbacks: list[str] = []

    if not os.environ.get("DISPLAY"):
        print("  SKIPPING: no X11 display ($DISPLAY not set)")
        return

    def _on_num1(name: str) -> None:
        _callbacks.append(name)
        print(f"  🔥 HOTKEY: {name}")

    def _on_ctrlq(name: str) -> None:
        _callbacks.append(name)
        print(f"  🔥 HOTKEY: {name}")

    try:
        register_global_hotkey("Num1", _on_num1)
        register_global_hotkey("Ctrl+Alt+Q", _on_ctrlq)
        print("  Registered Num1, Ctrl+Alt+Q")
    except RuntimeError as e:
        print(f"  SKIPPING: {e}")
        return
    print()
    print("Now polling X11 events for 10 seconds...")
    print("Press Num1 or Ctrl+Alt+Q to test.")
    print()

    deadline = time.monotonic() + 10
    count = 0
    while time.monotonic() < deadline:
        poll_x11_events(block=False)
        time.sleep(0.05)
        count += 1
        if count % 100 == 0:
            print(f"  ... polled {count} times, {len(_callbacks)} hotkey(s) fired")

    unregister_all()
    print()
    print(f"Test complete. {len(_callbacks)} hotkey(s) received.")
    print("Cleanup: unregister_all() called.")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _test()
    else:
        print(
            "hotkeys_linux.py — X11 global hotkeys library.\n"
            "Run with --test to register test hotkeys and poll for 10 seconds."
        )