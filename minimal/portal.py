"""XDG Desktop Portal ScreenCast — get a PipeWire remote for the screen.

Why this exists: `minimal/capture.py` grabs through mss, which is X11. On a
Wayland desktop the XWayland root window is black — applications draw on the
compositor, not there — so every frame comes back empty and the pipeline looks
broken when only the capture is. The portal is the compositor-agnostic way in:
the user approves a screen once, and we get a PipeWire remote to read frames
from. It is one implementation for GNOME, KDE, wlroots and everything else.

The handshake, straight from `data/org.freedesktop.portal.ScreenCast.xml`:

    CreateSession(options)        -> request handle; session handle in the signal
    SelectSources(session, opts)  -> request handle
    Start(session, "", opts)      -> Response results carry `streams` (a(ua{sv}))
    OpenPipeWireRemote(session)   -> fd, an `h` in the *body*

**The fd does not come from Start.** It is a separate call
(`<arg type="h" name="fd" direction="out"/>`). A client that waits for it on the
Start response waits forever — the common way to get this wrong.

Responses arrive asynchronously: each of those calls returns a Request object
path immediately, and the real answer comes as a
`org.freedesktop.portal.Request.Response` signal with `(u response, a{sv}
results)` where response is 0 = success, 1 = the user cancelled, 2 = other error.

Everything here is deliberately synchronous and single-request-at-a-time: this is
a CLI tool, and matching every Response signal regardless of path is far more
robust than predicting the request path from our own unique bus name.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

try:  # a runtime dependency, not an import-time cliff: the MVP must still run
    from jeepney import DBusAddress, MatchRule, message_bus, new_method_call
    from jeepney.io.blocking import open_dbus_connection
    _HAS_JEEPNEY = True
except ImportError:  # pragma: no cover - environment problem, not logic
    _HAS_JEEPNEY = False

PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SCREENCAST_IFACE = "org.freedesktop.portal.ScreenCast"
REQUEST_IFACE = "org.freedesktop.portal.Request"

# SelectSources `types`: what the user may pick.
SOURCE_MONITOR = 1
SOURCE_WINDOW = 2
SOURCE_VIRTUAL = 4

# `cursor_mode`
CURSOR_HIDDEN = 1
CURSOR_EMBEDDED = 2
CURSOR_METADATA = 4

RESPONSE_SUCCESS = 0
RESPONSE_CANCELLED = 1
RESPONSE_FAILED = 2


class PortalError(RuntimeError):
    """The portal is unusable: missing, refused, or answered with an error."""


@dataclass
class ScreenCast:
    """A live screen-cast session plus the handle we read frames from."""

    fd: int                       # raw PipeWire remote fd; the caller owns it
    node_id: int                  # deprecated for targeting but widely supported
    serial: int | None            # `pipewire-serial` (interface v6+): preferred
    width: int
    height: int
    restore_token: str | None
    session_path: str
    _conn: object = field(default=None, repr=False)

    @property
    def pipewire_target(self) -> list[str]:
        """gst-launch arguments that name this stream.

        Interface v6 deprecates the node id for targeting — node ids are reused
        after destruction, so a hotplug or a resolution change can make a stale
        id point at a different stream. `target-object` with the serial is the
        supported way, and `path` is the fallback for older backends that do not
        publish a serial.
        """
        if self.serial is not None:
            return ["target-object=%d" % self.serial]
        return ["path=%d" % self.node_id]

    def close(self) -> None:
        if self.fd >= 0:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = -1


def available() -> tuple[bool, str]:
    """(usable, why not) — cheap enough to call before doing anything."""
    if not _HAS_JEEPNEY:
        return False, "jeepney is not installed (pip install jeepney)"
    if not os.environ.get("DBUS_SESSION_BUS_ADDRESS") and not os.environ.get(
            "XDG_RUNTIME_DIR"):
        return False, "no session bus (DBUS_SESSION_BUS_ADDRESS and XDG_RUNTIME_DIR are unset)"
    try:
        conn = open_dbus_connection(bus="SESSION")
    except Exception as exc:
        return False, f"cannot open the session bus: {exc}"
    try:
        reply = conn.send_and_get_reply(
            new_method_call(message_bus, "NameHasOwner", "s", (PORTAL_BUS,)))
        if not reply.body[0]:
            return False, (
                f"{PORTAL_BUS} is not running — install xdg-desktop-portal and the "
                "backend for your desktop (xdg-desktop-portal-kde on Plasma)")
        props = _get_properties(conn, SCREENCAST_IFACE)
        if "version" not in props:
            return False, f"{PORTAL_BUS} has no ScreenCast interface"
        return True, f"ScreenCast interface version {props['version'][1]}"
    except Exception as exc:
        return False, f"portal query failed: {exc}"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _get_properties(conn, interface: str) -> dict:
    addr = DBusAddress(PORTAL_PATH, bus_name=PORTAL_BUS, interface="org.freedesktop.DBus.Properties")
    reply = conn.send_and_get_reply(new_method_call(addr, "GetAll", "s", (interface,)))
    return reply.body[0]


def screencast_version() -> int:
    """The interface version, or 0 if it cannot be read.

    Version 6 changes how a stream should be targeted (see `ScreenCast.pipewire_target`).
    """
    usable, _ = available()
    if not usable:
        return 0
    conn = open_dbus_connection(bus="SESSION")
    try:
        return int(_get_properties(conn, SCREENCAST_IFACE).get("version", ("u", 0))[1])
    except Exception:
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


# --- options ---------------------------------------------------------------
# Split out because they are the part worth testing: jeepney encodes a variant
# as a (signature, value) pair, and getting one of those wrong produces a
# marshalling error from deep inside the bus code that says nothing useful.

def with_handle_token(args: tuple, token: str) -> tuple:
    """Return `args` with `handle_token` set in its trailing vardict.

    The value must be a variant pair, `("s", token)`.

    A bare string here is a real mistake this had: jeepney serialises a variant
    by unpacking `(signature, value)`, so a plain string is unpacked instead —
    `sig, data = "nsl_create"` — and the handshake dies on its first call with
    `too many values to unpack (expected 2)`, naming neither the option nor the
    call it came from. Every value in an `a{sv}` dict has this shape.
    """
    body = list(args)
    opts = dict(body[-1])
    opts["handle_token"] = ("s", token)
    body[-1] = opts
    return tuple(body)


def sources_options(*, types: int = SOURCE_MONITOR, multiple: bool = False,
                    cursor_mode: int = CURSOR_EMBEDDED,
                    restore_token: str | None = None) -> dict:
    opts = {
        "types": ("u", types),
        "multiple": ("b", multiple),
        "cursor_mode": ("u", cursor_mode),
    }
    if restore_token:
        opts["restore_token"] = ("s", restore_token)
    return opts


def parse_streams(results: dict) -> dict:
    """Pull the interesting fields out of a Start Response's `results`.

    Everything in a vardict arrives as a (signature, value) pair, so each field
    has to be unwrapped. Returns a dict with node_id, serial, width, height and
    restore_token, any of which may be missing on a hostile or minimal backend.
    """
    def unwrap(v, default=None):
        return v[1] if isinstance(v, tuple) and len(v) == 2 else (v if v is not None else default)

    out = {"node_id": None, "serial": None, "width": 0, "height": 0,
           "restore_token": None}

    streams = unwrap(results.get("streams"), []) or []
    if streams:
        first = streams[0]
        node_id, props = first[0], first[1]
        out["node_id"] = int(node_id)
        props = props or {}
        size = unwrap(props.get("size"))
        if isinstance(size, (tuple, list)) and len(size) == 2:
            out["width"], out["height"] = int(size[0]), int(size[1])
        serial = unwrap(props.get("pipewire-serial"))
        if serial is not None:
            out["serial"] = int(serial)
        sid = unwrap(props.get("id"))
        if sid is not None and out["serial"] is None:
            # No serial published (interface < 6). Keep the opaque id for the log.
            out["stream_id"] = sid

    token = unwrap(results.get("restore_token"))
    if token is not None:
        out["restore_token"] = str(token)
    return out


# --- the handshake ----------------------------------------------------------

def _request(conn, queue, addr, rule, method, signature, args, token, timeout):
    """Call a portal method whose real answer is a Response signal.

    Every portal method that starts an interaction returns a Request handle
    straight away and answers later on the bus. `handle_token` is passed so the
    handle is predictable, but the returned path is used rather than the
    predicted one.
    """
    body = with_handle_token(args, token)

    with conn.filter(rule, queue=queue):
        reply = conn.send_and_get_reply(
            new_method_call(addr, method, signature, body), timeout=timeout)
        handle = reply.body[0]
        signal = conn.recv_until_filtered(queue, timeout=timeout)

    code, results = signal.body
    if code != RESPONSE_SUCCESS:
        if code == RESPONSE_CANCELLED:
            raise PortalError("the screen-sharing prompt was cancelled")
        raise PortalError(f"the portal returned response code {code}")
    return handle, results


def open_screencast(*, types: int = SOURCE_MONITOR, cursor_mode: int = CURSOR_EMBEDDED,
                    restore_token: str | None = None, timeout: float = 120.0,
                    log=print) -> ScreenCast:
    """Run the ScreenCast handshake and return a session with a PipeWire fd.

    `timeout` bounds each wait, because the user has to answer a dialog: whoever
    calls this should say so before it blocks.
    """
    if not _HAS_JEEPNEY:
        raise PortalError("jeepney is not installed (pip install jeepney)")

    conn = open_dbus_connection(bus="SESSION", enable_fds=True)
    addr = DBusAddress(PORTAL_PATH, bus_name=PORTAL_BUS, interface=SCREENCAST_IFACE)

    # Match every Response regardless of path. One request is in flight at a
    # time, so there is nothing to confuse it with, and it avoids depending on
    # the predicted request-path format (which differs between portal versions).
    rule = MatchRule(type="signal", interface=REQUEST_IFACE, member="Response")
    try:
        conn.send_and_get_reply(message_bus.AddMatch(rule), timeout=timeout)
    except Exception as exc:
        raise PortalError(f"could not subscribe to portal responses: {exc}") from exc

    from collections import deque
    queue: deque = deque(maxlen=8)

    try:
        log("  CreateSession")
        _, results = _request(
            conn, queue, addr, rule, "CreateSession", "a{sv}",
            ({"session_handle_token": ("s", "nsl_port"), "handle_token": ("s", "nsl_create")},),
            "nsl_create", timeout)
        session_path = results.get("session_handle")
        session_path = session_path[1] if isinstance(session_path, tuple) else session_path
        if not session_path:
            raise PortalError("CreateSession returned no session handle")
        log(f"  session {session_path}")

        session_addr = DBusAddress(session_path, bus_name=PORTAL_BUS, interface=SCREENCAST_IFACE)

        log("  SelectSources")
        _request(conn, queue, addr, rule, "SelectSources", "oa{sv}",
                 (session_path,
                  sources_options(types=types, multiple=False, cursor_mode=cursor_mode,
                                  restore_token=restore_token)),
                 "nsl_select", timeout)

        log("  Start  (the compositor will ask you to choose a screen)")
        _, results = _request(conn, queue, addr, rule, "Start", "osa{sv}",
                              (session_path, "", {"handle_token": ("s", "nsl_start")}),
                              "nsl_start", timeout)
        parsed = parse_streams(results)
        if parsed["node_id"] is None:
            raise PortalError("Start returned no streams")
        log(f"  stream node={parsed['node_id']} serial={parsed['serial']} "
            f"{parsed['width']}x{parsed['height']}")

        # The fd is its own call — NOT part of the Start response.
        log("  OpenPipeWireRemote")
        reply = conn.send_and_get_reply(
            new_method_call(addr, "OpenPipeWireRemote", "oa{sv}", (session_path, {})),
            timeout=timeout)
        fd_obj = reply.body[0]
        raw_fd = fd_obj.to_raw_fd() if hasattr(fd_obj, "to_raw_fd") else int(fd_obj)

        return ScreenCast(fd=raw_fd, node_id=parsed["node_id"], serial=parsed["serial"],
                          width=parsed["width"], height=parsed["height"],
                          restore_token=parsed["restore_token"],
                          session_path=session_path, _conn=conn)
    except PortalError:
        conn.close()
        raise
    except Exception as exc:
        conn.close()
        # The type matters: a bare message like "too many values to unpack"
        # reads as prose and hides that it is a marshalling failure.
        raise PortalError(
            f"the portal handshake failed ({type(exc).__name__}): {exc}") from exc