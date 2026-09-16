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

import os

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


class SyntheticCapture:
    """A known frame instead of a screen.

    This exists because the pipeline has to be testable when capture cannot be.
    On a Wayland session mss reads the XWayland root window, and nothing draws
    there, so every grabbed frame is black — the pass then has nothing to act on
    and "the pass is broken" and "capture is broken" look identical. Feeding a
    frame whose contents are known separates the two questions.

    The frame carries what an NR pass needs to have an opinion about: a
    horizontal red ramp, a vertical green ramp, blue interference stripes for
    local structure, and a bar that moves each grab so consecutive frames differ.
    """

    def __init__(self, width: int = 1280, height: int = 720):
        self.width = int(width)
        self.height = int(height)
        self._n = 0

    @property
    def resolution(self) -> tuple[int, int]:
        return self.width, self.height

    def grab(self) -> np.ndarray:
        w, h, n = self.width, self.height, self._n
        self._n += 1
        x = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
        y = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
        frame = np.empty((h, w, 4), dtype=np.uint8)
        frame[..., 0] = (255.0 * x).astype(np.uint8)
        frame[..., 1] = (255.0 * y).astype(np.uint8)
        frame[..., 2] = (255.0 * (0.5 + 0.5 * np.sin(6.0 * (x + y)))).astype(np.uint8)
        frame[..., 3] = 255
        bar = int((n * 7) % max(1, w - w // 8))
        frame[:, bar:bar + max(1, w // 8), :3] = 255
        return frame

    def close(self) -> None:
        pass


class ImageCapture:
    """Replay one still image as the frame source.

    The practical Wayland workaround today: `grim shot.png` (or any screenshot
    tool), then point the MVP at the file. The interface is the same as a live
    capture, so when the portal-based backend lands nothing else changes.
    """

    def __init__(self, path):
        import cv2
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            raise CaptureError(f"cannot read image: {path}")
        alpha = np.full(img.shape[:2], 255, dtype=np.uint8)
        self._frame = np.dstack([img[:, :, ::-1], alpha])   # BGR -> RGBA
        self.height, self.width = self._frame.shape[:2]

    @property
    def resolution(self) -> tuple[int, int]:
        return self.width, self.height

    def grab(self) -> np.ndarray:
        return self._frame.copy()

    def close(self) -> None:
        pass


def open_capture(source: str, *, monitor: int = 0, input_image=None,
                 width: int | None = None, height: int | None = None):
    """Build the frame source named by --source.

    \"auto\" picks per session: Wayland desktops get the portal (mss would hand
    back the black XWayland root), everything else gets the X11 grab. \"synthetic\"
    and \"image\" exist so the pass can be exercised without any real capture.
    """
    if source == "auto":
        source = "wayland" if os.environ.get("XDG_SESSION_TYPE") == "wayland" else "screen"
        if source == "wayland":
            # Fall back rather than refuse: on a Wayland session with no portal,
            # an X11 grab is often still the only thing that works (XWayland),
            # and a black frame is more diagnosable than a startup failure.
            from minimal.capture_wayland import requirements
            usable, why = requirements()
            if not usable:
                print(f"  ! Wayland capture unavailable ({why}); "
                      f"falling back to the X11 grab, which may return black")
                source = "screen"
    if source == "screen":
        return Capture(monitor_idx=monitor)
    if source == "wayland":
        # Imported lazily: it pulls in jeepney, and the other sources must keep
        # working on machines where that is not installed.
        from minimal.capture_wayland import PortalCapture
        return PortalCapture(monitor_idx=monitor)
    if source == "synthetic":
        return SyntheticCapture(width or 1280, height or 720)
    if source == "image":
        if not input_image:
            raise CaptureError("--source image needs --input-image PATH")
        return ImageCapture(input_image)
    raise CaptureError(f"unknown source: {source}")


def save_png(path, frame: np.ndarray) -> None:
    """Write an (H, W, 4) RGBA frame as an OPAQUE 3-channel PNG.

    Two decisions, both of them consequences of a real bug:

    * **Three channels, not four.** A screenshot has no meaningful alpha. Writing
      one invites anything downstream to flatten the image against a background,
      and Telegram does exactly that when it converts an uploaded photo to JPEG —
      which is how a captured desktop ended up looking like a white sheet.

    * **Reorder with `[2, 1, 0]`, never `[..., ::-1]`.** cv2 works in BGR, so
      going from RGBA needs the red and blue swapped. `::-1` reverses *all four*
      channels, turning RGBA into ABGR: the file's blue gets the alpha, its green
      the blue, its red the green, and its alpha the **red channel**. With that
      alpha, compositing over white produced a frame at roughly 19% opacity —
      the washed-out image that cost a round of diagnosis.
    """
    import cv2
    cv2.imwrite(str(path), np.ascontiguousarray(frame[:, :, [2, 1, 0]]))