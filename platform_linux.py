"""
platform_linux.py — Linux (X11) window management for NeuralScreen.

Replaces Win32 winapi.py functions with subprocess(xdotool) calls and
lower-overhead ctypes/libX11 fallbacks.

All public functions take/return Python types; subprocess details are
internal.  Raises RuntimeError on X11 unavailability or xdotool failure.

Wayland note:
  window_under_cursor() is fundamentally limited — Wayland's security
  model hides pointer positions from clients.  The function will still
  attempt X11 paths, but on a pure-Wayland session it returns None.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# X11 availability check
# ---------------------------------------------------------------------------

_HAS_X11: bool | None = None


def _check_x11() -> bool:
    """Return True if a working X11 display is available.

    Checks $DISPLAY is set (fails fast under pure Wayland) and that
    `xdotool` is on PATH.
    """
    global _HAS_X11
    if _HAS_X11 is not None:
        return _HAS_X11

    if not os.environ.get("DISPLAY"):
        _HAS_X11 = False
        return False

    try:
        subprocess.run(
            ["xdotool", "--version"],
            capture_output=True,
            timeout=5,
        )
        _HAS_X11 = True
    except (FileNotFoundError, subprocess.SubprocessError):
        _HAS_X11 = False
    return _HAS_X11


def _require_x11() -> None:
    if not _check_x11():
        raise RuntimeError(
            "No X11 display or xdotool not found. "
            "Install: sudo apt install xdotool  (or xdotool on your distro)."
        )


# ---------------------------------------------------------------------------
# xdotool helpers
# ---------------------------------------------------------------------------

def _xdotool(*args: str, timeout: int = 10) -> str:
    """Run xdotool with *args, return stripped stdout or raise."""
    _require_x11()
    try:
        proc = subprocess.run(
            ["xdotool", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise RuntimeError("xdotool not installed (apt install xdotool)")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"xdotool {' '.join(args)} timed out")

    if proc.returncode != 0:
        err = proc.stderr.strip()
        raise RuntimeError(f"xdotool error: {err or proc.returncode}")
    return proc.stdout.strip()


# ---------------------------------------------------------------------------
# Public API — window management
# ---------------------------------------------------------------------------

def list_capturable_windows() -> list[dict]:
    """Return all visible windows, each: {id: int, title: str}.

    Uses ``xdotool search --onlyvisible`` — this excludes unmapped,
    shaded, or iconified windows.  The root/desktop window is filtered
    out when the window manager names it (e.g. "Desktop", "root").
    """
    win_ids_str = _xdotool("search", "--onlyvisible", "--name", "", timeout=10)
    if not win_ids_str:
        return []

    windows: list[dict] = []
    for wid_str in win_ids_str.splitlines():
        wid_str = wid_str.strip()
        if not wid_str:
            continue
        try:
            wid = int(wid_str)
        except ValueError:
            continue
        # fetch title for each window individually
        try:
            title = _xdotool("getwindowname", str(wid), timeout=5)
        except RuntimeError:
            title = ""
        windows.append({"id": wid, "title": title})

    return windows


def window_frame_rect(window_id: int) -> tuple[int, int, int, int]:
    """Return ``(x, y, width, height)`` of *window_id*'s frame.

    Uses ``xdotool getwindowgeometry --shell`` which reports the window
    position (including window-manager decorations on most WMs).
    """
    out = _xdotool("getwindowgeometry", "--shell", str(window_id), timeout=5)
    x = y = w = h = 0
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("X="):
            x = int(line[2:])
        elif line.startswith("Y="):
            y = int(line[2:])
        elif line.startswith("WIDTH="):
            w = int(line[6:])
        elif line.startswith("HEIGHT="):
            h = int(line[7:])
    return (x, y, w, h)


def window_under_cursor() -> Optional[int]:
    """Return the window id under the cursor, or ``None``.

    Uses ``xdotool getmouselocation --shell`` and reads the
    ``WINDOW=...`` line.

    .. caution::
       Under Wayland the compositor does not reveal the window under the
       cursor to clients; this function always returns ``None`` on a
       pure-Wayland session (checked via $DISPLAY).
    """
    if not _check_x11():
        return None
    try:
        out = _xdotool("getmouselocation", "--shell", timeout=5)
    except RuntimeError:
        return None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("WINDOW="):
            try:
                return int(line[7:])
            except ValueError:
                return None
    return None


def foreign_foreground() -> Optional[int]:
    """Return the currently active (focused) window id, or ``None``.

    Uses ``xdotool getactivewindow``.  Returns ``None`` if the desktop
    has no focused window (unusual but possible on some WMs).
    """
    try:
        out = _xdotool("getactivewindow", timeout=5)
    except RuntimeError:
        return None
    try:
        return int(out.strip())
    except ValueError:
        return None


def monitor_size(monitor_idx: int = 0) -> tuple[int, int]:
    """Return ``(width, height)`` of the specified monitor.

    Strategy:
      1. Try Xinerama via ``xrandr --query`` and parse the active
         monitor matching *monitor_idx* (by order).
      2. Fall back to ``xdotool getdisplaygeometry`` which returns the
         combined desktop size (spanning all monitors).

    Returns (0, 0) if nothing works.
    """
    # Try xrandr first — gives per-monitor geometry
    try:
        proc = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            monitors = _parse_xrandr_monitors(proc.stdout)
            if monitor_idx < len(monitors):
                return monitors[monitor_idx]
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    # Fallback: combined desktop geometry
    try:
        out = _xdotool("getdisplaygeometry", timeout=5)
        parts = out.split()
        if len(parts) >= 2:
            return (int(parts[0]), int(parts[1]))
    except (RuntimeError, ValueError):
        pass

    return (0, 0)


# ---------------------------------------------------------------------------
# Xrandr parser (internal)
# ---------------------------------------------------------------------------

_XRANDR_MONITOR_RE = re.compile(
    r"^(\S+(?:-\d+)?)\s+connected\s+"
    r"(?:primary\s+)?"
    r"(\d+)x(\d+)\+(\d+)\+(\d+)"
)


def _parse_xrandr_monitors(xrandr_output: str) -> list[tuple[int, int]]:
    """Parse ``xrandr --query`` output and return list of ``(w, h)`` per connected monitor, in order."""
    monitors: list[tuple[int, int]] = []
    for line in xrandr_output.splitlines():
        m = _XRANDR_MONITOR_RE.search(line)
        if m:
            w = int(m.group(2))
            h = int(m.group(3))
            monitors.append((w, h))
    return monitors


# ---------------------------------------------------------------------------
# ctypes/Xlib helpers — lower-overhead alternatives for latency-sensitive paths
# ---------------------------------------------------------------------------

try:
    import ctypes
    import ctypes.util
    _LIBX11_PATH: str | None = ctypes.util.find_library("X11")
except Exception:
    _LIBX11_PATH = None


def _libx11_available() -> bool:
    """Return True if libX11 can be loaded via ctypes (avoids subprocess overhead)."""
    return _LIBX11_PATH is not None and _check_x11()


def window_under_cursor_fast() -> Optional[int]:
    """Return window id under cursor via XQueryPointer (no subprocess).

    Faster than the xdotool variant — useful when polled at high rates
    (e.g. cursor tracking for neural rendering).  Falls back to the
    xdotool version if ctypes/libX11 is unavailable.
    """
    if not _libx11_available():
        return window_under_cursor()

    display = _open_display()
    if display is None:
        return None
    try:
        # XQueryPointer(display, root, &root_return, &child_return, &rx, &ry, &wx, &wy, &mask)
        root = ctypes.c_ulong(_default_root(display))
        root_return = ctypes.c_ulong()
        child_return = ctypes.c_ulong()
        rx = ctypes.c_int()
        ry = ctypes.c_int()
        wx = ctypes.c_int()
        wy = ctypes.c_int()
        mask = ctypes.c_uint()

        lib = _load_libx11()
        lib.XQueryPointer(
            ctypes.c_void_p(display),
            root,
            ctypes.byref(root_return),
            ctypes.byref(child_return),
            ctypes.byref(rx),
            ctypes.byref(ry),
            ctypes.byref(wx),
            ctypes.byref(wy),
            ctypes.byref(mask),
        )
        ret = child_return.value
        return ret if ret != 0 else None
    finally:
        _close_display(display)


def foreign_foreground_fast() -> Optional[int]:
    """Return active window via _NET_ACTIVE_WINDOW property (no subprocess).

    Uses the EWMH atom ``_NET_ACTIVE_WINDOW`` read from the root window.
    Falls back to xdotool if ctypes is unavailable.
    """
    if not _libx11_available():
        return foreign_foreground()

    display = _open_display()
    if display is None:
        return None
    try:
        root = _default_root(display)
        atom = _intern_atom(display, "_NET_ACTIVE_WINDOW")
        if atom == 0:
            return None

        lib = _load_libx11()
        actual_type = ctypes.c_ulong()
        actual_format = ctypes.c_int()
        nitems = ctypes.c_ulong()
        bytes_after = ctypes.c_ulong()
        prop_data = ctypes.c_void_p()

        lib.XGetWindowProperty(
            ctypes.c_void_p(display),
            ctypes.c_ulong(root),
            ctypes.c_ulong(atom),
            0,          # offset
            1,          # length (longs)
            0,          # delete = False
            0,          # AnyPropertyType
            ctypes.byref(actual_type),
            ctypes.byref(actual_format),
            ctypes.byref(nitems),
            ctypes.byref(bytes_after),
            ctypes.byref(prop_data),
        )
        if prop_data:
            wid = ctypes.cast(prop_data, ctypes.POINTER(ctypes.c_ulong))[0]
            lib.XFree(prop_data)
            return wid if wid != 0 else None
        return None
    finally:
        _close_display(display)


# ---------------------------------------------------------------------------
# ctypes / libX11 internals
# ---------------------------------------------------------------------------

_XLIB_CACHE: dict[str, any] = {}


def _load_libx11():
    if "lib" not in _XLIB_CACHE:
        _XLIB_CACHE["lib"] = ctypes.CDLL(_LIBX11_PATH, use_errno=True)
    return _XLIB_CACHE["lib"]


def _open_display() -> Optional[ctypes.c_void_p]:
    lib = _load_libx11()
    lib.XOpenDisplay.restype = ctypes.c_void_p
    display_name = os.environ.get("DISPLAY")
    disp = lib.XOpenDisplay(
        ctypes.c_char_p(display_name.encode() if display_name else None)
    )
    return disp if disp else None


def _close_display(disp) -> None:
    if disp is not None:
        lib = _load_libx11()
        lib.XCloseDisplay(ctypes.c_void_p(disp))


def _default_root(display) -> int:
    lib = _load_libx11()
    lib.XDefaultRootWindow.restype = ctypes.c_ulong
    return lib.XDefaultRootWindow(ctypes.c_void_p(display))


def _intern_atom(display, name: str) -> int:
    lib = _load_libx11()
    lib.XInternAtom.restype = ctypes.c_ulong
    return lib.XInternAtom(
        ctypes.c_void_p(display),
        ctypes.c_char_p(name.encode()),
        0,  # only_if_exists = False
    )


# ---------------------------------------------------------------------------
# CLI test mode
# ---------------------------------------------------------------------------

def _test() -> None:
    """Print results of every public function to stdout."""
    print("=== platform_linux.py self-test ===")
    print(f"X11 available: {_check_x11()}")
    print()

    if not _check_x11():
        print("SKIPPING runtime tests (no X11 display)")
        sys.exit(0)

    print("--- list_capturable_windows ---")
    wins = list_capturable_windows()
    print(f"  count: {len(wins)}")
    for w in wins[:10]:
        print(f"    id={w['id']:>8d}  title={w['title'][:80]}")
    if len(wins) > 10:
        print(f"    ... and {len(wins) - 10} more")

    print()
    print("--- window_frame_rect (first window) ---")
    if wins:
        wid = wins[0]["id"]
        r = window_frame_rect(wid)
        print(f"  window {wid}: x={r[0]} y={r[1]} w={r[2]} h={r[3]}")

    print()
    print("--- window_under_cursor ---")
    wuc = window_under_cursor()
    print(f"  result: {wuc}")

    print()
    print("--- window_under_cursor_fast (ctypes) ---")
    wuc2 = window_under_cursor_fast()
    print(f"  result: {wuc2}")

    print()
    print("--- foreign_foreground ---")
    fg = foreign_foreground()
    print(f"  result: {fg}")

    print()
    print("--- foreign_foreground_fast (ctypes) ---")
    fg2 = foreign_foreground_fast()
    print(f"  result: {fg2}")

    print()
    print("--- monitor_size (idx=0) ---")
    ms = monitor_size(0)
    print(f"  result: {ms}")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _test()
    else:
        print(
            "platform_linux.py — Linux window management library (X11/xdotool).\n"
            "Run with --test to print a self-test."
        )