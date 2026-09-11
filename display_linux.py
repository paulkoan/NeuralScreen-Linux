"""
display_linux.py — SDL2-based borderless fullscreen overlay window for Linux.

Matches the expected Display interface (show, poll_events, close, set_visible, reveal)
and provides a --test CLI mode.

Click-through on X11 is achieved via:
  1. _NET_WM_WINDOW_TYPE_DESKTOP window type hint (input passthrough)
  2. XShapeCombineRectangles with an empty region to suppress pointer events

Dependencies:
    pip install pysdl2
    plus platform SDL2 shared library (apt install libsdl2-2.0-0)
"""

import argparse
import ctypes
import ctypes.util
import sys
from collections import deque

import numpy as np

try:
    import sdl2
    import sdl2.ext
except ImportError:
    raise ImportError(
        "pysdl2 is required. Install with: pip install pysdl2\n"
        "Also ensure libsdl2-2.0-0 is installed (apt install libsdl2-2.0-0)."
    )

# ---------------------------------------------------------------------------
# X11 click-through helpers (ctypes)
# ---------------------------------------------------------------------------

_XLIB = None
_XSHAPE = None
_DISPLAY_PTR = None
_ROOT_WINDOW = None

_ATOM_NET_WM_WINDOW_TYPE = None
_ATOM_NET_WM_WINDOW_TYPE_DESKTOP = None


def _ensure_x11():
    """Load Xlib + XShape symbols on first call. Safe to call multiple times."""
    global _XLIB, _XSHAPE, _DISPLAY_PTR, _ROOT_WINDOW
    global _ATOM_NET_WM_WINDOW_TYPE, _ATOM_NET_WM_WINDOW_TYPE_DESKTOP

    if _XLIB is not None:
        return True, "x11_loaded"

    if sys.platform != "linux":
        return False, "not_linux"

    xlib_path = ctypes.util.find_library("X11")
    xshape_path = ctypes.util.find_library("Xext")
    if not xlib_path:
        return False, "libX11_not_found"

    _XLIB = ctypes.cdll.LoadLibrary(xlib_path)
    _DISPLAY_PTR = _XLIB.XOpenDisplay(None)
    if not _DISPLAY_PTR:
        return False, "cannot_open_display"

    _ROOT_WINDOW = _XLIB.XDefaultRootWindow(_DISPLAY_PTR)

    # Intern atoms for window type hints
    _XLIB.XInternAtom.restype = ctypes.c_ulong
    _ATOM_NET_WM_WINDOW_TYPE = _XLIB.XInternAtom(
        _DISPLAY_PTR, b"_NET_WM_WINDOW_TYPE", ctypes.c_int(False)
    )
    _ATOM_NET_WM_WINDOW_TYPE_DESKTOP = _XLIB.XInternAtom(
        _DISPLAY_PTR, b"_NET_WM_WINDOW_TYPE_DESKTOP", ctypes.c_int(False)
    )

    if xshape_path:
        _XSHAPE = ctypes.cdll.LoadLibrary(xshape_path)
        # XShapeQueryVersion to verify shape extension is present
        _XSHAPE.XShapeQueryVersion.restype = ctypes.c_int
        error_base = ctypes.c_int()
        event_base = ctypes.c_int()
        if not _XSHAPE.XShapeQueryExtension(
            _DISPLAY_PTR,
            ctypes.byref(event_base),
            ctypes.byref(error_base),
        ):
            _XSHAPE = None  # shape extension not available, fall back to type hint only

    return True, "x11_active"


def _set_click_through_x11(sdl_window):
    """Apply click-through on X11 using window type hint + input-only shape mask."""
    ok, reason = _ensure_x11()
    if not ok:
        return reason

    # Get the X11 window ID from SDL
    info = sdl2.SDL_SysWMinfo()
    sdl2.SDL_VERSION(info.version)
    sdl2.SDL_GetWindowWMInfo(sdl_window, ctypes.byref(info))
    x11_window = info.info.x11.window

    # 1. Set _NET_WM_WINDOW_TYPE to DESKTOP (some compositors respect this)
    cardinal = ctypes.c_ulong(_ATOM_NET_WM_WINDOW_TYPE_DESKTOP)
    _XLIB.XChangeProperty(
        _DISPLAY_PTR,
        x11_window,
        _ATOM_NET_WM_WINDOW_TYPE,
        ctypes.c_ulong(4),  # XA_ATOM
        ctypes.c_int(32),  # 32-bit format
        ctypes.c_int(0),  # PropModeReplace
        ctypes.byref(cardinal),
        ctypes.c_int(1),
    )

    # 2. If XShape is available, set an empty input mask — this is the
    #    definitive way to achieve click-through on X11.
    #    ShapeInput = 2 in the XShape specification.
    if _XSHAPE is not None:
        # An empty region means no pointer events are delivered to our window.
        _XSHAPE.XShapeCombineRectangles(
            _DISPLAY_PTR,
            x11_window,
            ctypes.c_int(2),  # ShapeInput
            ctypes.c_int(0),  # x_offset
            ctypes.c_int(0),  # y_offset
            None,             # rects — empty → zero input region
            ctypes.c_int(0),  # n_rects
            ctypes.c_int(0),  # Unsorted
            ctypes.c_int(0),  # ShapeSet
        )

    _XLIB.XFlush(_DISPLAY_PTR)
    return "click_through_x11"


def _unset_click_through_x11(sdl_window):
    """Restore normal input processing (set bounding shape to full window)."""
    if _XSHAPE is None:
        return

    ok, reason = _ensure_x11()
    if not ok or _DISPLAY_PTR is None:
        return

    info = sdl2.SDL_SysWMinfo()
    sdl2.SDL_VERSION(info.version)
    sdl2.SDL_GetWindowWMInfo(sdl_window, ctypes.byref(info))
    x11_window = info.info.x11.window

    # Get window dimensions
    w = ctypes.c_int()
    h = ctypes.c_int()
    _XLIB.XGetGeometry(_DISPLAY_PTR, x11_window,
                       ctypes.byref(ctypes.c_ulong()),
                       ctypes.byref(ctypes.c_int()),
                       ctypes.byref(ctypes.c_int()),
                       ctypes.byref(w), ctypes.byref(h),
                       ctypes.byref(ctypes.c_uint()),
                       ctypes.byref(ctypes.c_uint()))

    class XRectangle(ctypes.Structure):
        _fields_ = [("x", ctypes.c_short), ("y", ctypes.c_short),
                    ("width", ctypes.c_ushort), ("height", ctypes.c_ushort)]

    rect = XRectangle(0, 0, ctypes.c_ushort(w.value), ctypes.c_ushort(h.value))
    _XSHAPE.XShapeCombineRectangles(
        _DISPLAY_PTR, x11_window,
        ctypes.c_int(2),  # ShapeInput — see enum above
        0, 0,
        ctypes.byref(rect), 1,
        ctypes.c_int(0),  # Unsorted
        ctypes.c_int(0),  # XShapeSet — replace
    )
    _XLIB.XFlush(_DISPLAY_PTR)


# ---------------------------------------------------------------------------
# Key ↔ event string mapping
# ---------------------------------------------------------------------------

_KEY_EVENT_MAP = {
    sdl2.SDLK_ESCAPE: "quit",
    sdl2.SDLK_q: "quit",
    sdl2.SDLK_F1: "menu",
    sdl2.SDLK_F10: "menu",
    sdl2.SDLK_TAB: "tab",
    sdl2.SDLK_SPACE: "space",
    sdl2.SDLK_RETURN: "enter",
    sdl2.SDLK_BACKSPACE: "backspace",
    sdl2.SDLK_UP: "up",
    sdl2.SDLK_DOWN: "down",
    sdl2.SDLK_LEFT: "left",
    sdl2.SDLK_RIGHT: "right",
    sdl2.SDLK_v: "toggle_visibility",
    sdl2.SDLK_h: "toggle_hud",
    sdl2.SDLK_r: "toggle_recording",
    sdl2.SDLK_f: "toggle_fullscreen",
}


# ---------------------------------------------------------------------------
# Display class
# ---------------------------------------------------------------------------

class Display:
    """Borderless fullscreen overlay window using SDL2 on Linux.

    Interface expected by NeuralScreen's Python process:

        __init__(width, height, fullscreen, click_through)
        show(frame: np.ndarray)        # (H, W, 4) uint8, BGRA
        set_hud(hud: dict)
        poll_events() -> list[str]
        close()
        set_visible(visible: bool)
        reveal()
    """

    def __init__(
        self,
        width: int,
        height: int,
        fullscreen: bool = True,
        click_through: bool = True,
    ):
        self.width = width
        self.height = height
        self._visible = True
        self._closed = False
        self._hud = {}
        self._event_queue: deque = deque()

        # Initialise SDL subsystems
        if sdl2.SDL_Init(
            sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_EVENTS
        ) != 0:
            raise RuntimeError(
                f"SDL_Init failed: {sdl2.SDL_GetError().decode()}"
            )

        sdl2.SDL_SetHint(
            sdl2.SDL_HINT_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR,
            b"0",
        )

        # Build window flags
        flags = (
            sdl2.SDL_WINDOW_BORDERLESS
            | sdl2.SDL_WINDOW_ALWAYS_ON_TOP
            | sdl2.SDL_WINDOW_SKIP_TASKBAR
        )
        if fullscreen:
            flags |= sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP

        self.window = sdl2.SDL_CreateWindow(
            b"NeuralScreen",
            0, 0,
            width, height,
            flags,
        )
        if not self.window:
            raise RuntimeError(
                f"SDL_CreateWindow failed: {sdl2.SDL_GetError().decode()}"
            )

        self.renderer = sdl2.SDL_CreateRenderer(
            self.window,
            -1,
            sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC,
        )
        if not self.renderer:
            raise RuntimeError(
                f"SDL_CreateRenderer failed: {sdl2.SDL_GetError().decode()}"
            )

        # Disable vsync so we can target 60 FPS via timing instead
        sdl2.SDL_GL_SetSwapInterval(0)

        # Streaming texture matching the expected BGRA pixel format
        self.texture = sdl2.SDL_CreateTexture(
            self.renderer,
            sdl2.SDL_PIXELFORMAT_BGRA32,
            sdl2.SDL_TEXTUREACCESS_STREAMING,
            width,
            height,
        )
        if not self.texture:
            raise RuntimeError(
                f"SDL_CreateTexture failed: {sdl2.SDL_GetError().decode()}"
            )

        # Click-through setup
        self._click_through_enabled = click_through
        if click_through:
            _set_click_through_x11(self.window)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def show(self, frame: np.ndarray):
        """Present a frame.  *frame* is (H, W, 4) uint8, BGRA byte order."""
        if self._closed or not self._visible:
            return

        assert frame.dtype == np.uint8, f"Expected uint8, got {frame.dtype}"
        assert frame.shape[2] == 4, f"Expected 4 channels, got {frame.shape[2]}"

        # Upload pixel data via ctypes pointer to the flat numpy buffer
        raw = frame.reshape(-1).ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
        sdl2.SDL_UpdateTexture(
            self.texture,
            None,  # entire texture
            raw,
            frame.shape[1] * 4,  # pitch = width × 4 bytes
        )

        sdl2.SDL_RenderCopy(self.renderer, self.texture, None, None)

        # HUD overlay: if set_hud was called with a dict of labels/values
        # we could render them here.  For now, future rendering passes
        # through the HUD state and can blend extra elements if needed
        # (e.g. via SDL2_ttf or SDL2_gfx — not included to keep deps minimal.)

        sdl2.SDL_RenderPresent(self.renderer)

    def set_hud(self, hud: dict):
        """Store HUD state for optional on-screen rendering."""
        self._hud = dict(hud) if hud else {}

    def poll_events(self) -> list[str]:
        """Return a list of event strings since the last call."""
        events = []
        # Also drain the internal queue (from mouse-button synthetic events etc.)
        while self._event_queue:
            events.append(self._event_queue.popleft())

        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(event)):
            parsed = self._parse_event(event)
            if parsed:
                if isinstance(parsed, list):
                    events.extend(parsed)
                else:
                    events.append(parsed)

        return events

    def close(self):
        """Tear down the window and SDL subsystems."""
        if self._closed:
            return
        self._closed = True
        self._visible = False

        if self.texture:
            sdl2.SDL_DestroyTexture(self.texture)
            self.texture = None
        if self.renderer:
            sdl2.SDL_DestroyRenderer(self.renderer)
            self.renderer = None
        if self.window:
            sdl2.SDL_DestroyWindow(self.window)
            self.window = None
        sdl2.SDL_Quit()

    def set_visible(self, visible: bool):
        """Show or hide the window."""
        if visible == self._visible:
            return
        self._visible = visible
        if visible:
            sdl2.SDL_ShowWindow(self.window)
            self.reveal()
        else:
            sdl2.SDL_HideWindow(self.window)

    def reveal(self):
        """Raise the window to the top of the stacking order and restore input
        focus (useful after a compositor or another window stole focus)."""
        sdl2.SDL_RaiseWindow(self.window)

        # On X11 we also need to explicitly request focus
        ok, reason = _ensure_x11()
        if ok and _XLIB is not None:
            info = sdl2.SDL_SysWMinfo()
            sdl2.SDL_VERSION(info.version)
            sdl2.SDL_GetWindowWMInfo(self.window, ctypes.byref(info))
            x11_window = info.info.x11.window

            # Set _NET_ACTIVE_WINDOW message
            _XLIB.XRaiseWindow(_DISPLAY_PTR, x11_window)
            _XLIB.XMapRaised(_DISPLAY_PTR, x11_window)

            # Send WM_TAKE_FOCUS protocol
            wm_protocols = _XLIB.XInternAtom(
                _DISPLAY_PTR, b"WM_PROTOCOLS", ctypes.c_int(True)
            )
            wm_take_focus = _XLIB.XInternAtom(
                _DISPLAY_PTR, b"WM_TAKE_FOCUS", ctypes.c_int(True)
            )

            class XClientMessageEvent(ctypes.Structure):
                _fields_ = [
                    ("type", ctypes.c_int),
                    ("serial", ctypes.c_ulong),
                    ("send_event", ctypes.c_int),
                    ("display", ctypes.c_void_p),
                    ("window", ctypes.c_ulong),
                    ("message_type", ctypes.c_ulong),
                    ("format", ctypes.c_int),
                    ("data", ctypes.c_ulong * 5),
                ]

            ev = XClientMessageEvent()
            ev.type = 33  # ClientMessage
            ev.window = x11_window
            ev.message_type = wm_protocols
            ev.format = 32
            ev.data[0] = wm_take_focus
            ev.data[1] = 0  # timestamp 0 = current time
            _XLIB.XSendEvent(
                _DISPLAY_PTR,
                _ROOT_WINDOW,
                ctypes.c_int(False),
                ctypes.c_int(0xFFFFFF),  # SubstructureRedirect | SubstructureNotify
                ctypes.byref(ev),
            )

            _XLIB.XFlush(_DISPLAY_PTR)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_event(self, event) -> str | list[str] | None:
        """Translate an SDL_Event into one or more event strings."""
        etype = event.type

        if etype == sdl2.SDL_QUIT:
            return "quit"

        if etype == sdl2.SDL_KEYDOWN:
            sym = event.key.keysym.sym
            mapped = _KEY_EVENT_MAP.get(sym)
            if mapped:
                return mapped
            # Pass printable characters through
            c = sdl2.SDL_GetKeyName(sym)
            if c and len(c) == 1:
                return f"key:{c.decode()}"
            return f"key:{sym}"

        if etype == sdl2.SDL_KEYUP:
            return None  # we only care about presses

        if etype == sdl2.SDL_WINDOWEVENT:
            sub = event.window.event
            if sub == sdl2.SDL_WINDOWEVENT_FOCUS_LOST:
                return "focus_lost"
            if sub == sdl2.SDL_WINDOWEVENT_FOCUS_GAINED:
                return "focus_gained"
            if sub == sdl2.SDL_WINDOWEVENT_CLOSE:
                return "quit"
            if sub == sdl2.SDL_WINDOWEVENT_EXPOSED:
                return "exposed"
            if sub == sdl2.SDL_WINDOWEVENT_SIZE_CHANGED:
                return "resized"
            return None

        if etype == sdl2.SDL_MOUSEBUTTONDOWN:
            btn = event.button.button
            return f"mousedown:{btn}"

        if etype == sdl2.SDL_MOUSEBUTTONUP:
            btn = event.button.button
            return f"mouseup:{btn}"

        if etype == sdl2.SDL_MOUSEMOTION:
            return None  # too noisy for poll_events

        return None

    def __del__(self):
        self.close()


# ---------------------------------------------------------------------------
# --test CLI mode
# ---------------------------------------------------------------------------

def _test_mode():
    """Run a self-test: show a window with an animated coloured gradient."""
    parser = argparse.ArgumentParser(description="display_linux.py self-test")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--click-through", action="store_true", default=False)
    args = parser.parse_args()

    print(
        f"display_linux.py --test: {args.width}x{args.height} "
        f"(click-through={args.click_through})"
    )
    print("  Press ESC or Q to quit.")

    display = Display(
        width=args.width,
        height=args.height,
        fullscreen=False,
        click_through=args.click_through,
    )

    running = True
    t = 0.0

    try:
        while running:
            # Poll events
            for ev in display.poll_events():
                if ev in ("quit",):
                    print(f"  Event: {ev}")
                    running = False
                    break
                print(f"  Event: {ev}")

            if not running:
                break

            # Generate a gradient frame — smooth RGBA colour sweep
            frame = np.zeros((args.height, args.width, 4), dtype=np.uint8)

            y_coords = np.arange(args.height)[:, None]  # (H, 1)
            x_coords = np.arange(args.width)[None, :]    # (1, W)

            # Red-green-blue sweep with a time-varying twist
            r = (y_coords * 255 // args.height).astype(np.uint8)
            g = (x_coords * 255 // args.width).astype(np.uint8)
            b = (
                (np.sin(t + x_coords * 0.02 + y_coords * 0.02) * 0.5 + 0.5) * 255
            ).astype(np.uint8)

            frame[:, :, 0] = 0      # B channel (BGRA order)
            frame[:, :, 1] = g      # G channel
            frame[:, :, 2] = r      # R channel
            frame[:, :, 3] = 255    # A channel

            # Actually fill B with a wave for visual interest
            frame[:, :, 0] = b

            display.show(frame)

            # ~16.6 ms between frames (≈60 FPS)
            sdl2.SDL_Delay(16)
            t += 0.05

    except KeyboardInterrupt:
        pass
    finally:
        display.close()
        print("display_linux.py --test: done.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _test_mode()