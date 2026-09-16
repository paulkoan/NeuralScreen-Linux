"""Screen capture for the MVP — X11 via mss, returning RGBA frames.

Deliberately one backend. PipeWire/Wayland is a later milestone; mss on X11
(and on XWayland, which is what most Wayland desktops run GTK apps under) is
enough to prove the pipeline. The interface is the same shape capture_linux
uses, so swapping the backend later touches nothing else:

    cap = Capture(monitor_idx=0)
    frame = cap.grab()          # (H, W, 4) uint8 RGBA
    cap.close()
"""

from __future__ import annotations

import numpy as np

try:
    import mss
    _HAS_MSS = True
except ImportError:  # pragma: no cover - environment problem, not logic
    _HAS_MSS = False

# `mss.mss` was deprecated in favour of `mss.MSS`; call the class either way so
# the minimum supported mss version does not matter.
_MSS_FACTORY = getattr(mss, "MSS", None) or mss.mss if _HAS_MSS else None


class CaptureError(RuntimeError):
    """Raised when no screen can be captured (no display, no permissions)."""


class Capture:
    """Grab the screen on X11 through mss, converted to RGBA."""

    def __init__(self, monitor_idx: int = 0):
        if not _HAS_MSS:
            raise CaptureError("mss is not installed (pip install mss)")
        try:
            self._sct = _MSS_FACTORY()
        except Exception as exc:  # no display, bad DISPLAY, no X server
            raise CaptureError(f"cannot open a screen capture session: {exc}") from exc

        monitors = self._sct.monitors
        # monitors[0] is the union of all screens; the real ones start at 1.
        wanted = monitor_idx + 1
        if wanted >= len(monitors):
            raise CaptureError(
                f"monitor {monitor_idx} does not exist "
                f"({len(monitors) - 1} screen(s) found)")
        self.monitor_idx = monitor_idx
        self._monitor = monitors[wanted]
        self.width = int(self._monitor["width"])
        self.height = int(self._monitor["height"])

    @property
    def resolution(self) -> tuple[int, int]:
        """(width, height) of the captured screen."""
        return self.width, self.height

    def grab(self) -> np.ndarray:
        """One frame as (H, W, 4) uint8 RGBA.

        mss hands back BGRA; the worker's colour input is RGBA, so the two
        colour channels are swapped. The alpha channel is left as captured.
        """
        shot = np.asarray(self._sct.grab(self._monitor))
        # mss gives (H, W, 4) as BGRA. Reverse B and R in place.
        return shot[:, :, [2, 1, 0, 3]].copy()

    def close(self) -> None:
        try:
            self._sct.close()
        except Exception:
            pass

    def __enter__(self) -> "Capture":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def list_monitors() -> list[tuple[int, str]]:
    """[(index, description)] for the connected screens.

    monitors[0] in mss is the union of every screen, so index 0 here is the
    first *real* monitor, matching Capture(monitor_idx=0).
    """
    with _MSS_FACTORY() as sct:
        return [(i, f"{m['width']}x{m['height']} at ({m['left']},{m['top']})")
                for i, m in enumerate(sct.monitors[1:])]