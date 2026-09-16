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


class Display:
    """An SDL2 window that shows RGBA frames."""

    def __init__(self, width: int, height: int, *, fullscreen: bool = False,
                 headless: bool = False, title: str = "NeuralScreen (MVP)"):
        if not _HAS_SDL2:
            raise DisplayError("pysdl2 is not installed (pip install pysdl2)")

        self.width, self.height = int(width), int(height)
        self.headless = headless

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
        self.texture = sdl2.SDL_CreateTexture(
            self.renderer, sdl2.SDL_PIXELFORMAT_ABGR8888,
            sdl2.SDL_TEXTUREACCESS_STREAMING, self.width, self.height)
        if not self.texture:
            raise DisplayError(f"SDL_CreateTexture failed: {sdl2.SDL_GetError()}")

        self.frames_shown = 0

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
        sdl2.SDL_RenderPresent(self.renderer)
        self.frames_shown += 1

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