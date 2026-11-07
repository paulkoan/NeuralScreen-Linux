"""Which hotkey backend to use, and what to say when it cannot be used.

Two backends exist and they fail in opposite circumstances:

    hotkeys_evdev   reads /dev/input/event*, so it works on Wayland and X11 alike, and needs
                    read access to those nodes (the `input` group).
    hotkeys_linux   grabs the key through XGrabKey. It works when the focused window is an X11
                    client, and on a Wayland session it cannot work at all — the compositor
                    never routes a Wayland client's keys through XWayland, so the grab registers
                    and then silently never fires. That silence is why Ctrl+Alt+1 did nothing.

So the session decides which one to try first, and the other is the fallback. Both are injected
rather than imported at module scope, so this decision is testable without a keyboard.
"""
from __future__ import annotations

import os
import sys

# The bindings the MVP wants. Kept here so both backends register the same set.
DEFAULT_BINDINGS: tuple[tuple[str, str], ...] = (
    ("Ctrl+Alt+1", "toggle"),
    ("Ctrl+Alt+Q", "quit"),
)


def on_wayland(env: dict | None = None) -> bool:
    """True when the session is Wayland, by either of the two ways it announces itself."""
    env = os.environ if env is None else env
    if env.get("WAYLAND_DISPLAY"):
        return True
    return str(env.get("XDG_SESSION_TYPE", "")).lower() == "wayland"


def _default_backends() -> dict:
    import hotkeys_evdev
    backends = {"evdev": hotkeys_evdev}
    try:
        import hotkeys_linux
        backends["x11"] = hotkeys_linux
    except Exception:      # libX11 absent: nothing to fall back to
        pass
    return backends


def install(pipe, *, env=None, log=print, backends=None,
            bindings: tuple[tuple[str, str], ...] = DEFAULT_BINDINGS) -> str | None:
    """Register the bindings on the best backend available.

    Returns the name of the backend that took, or None. Never raises: a run without hotkeys is
    still a run, and the F1/Space keys in the output window and the A/B timer both survive it.
    """
    backends = _default_backends() if backends is None else backends
    order = ["evdev", "x11"] if on_wayland(env) else ["x11", "evdev"]
    reasons = []

    for name in order:
        module = backends.get(name)
        if module is None:
            reasons.append(f"{name}: not available")
            continue
        try:
            for combo, command in bindings:
                module.register_global_hotkey(
                    combo, (lambda c: (lambda _name: pipe.commands.put(c)))(command))
            poll = getattr(module, "poll_events", None)
            if poll is not None:
                pipe.hotkey_poll = poll
        except Exception as exc:
            reasons.append(f"{name}: {exc}")
            continue
        where = "Wayland" if on_wayland(env) else "X11"
        log(f"hotkeys: {', '.join(c for c, _ in bindings)} via {name} ({where} session)")
        if reasons:
            log(f"hotkeys: tried before that - {'; '.join(reasons)}", file=sys.stderr)
        return name

    log("hotkeys: none of the backends could register - the output window's F1/Space still "
        "toggles, and the A/B timer needs nothing"
        + (f" ({'; '.join(reasons)})" if reasons else ""), file=sys.stderr)
    return None


def uninstall(backends=None) -> None:
    """Release whatever install() took. Safe to call when nothing was registered."""
    for module in (_default_backends() if backends is None else backends).values():
        fn = getattr(module, "unregister_all", None)
        if fn is None:
            continue
        try:
            fn()
        except Exception:
            pass
