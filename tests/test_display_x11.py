"""The X11 click-through path: ctypes signatures, and not touching X11 on a Wayland window.

v1's first segfault was here. `XOpenDisplay` returns a `Display*`, and without `restype` ctypes
assumes `int` - so the pointer was truncated to 32 bits and the next call, `XDefaultRootWindow`,
dereferenced it. The crash landed in `_ensure_x11` with no Python-level explanation until
faulthandler was turned on.

These tests do not need an X server: the signatures are declared before the display is opened, so
they can be checked even when opening it fails.
"""
from __future__ import annotations

import ctypes
import ctypes.util

import pytest

# display_linux refuses to import without pysdl2, and pysdl2 raises RuntimeError (not
# ImportError) when libSDL2 itself is missing - one of the sandbox's environment gaps. The box has
# it, so these run there.
try:
    import sdl2  # noqa: F401
except (ImportError, RuntimeError) as exc:      # pragma: no cover - environment dependent
    pytest.skip(f"pysdl2/SDL2 is unusable here: {exc}", allow_module_level=True)

import display_linux


def _xlib_available() -> bool:
    return bool(ctypes.util.find_library("X11"))


@pytest.mark.skipif(not _xlib_available(), reason="libX11 is not installed")
def test_the_display_pointer_is_not_truncated():
    """The bug: restype defaulted to int, so a 64-bit pointer became 32 bits."""
    display_linux._XLIB = None          # force a fresh load
    display_linux._ensure_x11()         # may fail to open a display; the types are set first
    assert display_linux._XLIB is not None
    assert display_linux._XLIB.XOpenDisplay.restype is ctypes.c_void_p
    assert display_linux._XLIB.XDefaultRootWindow.restype is ctypes.c_ulong
    assert display_linux._XLIB.XDefaultRootWindow.argtypes == [ctypes.c_void_p]


@pytest.mark.skipif(not _xlib_available(), reason="libX11 is not installed")
def test_the_calls_that_take_the_display_declare_it():
    display_linux._XLIB = None
    display_linux._ensure_x11()
    for name in ("XInternAtom", "XChangeProperty", "XFlush", "XCloseDisplay"):
        fn = getattr(display_linux._XLIB, name)
        assert fn.argtypes, f"{name} has no argtypes; a pointer argument would be truncated"
        assert fn.argtypes[0] is ctypes.c_void_p, f"{name} must take the Display* as c_void_p"


def test_click_through_is_skipped_when_the_window_is_not_x11():
    """On Wayland the SDL union holds Wayland data; reading x11.window gives a garbage id."""
    source = open(display_linux.__file__, encoding="utf-8").read()
    assert "info.subsystem != sdl2.SDL_SYSWM_X11" in source
    assert source.count("info.subsystem != sdl2.SDL_SYSWM_X11") >= 2, (
        "both the set and the unset path must check the subsystem")


@pytest.mark.skipif(not _xlib_available(), reason="libX11 is not installed")
def test_every_xlib_call_declares_its_signature():
    """The general form of the segfault: any call without argtypes truncates a pointer argument."""
    import re
    source = open(display_linux.__file__, encoding="utf-8").read()
    used = sorted(set(re.findall(r"_XLIB\.(X[A-Za-z]+)", source)))
    assert used, "no Xlib calls found - the regex or the module changed"

    display_linux._XLIB = None
    display_linux._ensure_x11()
    lib = display_linux._XLIB
    assert lib is not None
    undeclared = [name for name in used if not getattr(lib, name).argtypes]
    assert not undeclared, (
        "these are called without argtypes, so their pointer arguments are truncated: "
        + ", ".join(undeclared))
