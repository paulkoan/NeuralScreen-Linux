"""Wayland capture: the parts that can be checked without a compositor.

The portal handshake itself needs a live session bus and a user to answer a
dialog, so it is exercised by tools/wayland_probe.py on the desktop, not here.
What is tested here is everything that would otherwise fail silently and be
expensive to discover on the GPU box:

  * the vardict options — jeepney encodes a variant as a (signature, value)
    pair, and one wrong pair produces a marshalling error from inside the bus
    code that says nothing about the actual mistake;
  * what we read out of the Start response, including the case where a backend
    publishes no `pipewire-serial` (interface < 6);
  * how a stream is targeted — node id versus serial is the difference between
    working now and breaking on a hotplug or a resolution change;
  * the gst-launch pipeline string, which is where a typo costs a round trip.

None of these use the xvfb fixture or a display: they must not need one.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from minimal import portal  # noqa: E402


# --- options ---------------------------------------------------------------

def test_sources_options_are_variant_pairs():
    opts = portal.sources_options(types=portal.SOURCE_MONITOR, cursor_mode=portal.CURSOR_EMBEDDED)
    assert opts["types"] == ("u", 1)
    assert opts["multiple"] == ("b", False)
    assert opts["cursor_mode"] == ("u", 2)
    # restore_token is optional; sending an empty one makes some backends refuse
    assert "restore_token" not in opts


def test_sources_options_pass_a_restore_token_when_given():
    opts = portal.sources_options(restore_token="tok-123")
    assert opts["restore_token"] == ("s", "tok-123")


def test_sources_options_do_not_send_a_blank_restore_token():
    assert "restore_token" not in portal.sources_options(restore_token="")


# --- handle_token, which is where the handshake actually broke -------------

def test_handle_token_is_a_variant_pair_not_a_bare_string():
    """A bare string here is what killed the handshake on the GPU box."""
    out = portal.with_handle_token(({"session_handle_token": ("s", "x")},), "tok")
    assert out[-1]["handle_token"] == ("s", "tok")


def test_handle_token_overrides_whatever_was_already_there():
    out = portal.with_handle_token(({"handle_token": ("s", "old")},), "new")
    assert out[-1]["handle_token"] == ("s", "new")


def test_handle_token_does_not_mutate_the_caller_s_arguments():
    args = ({"a": ("s", "b")},)
    portal.with_handle_token(args, "tok")
    assert "handle_token" not in args[0], "the caller's dict was modified in place"


def _call_bodies():
    """The exact arguments open_screencast sends, per call."""
    return [
        ("CreateSession", "a{sv}",
         ({"session_handle_token": ("s", "nsl_port")},), "nsl_create"),
        ("SelectSources", "oa{sv}",
         ("/org/freedesktop/portal/desktop/session/1_1/nsl", portal.sources_options()), "nsl_select"),
        ("Start", "osa{sv}",
         ("/org/freedesktop/portal/desktop/session/1_1/nsl", "", {}), "nsl_start"),
    ]


def test_every_call_body_serialises():
    """The check that would have caught it: hand each body to jeepney's marshaller.

    A bad variant raises from deep inside the serialiser — `sig, data =
    "nsl_create"` — naming neither the option nor the call. Nothing short of
    serialising the real message exposes it, which is why it survived to the GPU
    box: every test up to this point only ever inspected the dicts.
    """
    import array
    from jeepney import DBusAddress, new_method_call

    addr = DBusAddress(portal.PORTAL_PATH, bus_name=portal.PORTAL_BUS,
                       interface=portal.SCREENCAST_IFACE)
    for method, signature, args, token in _call_bodies():
        body = portal.with_handle_token(args, token)
        msg = new_method_call(addr, method, signature, body)
        # serial is normally assigned by the connection; a standalone message has
        # to be given one or the header cannot be packed.
        msg.serialise(serial=1, fds=array.array("i"))     # must not raise


def test_the_marshaller_really_does_reject_a_bare_string():
    """Prove the check above bites, by feeding it the original bug."""
    import array
    from jeepney import DBusAddress, new_method_call

    addr = DBusAddress(portal.PORTAL_PATH, bus_name=portal.PORTAL_BUS,
                       interface=portal.SCREENCAST_IFACE)
    msg = new_method_call(addr, "CreateSession", "a{sv}",
                          ({"handle_token": "not-a-variant"},))
    with pytest.raises((ValueError, TypeError)) as exc:
        msg.serialise(serial=1, fds=array.array("i"))
    # The same message the GPU box printed.
    assert "unpack" in str(exc.value), (
        f"expected the unpacking failure the handshake hit, got: {exc.value}")


# --- the Start response ----------------------------------------------------

def test_parse_streams_reads_serial_and_size():
    results = {
        "streams": ("a(ua{sv})", [
            (42, {
                "size": ("(ii)", (2560, 1440)),
                "position": ("(ii)", (0, 0)),
                "pipewire-serial": ("t", 991),
                "id": ("s", "opaque"),
            }),
        ]),
        "restore_token": ("s", "restore-me"),
    }
    parsed = portal.parse_streams(results)
    assert parsed["node_id"] == 42
    assert parsed["serial"] == 991
    assert (parsed["width"], parsed["height"]) == (2560, 1440)
    assert parsed["restore_token"] == "restore-me"


def test_parse_streams_survives_a_pre_v6_backend():
    """Interface < 6 publishes no pipewire-serial; the node id has to carry it."""
    results = {"streams": ("a(ua{sv})", [(7, {"size": ("(ii)", (1920, 1080))})])}
    parsed = portal.parse_streams(results)
    assert parsed["node_id"] == 7
    assert parsed["serial"] is None
    assert (parsed["width"], parsed["height"]) == (1920, 1080)
    assert parsed["restore_token"] is None


def test_parse_streams_on_an_empty_or_hostile_response():
    """A backend that answers with nothing must not crash the parser."""
    for results in ({}, {"streams": ("a(ua{sv})", [])}, {"streams": None}):
        parsed = portal.parse_streams(results)
        assert parsed["node_id"] is None
        assert parsed["serial"] is None
        assert (parsed["width"], parsed["height"]) == (0, 0)


def test_stream_without_a_size_is_reported_as_zero_not_guessed():
    parsed = portal.parse_streams({"streams": ("a(ua{sv})", [(3, {})])})
    assert parsed["node_id"] == 3
    assert (parsed["width"], parsed["height"]) == (0, 0)


# --- stream targeting ------------------------------------------------------

def test_target_prefers_the_serial_when_present():
    """Node ids are reused after destruction, so the serial is the safe target."""
    sc = portal.ScreenCast(fd=-1, node_id=42, serial=991, width=1, height=1,
                           restore_token=None, session_path="/x")
    assert sc.pipewire_target == ["target-object=991"]


def test_target_falls_back_to_the_node_id():
    sc = portal.ScreenCast(fd=-1, node_id=42, serial=None, width=1, height=1,
                           restore_token=None, session_path="/x")
    assert sc.pipewire_target == ["path=42"]


def test_close_releases_the_fd_and_is_idempotent():
    read_fd, write_fd = os.pipe()
    sc = portal.ScreenCast(fd=read_fd, node_id=1, serial=None, width=1, height=1,
                           restore_token=None, session_path="/x")
    sc.close()
    sc.close()                      # must not raise on a second call
    assert sc.fd == -1
    with pytest.raises(OSError):
        os.fstat(read_fd)           # it really is closed
    os.close(write_fd)


# --- reporting -------------------------------------------------------------

def test_available_returns_a_reason_not_an_exception():
    """Callers print this; it must never raise, whatever the environment."""
    usable, why = portal.available()
    assert isinstance(usable, bool)
    assert isinstance(why, str) and why