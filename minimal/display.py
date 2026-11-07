"""Presentation for the MVP — an SDL2 window with a streaming texture.

One window, one texture, one blit per frame. Click-through, HUD, menus and the
overlay UI are all later milestones.

`headless=True` builds the window hidden and never presents, which is what the
tests use: SDL2 still needs a video driver to create a renderer, so the tests
run under Xvfb.
"""

from __future__ import annotations

import ctypes

import numpy as np

try:
    import sdl2
    import sdl2.ext
    _HAS_SDL2 = True
except ImportError:  # pragma: no cover
    _HAS_SDL2 = False


class DisplayError(RuntimeError):
    """Raised when an SDL2 window or renderer cannot be created."""


# A 3x5 pixel font, scaled up at draw time. Three letters is all the badge needs ("ON" / "OFF"),
# and a bitmap here avoids pulling SDL_ttf - or pygame, which minimal/ deliberately does not use -
# into the one path that has to stay reliable.
_GLYPHS = {
    "O": ("111", "101", "101", "101", "111"),
    "N": ("101", "111", "111", "111", "101"),
    "F": ("111", "100", "110", "100", "100"),
}
_GLYPH_ADVANCE = 4          # 3 wide + 1 gap, in font pixels


def indicator_layout(text: str, x: int, y: int, scale: int) -> tuple[int, int, int, int]:
    """The badge rect for `text` at (x, y), in screen pixels. Pure, so it can be tested."""
    return (x, y, len(text) * _GLYPH_ADVANCE * scale, 5 * scale)


def glyph_pixels(text: str, x: int, y: int, scale: int):
    """(rect, is_lit) for every cell of `text`, so a caller can draw without knowing the font."""
    out = []
    cursor = x
    for char in text:
        rows = _GLYPHS.get(char)
        if rows is None:
            cursor += _GLYPH_ADVANCE * scale
            continue
        for row, bits in enumerate(rows):
            for col, bit in enumerate(bits):
                out.append(((cursor + col * scale, y + row * scale, scale, scale), bit == "1"))
        cursor += _GLYPH_ADVANCE * scale
    return out


class Display:
    """An SDL2 window that shows RGBA frames."""

    def __init__(self, width: int, height: int, *, fullscreen: bool = False,
                 headless: bool = False, title: str = "NeuralScreen (MVP)",
                 indicator: bool = False):
        if not _HAS_SDL2:
            from minimal.deps import hint
            raise DisplayError(hint("pysdl2", "sdl2"))

        self.width, self.height = int(width), int(height)
        self.headless = headless
        # The enhancement badge. Drawn by the renderer after the frame is copied, never into the
        # frame itself: a saved PNG must be the pass's output, not the UI.
        self.indicator = bool(indicator)
        self.enhanced = True
        self.badge_scale = max(3, int(height / 360))

        if sdl2.SDL_InitSubSystem(sdl2.SDL_INIT_VIDEO) != 0:
            raise DisplayError(f"SDL_InitSubSystem failed: {sdl2.SDL_GetError()}")

        flags = sdl2.SDL_WINDOW_BORDERLESS | sdl2.SDL_WINDOW_ALWAYS_ON_TOP
        if headless:
            flags |= sdl2.SDL_WINDOW_HIDDEN
        if fullscreen:
            flags |= sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP

        self.window = sdl2.SDL_CreateWindow(
            title.encode(), sdl2.SDL_WINDOWPOS_UNDEFINED, sdl2.SDL_WINDOWPOS_UNDEFINED,
            self.width, self.height, flags)
        if not self.window:
            raise DisplayError(f"SDL_CreateWindow failed: {sdl2.SDL_GetError()}")

        self.renderer = sdl2.SDL_CreateRenderer(
            self.window, -1, sdl2.SDL_RENDERER_ACCELERATED)
        if not self.renderer:
            # No accelerated driver (a bare Xvfb, for instance): the software
            # renderer is slower but perfectly good for proving the pipeline.
            self.renderer = sdl2.SDL_CreateRenderer(
                self.window, -1, sdl2.SDL_RENDERER_SOFTWARE)
        if not self.renderer:
            raise DisplayError(f"SDL_CreateRenderer failed: {sdl2.SDL_GetError()}")

        # Frames arrive as RGBA; on a little-endian machine that is
        # SDL_PIXELFORMAT_ABGR8888.
        # The present scales the frame into the window, and says so: the window is the desktop in
        # fullscreen, so a pipeline running at 1920x1080 on a 2560x1440 screen was stretched only
        # because SDL_RenderCopy fills its target by default. The logical size makes the frame's
        # resolution the contract and the window the scaler - see display_linux.py, where the same
        # line is what makes an internal 1080p pipeline present correctly at 1440p.
        sdl2.SDL_SetHint(sdl2.SDL_HINT_RENDER_SCALE_QUALITY, b"linear")
        sdl2.SDL_RenderSetLogicalSize(self.renderer, self.width, self.height)
        self.texture = sdl2.SDL_CreateTexture(
            self.renderer, sdl2.SDL_PIXELFORMAT_ABGR8888,
            sdl2.SDL_TEXTUREACCESS_STREAMING, self.width, self.height)
        if not self.texture:
            raise DisplayError(f"SDL_CreateTexture failed: {sdl2.SDL_GetError()}")

        self.frames_shown = 0
        self.clear()

    def clear(self) -> None:
        """Paint the window black and present it.

        The window exists from setup, but nothing is drawn into it until the worker
        answers its first frame — and with the native worker that first frame is a model
        load plus the JIT of 249 PTX kernels, so the wait is seconds long and worth
        seeing. Until something is presented the surface holds whatever the driver left
        in it: on an accelerated renderer that can be a solid colour, and a solid amber
        or yellow fullscreen window reads as "the pipeline is broken" when it is only
        waiting for frame 0. Black says the same thing the log does.
        """
        if self.headless:
            return
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 255)
        sdl2.SDL_RenderClear(self.renderer)
        sdl2.SDL_RenderPresent(self.renderer)

    def show(self, frame_rgba: np.ndarray) -> None:
        """Upload one (H, W, 4) uint8 RGBA frame and present it."""
        if frame_rgba.dtype != np.uint8 or frame_rgba.ndim != 3:
            raise ValueError(f"expected uint8 (H, W, 4), got {frame_rgba.shape} {frame_rgba.dtype}")
        h, w = frame_rgba.shape[:2]
        if (w, h) != (self.width, self.height):
            raise ValueError(
                f"frame is {w}x{h}, the window is {self.width}x{self.height}")

        ptr = frame_rgba.ctypes.data_as(ctypes.c_void_p)
        if sdl2.SDL_UpdateTexture(self.texture, None, ptr, w * 4) != 0:
            raise DisplayError(f"SDL_UpdateTexture failed: {sdl2.SDL_GetError()}")

        if self.headless:
            self.frames_shown += 1
            return

        sdl2.SDL_RenderClear(self.renderer)
        sdl2.SDL_RenderCopy(self.renderer, self.texture, None, None)
        if self.indicator:
            self._draw_indicator()
        sdl2.SDL_RenderPresent(self.renderer)
        self.frames_shown += 1

    def set_enhanced(self, on: bool) -> None:
        """Tell the badge whether the pass is running. Called every frame by the loop."""
        self.enhanced = bool(on)

    def _draw_indicator(self) -> None:
        """A badge in the top-left corner: green "ON" while the pass runs, grey "OFF" when not.

        Colour AND text, because a colour alone is ambiguous on a busy picture and a colour-blind
        viewer may not separate them. The badge sits on its own dark plate so it reads on any
        content; the plate is what makes it legible over a bright sky as well as a dark one.
        """
        text = "ON" if self.enhanced else "OFF"
        pad = 2 * self.badge_scale
        x0, y0 = 4 * self.badge_scale, 4 * self.badge_scale
        _, _, text_w, text_h = indicator_layout(text, x0 + pad, y0 + pad, self.badge_scale)
        plate = sdl2.SDL_Rect(x0, y0, text_w + 2 * pad, text_h + 2 * pad)

        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 170)
        sdl2.SDL_RenderFillRect(self.renderer, ctypes.byref(plate))

        lit = (40, 210, 90) if self.enhanced else (150, 150, 150)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 190)
        border = sdl2.SDL_Rect(plate.x, plate.y, plate.w, self.badge_scale)
        sdl2.SDL_RenderFillRect(self.renderer, ctypes.byref(border))
        border = sdl2.SDL_Rect(plate.x, plate.y + plate.h - self.badge_scale,
                               plate.w, self.badge_scale)
        sdl2.SDL_RenderFillRect(self.renderer, ctypes.byref(border))

        for (rx, ry, rw, rh), is_on in glyph_pixels(text, x0 + pad, y0 + pad, self.badge_scale):
            if not is_on:
                continue
            sdl2.SDL_SetRenderDrawColor(self.renderer, lit[0], lit[1], lit[2], 255)
            rect = sdl2.SDL_Rect(rx, ry, rw, rh)
            sdl2.SDL_RenderFillRect(self.renderer, ctypes.byref(rect))

    def poll_events(self) -> list[str]:
        """Drain the event queue; returns ['quit'] if the user closed the window."""
        events: list[str] = []
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                events.append("quit")
            elif event.type == sdl2.SDL_KEYDOWN and event.key.keysym.sym in (
                    sdl2.SDLK_ESCAPE, sdl2.SDLK_q):
                events.append("quit")
            elif event.type == sdl2.SDL_KEYDOWN and event.key.keysym.sym in (
                    sdl2.SDLK_F1, sdl2.SDLK_SPACE):
                # Window-level A/B. The global X grab cannot see keys pressed in a Wayland-native
                # window, so this is the one that works whenever this window has focus.
                events.append("toggle")
        return events

    def close(self) -> None:
        for attr in ("texture", "renderer", "window"):
            obj = getattr(self, attr, None)
            if obj:
                try:
                    if attr == "texture":
                        sdl2.SDL_DestroyTexture(obj)
                    elif attr == "renderer":
                        sdl2.SDL_DestroyRenderer(obj)
                    else:
                        sdl2.SDL_DestroyWindow(obj)
                except Exception:
                    pass
                setattr(self, attr, None)
        try:
            sdl2.SDL_QuitSubSystem(sdl2.SDL_INIT_VIDEO)
        except Exception:
            pass

    def __enter__(self) -> "Display":
        return self

    def __exit__(self, *exc) -> None:
        self.close()