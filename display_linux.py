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
import time
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

    # Declare the signatures BEFORE the first call. A Display* is a 64-bit pointer, and without
    # restype ctypes assumes int - so XOpenDisplay returned a truncated pointer and the very next
    # call, XDefaultRootWindow, dereferenced it and took the process down (v1's first segfault).
    # Every Xlib entry point used below gets its types for the same reason.
    _XLIB.XOpenDisplay.restype = ctypes.c_void_p
    _XLIB.XOpenDisplay.argtypes = [ctypes.c_char_p]
    _XLIB.XDefaultRootWindow.restype = ctypes.c_ulong
    _XLIB.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    _XLIB.XInternAtom.restype = ctypes.c_ulong
    _XLIB.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    _XLIB.XChangeProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
                                      ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
                                      ctypes.c_void_p, ctypes.c_int]
    _XLIB.XFlush.argtypes = [ctypes.c_void_p]
    _XLIB.XCloseDisplay.argtypes = [ctypes.c_void_p]

    _DISPLAY_PTR = _XLIB.XOpenDisplay(None)
    if not _DISPLAY_PTR:
        return False, "cannot_open_display"

    _ROOT_WINDOW = _XLIB.XDefaultRootWindow(_DISPLAY_PTR)
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
        _XSHAPE.XShapeQueryExtension.restype = ctypes.c_int
        _XSHAPE.XShapeQueryExtension.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
        _XSHAPE.XShapeCombineRectangles.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
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

    # Get the X11 window ID from SDL - but only if this window is an X11 one. On a Wayland
    # session the union carries Wayland data, and reading info.info.x11.window would hand Xlib a
    # window id that never existed. Click-through is an X11 trick; elsewhere it is simply skipped.
    info = sdl2.SDL_SysWMinfo()
    sdl2.SDL_VERSION(info.version)
    if not sdl2.SDL_GetWindowWMInfo(sdl_window, ctypes.byref(info)):
        return "wm_info_failed"
    if info.subsystem != sdl2.SDL_SYSWM_X11:
        return "not_x11"
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
    if not sdl2.SDL_GetWindowWMInfo(sdl_window, ctypes.byref(info)):
        return
    if info.subsystem != sdl2.SDL_SYSWM_X11:
        return
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

class _ScreenInfo:
    """What commands.py asks of ``display.screen``: the current frame size."""

    def __init__(self, owner):
        self._owner = owner

    def get_width(self) -> int:
        return int(self._owner.width)

    def get_height(self) -> int:
        return int(self._owner.height)


class Display:
    """Borderless fullscreen overlay window using SDL2 on Linux.

    Interface expected by NeuralScreen's Python process:

        __init__(width, height, fullscreen, click_through)
        show(frame: np.ndarray)        # (H, W, 4) uint8, RGBA
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

        # Streaming texture in the order the worker actually returns: RGBA. The port's composite
        # writes RGBA8 (the same bytes minimal/ saves as a PNG), so a BGRA texture here would show
        # every frame with red and blue swapped. The Wine path returned BGRA; v1 ships the port.
        self.texture = sdl2.SDL_CreateTexture(
            self.renderer,
            sdl2.SDL_PIXELFORMAT_RGBA32,
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

        # --- The rest of the surface main_linux.py expects ------------------
        # This class was written as a minimal pysdl2 window and the app asks for a good deal
        # more: a menu object, alerts, HUD modes, switch-window state, a screenshot overlay.
        # Everything below exists so the app runs against this backend; the pieces that are
        # genuinely Windows-era (excluding the layer from capture, the native window handle)
        # record their state and do nothing, and say so in the log rather than pretending.
        self.lang = "en"
        self._alert_text: str | None = None
        self._alert_until = 0.0
        self._hud_only = False
        self._menu_opaque = True
        self._menu_input = True
        self._excluded = True
        self._switch: tuple[int, int] | None = None
        self.screen = _ScreenInfo(self)
        import pygame
        pygame.font.init()
        from overlay_ui import OverlayMenu
        self.menu = OverlayMenu(1.0, lambda size: pygame.font.Font(None, size))

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def show(self, frame: np.ndarray):
        """Present a frame.  *frame* is (H, W, 4) uint8, RGBA byte order."""
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

    # --- The app-facing surface -------------------------------------------
    # See the note in __init__: these exist so main_linux.py can drive this backend.

    def set_lang(self, lang: str) -> None:
        """The UI language. Also sent to the menu, which has its own copy."""
        self.lang = str(lang)
        try:
            self.menu.lang = self.lang
        except Exception:
            pass

    def alert(self, text: str, seconds: float = 2.5) -> None:
        """A transient message. Printed as well, so a headless run still shows it."""
        self._alert_text = str(text)
        self._alert_until = time.monotonic() + float(seconds)
        print(f"[main] alert: {text}")

    def set_menu_opaque(self, on: bool) -> None:
        self._menu_opaque = bool(on)

    def set_menu_input(self, on: bool) -> None:
        self._menu_input = bool(on)

    def set_hud_only(self, on: bool) -> None:
        """HUD without the picture - the old DDA mode's shape. State only."""
        self._hud_only = bool(on)

    def draw_overlay(self, *_args) -> None:
        """Compose the HUD/menu into the frame.

        Not implemented on this backend: the overlay is drawn by the pygame layer on the
        Windows path, and this window is pysdl2. Kept so the loop's call sites stay honest
        about where the drawing was expected; the menu will not appear until this is built.
        """

    def draw_capture_overlay(self, _surface) -> None:
        """Bake the overlay into a screenshot. Nothing to bake here yet."""

    def enter_switch_mode(self, _frame, width: int, height: int) -> None:
        self._switch = (int(width), int(height))

    def exit_switch_mode(self) -> None:
        self._switch = None

    def is_switch_active(self) -> bool:
        return self._switch is not None

    def set_excluded_from_capture(self, on: bool) -> None:
        """Keep the overlay out of our own capture. Wayland has no such concept."""
        self._excluded = bool(on)

    def set_fullscreen_layer(self, width: int, height: int) -> None:
        self.resize(int(width), int(height))

    def set_window_layer(self, _x: int, _y: int, width: int, height: int) -> None:
        self.resize(int(width), int(height))

    def raise_topmost(self) -> None:
        """Put the overlay above the captured window, where the platform allows it.

        Wayland has no "raise someone else's surface" call, so this is best-effort: SDL raises
        our own window within our application, which is all the app can do here.
        """
        if self.window:
            try:
                sdl2.SDL_RaiseWindow(self.window)
            except Exception:
                pass

    def get_hwnd(self) -> int:
        """The native window handle. There is none on Linux; callers treat 0 as "no window"."""
        return 0

    def resize(self, width: int, height: int) -> None:
        """Resize the window and its streaming texture to a new frame size."""
        width, height = int(width), int(height)
        if width <= 0 or height <= 0 or (width, height) == (self.width, self.height):
            return
        self.width, self.height = width, height
        if self._closed:
            return
        if self.texture:
            sdl2.SDL_DestroyTexture(self.texture)
        if self.window:
            sdl2.SDL_SetWindowSize(self.window, width, height)
        self.texture = sdl2.SDL_CreateTexture(
            self.renderer, sdl2.SDL_PIXELFORMAT_RGBA32,
            sdl2.SDL_TEXTUREACCESS_STREAMING, width, height)

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