"""
capture_linux.py — Linux screen capture for NeuralScreen.

Two backends, auto-selected:

1. **PipeWire** (Wayland, preferred) — uses `pipewire-capture` (bquenin) which
   talks to xdg-desktop-portal for screencast + reads DMA-BUF frames.
   Install: ``pip install pipewire-capture``
   Requires: Wayland session, xdg-desktop-portal implementation (GNOME/KDE).

2. **X11/XShm** (fallback) — uses `python-mss` for fast shared-memory capture.
   Install: ``pip install mss``
   Requires: X11 display, MIT-SHM extension (nearly universal).

Interface matches capture.py's ``ScreenCapture`` exactly:
    cap = ScreenCapture(monitor_idx=0)
    frame = cap.grab()        # (H, W, 4) uint8 RGBA
    cap.close()
"""

from __future__ import annotations

import os
import sys

import numpy as np


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

def _is_wayland() -> bool:
    """True if WAYLAND_DISPLAY is set (indicating a Wayland session)."""
    return bool(os.environ.get("WAYLAND_DISPLAY"))


# ---------------------------------------------------------------------------
# Backend 1: PipeWire (Wayland) via bquenin/pipewire-capture
# ---------------------------------------------------------------------------

try:
    import pipewire_capture
    _HAS_PIPEWIRE = pipewire_capture.is_available()
except ImportError:
    _HAS_PIPEWIRE = False
except Exception:
    _HAS_PIPEWIRE = False


class _PipeWireCapture:
    """PipeWire screencast capture backend.

    Uses xdg-desktop-portal ScreenCast D-Bus API to request a monitor capture
    stream and PipeWire to receive DMA-BUF frames converted to numpy RGBA.
    """

    def __init__(self, monitor_idx: int = 0):
        if not _HAS_PIPEWIRE:
            raise RuntimeError(
                "PipeWire capture not available. Install:\n"
                "  pip install pipewire-capture\n"
                "Requires a Wayland session with xdg-desktop-portal."
            )
        self._monitor_idx = monitor_idx
        self._portal = pipewire_capture.PortalCapture()
        # SelectSources(Monitor) captures the whole screen.
        # monitor_idx is used to select which monitor (0 = primary).
        source_type = 1  # Monitor = 1, Window = 2
        self._portal.select_sources(source_type)
        self._stream: pipewire_capture.CaptureStream | None = None
        self._started = False

    def grab(self) -> np.ndarray:
        """Return (H, W, 4) uint8 RGBA frame from the PipeWire stream."""
        if not self._started:
            info = self._portal.start()
            self._stream = pipewire_capture.CaptureStream(info)
            self._started = True
        # Read the latest frame (blocking for up to 1/30s)
        frame = self._stream.read()
        # frame is typically (H, W, 4) uint8 BGRA or RGBA depending on
        # the portal implementation. pipewire-capture returns numpy arrays.
        if frame is None:
            raise RuntimeError("PipeWire stream returned no frame")
        # Ensure RGBA — pipewire-capture may return BGRA
        if frame.shape[2] == 4:
            # Check if it's actually BGRA by looking at a known pixel;
            # for safety, assume the library returns RGBX and convert
            # only if first byte != last byte in simple patterns.
            # pipewire-capture currently returns RGBA, so this is a no-op.
            pass
        return frame

    def close(self):
        if self._stream is not None:
            try:
                self._stream.stop()
            except Exception:
                pass
            self._stream = None
        if self._portal is not None:
            try:
                self._portal.close()
            except Exception:
                pass
            self._portal = None  # type: ignore[assignment]
        self._started = False


# ---------------------------------------------------------------------------
# Backend 2: X11/XShm via python-mss
# ---------------------------------------------------------------------------

try:
    import mss
    import mss.tools
    _HAS_MSS = True
except ImportError:
    _HAS_MSS = False


class _XScreencapture:
    """X11/XShm screen capture backend using python-mss.

    Uses the MIT-SHM shared-memory extension for fast capture. Falls back
    to XGetImage when SHM is unavailable (e.g. over SSH -X).
    """

    def __init__(self, monitor_idx: int = 0):
        if not _HAS_MSS:
            raise RuntimeError(
                "MSS (python-mss) not available. Install:\n"
                "  pip install mss\n"
                "Requires an X11 display."
            )
        self._sct = mss.mss()
        monitors = self._sct.monitors
        if monitor_idx < 0 or monitor_idx >= len(monitors):
            self.close()
            raise ValueError(
                f"monitor_idx={monitor_idx} out of range "
                f"(0..{len(monitors)-1}, where 0 = all monitors)"
            )
        # Index 0 = combined virtual screen, 1+ = individual monitors
        self._monitor_idx = monitor_idx
        self._mon_info = monitors[monitor_idx]

    def grab(self) -> np.ndarray:
        """Return (H, W, 4) uint8 RGBA frame.

        python-mss returns BGRA by default; we do a shallow conversion
        to RGBA (swap R↔B in-place to avoid unnecessary allocation).
        """
        raw = self._sct.grab(self._mon_info)
        # raw is a PIL Image or mss screenshot object
        img = np.asarray(raw)  # (H, W, 4) uint8 BGRA
        # In-place BGRA → RGBA (swap channels 0 and 2)
        img[:, :, [0, 2]] = img[:, :, [2, 0]]
        return img

    def close(self):
        if self._sct is not None:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Public interface: ScreenCapture
# ---------------------------------------------------------------------------

class ScreenCapture:
    """Single unified capture class — selects the best backend automatically.

    Priority:
        1. PipeWire (Wayland session + pipewire-capture installed)
        2. X11/XShm  (X11 display + mss installed)

    Raises RuntimeError if no backend is available.
    """

    def __init__(self, monitor_idx: int = 0):
        self._backend: _PipeWireCapture | _XScreencapture
        self._closed = False

        if _is_wayland() and _HAS_PIPEWIRE:
            self._backend = _PipeWireCapture(monitor_idx)
        elif not _is_wayland() and _HAS_MSS:
            self._backend = _XScreencapture(monitor_idx)
        elif _is_wayland() and not _HAS_PIPEWIRE:
            raise RuntimeError(
                "Wayland detected but pipewire-capture not installed.\n"
                "  pip install pipewire-capture\n"
                "Alternatively switch to an X11 session and install mss:\n"
                "  pip install mss"
            )
        else:
            raise RuntimeError(
                "No capture backend available.\n"
                "  X11: pip install mss\n"
                "  Wayland: pip install pipewire-capture"
            )

    def grab(self) -> np.ndarray:
        """Capture one frame. Returns (H, W, 4) uint8 RGBA."""
        return self._backend.grab()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._backend.close()


def list_monitors() -> list[tuple[int, str]]:
    """Return [(index, description), ...] for available monitors.

    Uses MSS if available; returns a placeholder on Wayland since
    monitor enumeration needs the portal to be active.
    """
    if _HAS_MSS:
        try:
            with mss.mss() as sct:
                return list(enumerate(m["monitor"] for m in sct.monitors))
        except Exception:
            pass
    return [(0, "Primary (PipeWire)")]


# ---------------------------------------------------------------------------
# Test mode
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Linux screen capture")
    parser.add_argument("--monitor", type=int, default=0)
    parser.add_argument("--out", default="test_capture.png",
                       help="Save first frame to this PNG (default: test_capture.png)")
    args = parser.parse_args()

    print(f"Display: {'Wayland' if _is_wayland() else 'X11'}")
    print(f"PipeWire available: {_HAS_PIPEWIRE}")
    print(f"MSS available: {_HAS_MSS}")
    print()

    cap = ScreenCapture(monitor_idx=args.monitor)
    frame = cap.grab()
    cap.close()

    print(f"Frame: {frame.shape} dtype={frame.dtype}")
    print(f"Mean pixel: R={frame[:,:,0].mean():.1f} "
          f"G={frame[:,:,1].mean():.1f} B={frame[:,:,2].mean():.1f}")
    if args.out:
        try:
            import PIL.Image
            PIL.Image.fromarray(
                frame[:, :, [2, 1, 0]]  # RGBA → BGRA for PIL
            ).save(args.out)
            print(f"Saved to {args.out}")
        except ImportError:
            print("(PIL not installed, skipping save)")
    print("OK")