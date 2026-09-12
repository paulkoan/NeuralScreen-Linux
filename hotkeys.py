"""HotkeyController — global hotkeys on Linux via XGrabKey + polling.

Maintains a binding table (command → keysym) and registers each combo
through XGrabKey.  The same default key layout as the Windows version:

    Num1  = toggle NR       Num4  = resolution down
    Num2  = menu toggle     Num6  = resolution up
    Num3  = screenshot      Num5  = capture window under cursor
    Num0  = record          Ctrl+Alt+Q = quit

All mods are registered with NumLock/CapsLock/ScrollLock variants so
they fire regardless of lock-state.

Wayland: XGrabKey does not work.  The overlay SDL window still receives
key events when focused — hotkeys work while the menu is open.
"""

from __future__ import annotations

import queue
import sys
import threading
import time

try:
    from hotkeys_linux import register_global_hotkey, unregister_all, poll_x11_events
    from hotkeys_linux import _parse_key_combo as _parse_keysym
    _HOTKEYS_AVAILABLE = True
except ImportError:
    _HOTKEYS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Key constants (Linux keysyms — same as hotkeys_linux.py)
# ---------------------------------------------------------------------------

# Numpad keysyms
KP_BASE = 0xFFB0
KP = {n: KP_BASE + n for n in range(10)}  # KP_0 = 0xFFB0 .. KP_9 = 0xFFB9
KP_DECIMAL   = 0xFFAE
KP_MULTIPLY  = 0xFFAA
KP_ADD       = 0xFFAB
KP_SUBTRACT  = 0xFFAD
KP_DIVIDE    = 0xFFAF

# Modifier masks (X11 modifier indices)
MOD_ALT     = 0x0008  # Mod1Mask
MOD_CONTROL = 0x0004  # ControlMask
MOD_SHIFT   = 0x0001  # ShiftMask
MOD_META    = 0x0020  # reserved for Mod2Mask — used on some layouts
MOD_NOREPEAT = 0x0000  # no X11 equivalent; we use XGrabKey (auto-repeat off)

# Modifier names for parse_binding
_MOD_NAMES = {
    "CTRL":   MOD_CONTROL,
    "CONTROL": MOD_CONTROL,
    "ALT":    MOD_ALT,
    "SHIFT":  MOD_SHIFT,
    "META":   MOD_META,
    "SUPER":  MOD_META,
}

# Key name → keysym lookup (same keys as Windows version for cross-compat)
_KEY_NAMES: dict[str, int] = {}
for n in range(10):
    _KEY_NAMES[f"NUM{n}"] = KP[n]
_KEY_NAMES.update({
    "NUM0": KP[0], "NUM1": KP[1], "NUM2": KP[2], "NUM3": KP[3],
    "NUM4": KP[4], "NUM5": KP[5], "NUM6": KP[6], "NUM7": KP[7],
    "NUM8": KP[8], "NUM9": KP[9],
    "NUMDOT": KP_DECIMAL, "NUMMUL": KP_MULTIPLY, "NUMMINUS": KP_SUBTRACT,
    "NUMPLUS": KP_ADD, "NUMDIV": KP_DIVIDE,
    # Function keys
    "F1": 0xFFBE, "F2": 0xFFBF, "F3": 0xFFC0, "F4": 0xFFC1,
    "F5": 0xFFC2, "F6": 0xFFC3, "F7": 0xFFC4, "F8": 0xFFC5,
    "F9": 0xFFC6, "F10": 0xFFC7, "F11": 0xFFC8, "F12": 0xFFC9,
    # Navigation
    "INSERT": 0xFF63, "HOME": 0xFF50, "END": 0xFF57,
    "PAGEUP": 0xFF55, "PAGEDOWN": 0xFF56,
    "DELETE": 0xFFFF, "BACKSPACE": 0xFF08, "ESCAPE": 0xFF1B,
    "SPACE": 0x0020, "RETURN": 0xFF0D, "TAB": 0xFF09,
    # Letters (uppercase A-Z map to lowercase X keysyms)
    "Q": 0x0071,  # X11 lowercase q
})

# Default bindings — same as the Windows version but with Linux keysyms
# id -> (mods, keysym, command, human-readable name)
DEFAULT_BINDINGS: dict[int, tuple[int, int, str, str]] = {
    1: (MOD_NOREPEAT, KP[1], "toggle", "Num1"),
    2: (MOD_NOREPEAT, KP[2], "settings", "Num2"),
    3: (MOD_NOREPEAT, KP[6], "scale_up", "Num6"),
    4: (MOD_NOREPEAT, KP[4], "scale_down", "Num4"),
    5: (MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, 0x0071, "quit", "Ctrl+Alt+Q"),
    6: (MOD_NOREPEAT, KP[0], "record", "Num0"),
    7: (MOD_NOREPEAT, KP[3], "screenshot_menu", "Num3"),
    8: (MOD_NOREPEAT, KP[5], "window", "Num5"),
}


# ---------------------------------------------------------------------------
# Binding management (cross-platform, same as Windows version)
# ---------------------------------------------------------------------------

def parse_binding(text: str) -> tuple[int, int] | None:
    """Parse 'Ctrl+Alt+Q', 'Num1', 'F10' → (mods_mask, keysym)."""
    if not text:
        return None
    stripped = text.strip()
    if stripped.startswith("+") or stripped.endswith("+"):
        return None
    parts = [p.strip().upper() for p in stripped.split("+") if p.strip()]
    if not parts:
        return None
    mods = 0
    for p in parts[:-1]:
        m = _MOD_NAMES.get(p)
        if m is None:
            return None
        mods |= m
    vk = _KEY_NAMES.get(parts[-1])
    if vk is None:
        return None
    return mods, vk


def build_bindings(overrides: dict | None = None) -> dict:
    """Bindings dict with user overrides applied.

    overrides: {"toggle": "F10", "record": "Insert", ...}  command → string.
    Unknown commands or unparseable strings are silently ignored.
    """
    bindings = {hk_id: tuple(entry) for hk_id, entry in DEFAULT_BINDINGS.items()}
    if not overrides:
        return bindings
    for hk_id, (mods, vk, cmd, name) in list(bindings.items()):
        text = overrides.get(cmd)
        if not text:
            continue
        parsed = parse_binding(text)
        if parsed is None:
            continue
        new_mods, new_vk = parsed
        bindings[hk_id] = (new_mods, new_vk, cmd, text)
    return bindings


def describe(bindings: dict | None = None) -> str:
    """Human-readable summary like 'Num1=toggle, Num2=settings, ...'."""
    src = bindings or DEFAULT_BINDINGS
    return ", ".join(f"{name}={cmd}" for _, (_, _, cmd, name) in sorted(src.items()))


def numlock_on() -> bool:
    """Not applicable on Linux (XGrabKey registers lock-state variants)."""
    return True


def numlock_needed(bindings: dict | None = None) -> list:
    """Not applicable on Linux."""
    return []


# ---------------------------------------------------------------------------
# HotkeyController — the class commands.py and main_linux.py expect
# ---------------------------------------------------------------------------

class HotkeyController:
    """Drives the hotkey thread that registers + polls X11 hotkeys.

    Matches the Windows HotkeyController interface:
        hk = HotkeyController(bindings, cmd_queue)
        hk.start()
        hk.suspend() / hk.resume() / hk.rebind(new_bindings)
        hk.stop()
    """

    def __init__(self, bindings: dict, cmd_queue: queue.Queue):
        self._bindings = dict(bindings)
        self._cmd_queue = cmd_queue
        self._thread: threading.Thread | None = None
        self._running = False

    def _callback_for(self, cmd: str):
        """Return a function that pushes cmd to the queue."""
        def _on(name: str = ""):
            self._cmd_queue.put(cmd)
        return _on

    def _worker(self):
        """Thread body: register all hotkeys, then poll for events."""
        for hk_id, (mods, keysym, cmd, name) in self._bindings.items():
            if _HOTKEYS_AVAILABLE:
                register_global_hotkey(name, self._callback_for(cmd))
            print(f"[hotkeys] registered: {name} → {cmd}")
        # Poll loop (X11)
        while self._running:
            try:
                if _HOTKEYS_AVAILABLE:
                    poll_x11_events(block=False)
                time.sleep(0.01)  # 10 ms — matches the original polling rate
            except Exception:
                time.sleep(0.1)

    def start(self):
        if self._thread is not None:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def suspend(self):
        """Unregister and stop the polling loop."""
        self._running = False
        if _HOTKEYS_AVAILABLE:
            pass  # unregister_all called in stop()

    def resume(self):
        """Re-register and restart polling."""
        if self._thread is not None and not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def rebind(self, new_bindings: dict):
        """Replace the binding table and restart."""
        self._bindings = dict(new_bindings)
        self.suspend()
        if _HOTKEYS_AVAILABLE:
            unregister_all()
        self.resume()

    def stop(self):
        """Clean shutdown."""
        self._running = False
        if _HOTKEYS_AVAILABLE:
            unregister_all()
        self._thread = None