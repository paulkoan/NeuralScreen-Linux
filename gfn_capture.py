"""
gfn_capture.py — GeForce Now window detection and capture helpers.

Finds the GeForce Now stream window (browser tab or native client) and
provides helpers to focus capture on it.  On X11, uses xdotool for
window matching; on Wayland, falls back to manual selection.

Window title patterns matched (case-insensitive):
    - "GeForce NOW"
    - "NVIDIA GeForce NOW"
    - "GeForceNow" (native client)
"""

from __future__ import annotations

import re
import subprocess

from platform_linux import _check_x11 as _x11_available


# ---------------------------------------------------------------------------
# Window title patterns
# ---------------------------------------------------------------------------

_GFN_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"geforce\s*now",
        r"nvidia\s+geforce",
        r"geforcenow",
    ]
]


def _matches_gfn(title: str) -> bool:
    """True if the window title matches a GeForce Now pattern."""
    return any(p.search(title) for p in _GFN_PATTERNS)


def find_gfn_window() -> dict | None:
    """Find a GeForce Now window.

    Returns:
        ``{"id": int, "title": str, "x": int, "y": int, "w": int, "h": int}``
        or None if no matching window is found.

    Only works on X11 (xdotool).  Returns None on Wayland.
    """
    if not _x11_available():
        return None

    try:
        # List all visible windows with their PIDs, names, and geometry
        output = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--name", ""],
            capture_output=True, text=True, timeout=5,
        )
        wids = output.stdout.strip().split()
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        return None

    for wid in wids:
        try:
            # Get window name
            name = subprocess.run(
                ["xdotool", "getwindowname", wid],
                capture_output=True, text=True, timeout=2,
            ).stdout.strip()
        except Exception:
            continue

        if _matches_gfn(name):
            try:
                geom = subprocess.run(
                    ["xdotool", "getwindowgeometry", "--shell", wid],
                    capture_output=True, text=True, timeout=2,
                )
                props = {}
                for line in geom.stdout.strip().splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        props[k] = int(v)
                return {
                    "id": int(wid),
                    "title": name,
                    "x": props.get("X", 0),
                    "y": props.get("Y", 0),
                    "w": props.get("WIDTH", 0),
                    "h": props.get("HEIGHT", 0),
                }
            except Exception:
                return {"id": int(wid), "title": name,
                        "x": 0, "y": 0, "w": 0, "h": 0}
    return None


def capture_gfn_window(capture_instance) -> None:
    """Convenience: find the GFN window and switch capture to it.

    Call this when the user presses Num5 while GeForce Now is running.
    The capture switches from full-screen to single-window mode.

    Args:
        capture_instance: a ScreenCapture-like object that supports
            ``set_window(id: int)`` or similar.  If the capture object
            doesn't have this method, returns without error.
    """
    win = find_gfn_window()
    if win is None:
        print("[gfn] No GeForce Now window found")
        return
    print(f"[gfn] Found GFN window: \"{win['title']}\" "
          f"({win['w']}x{win['h']} @ {win['x']},{win['y']})")
    if hasattr(capture_instance, "set_window"):
        capture_instance.set_window(win["id"])


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    win = find_gfn_window()
    if win:
        print(f"GFN window found: {win}")
    else:
        print("No GFN window found (not running or not on X11)")
        sys.exit(1)