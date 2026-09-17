"""The Wayland capture pipeline: the string, and the failure modes.

No compositor and no display is involved, deliberately. The parts tested here
are the ones that cost a round trip when they are wrong: the gst-launch
invocation, and whether a failure says what actually happened instead of raising
something that reads like a bug in our own code.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from minimal import capture_wayland as cw  # noqa: E402
from minimal.capture import CaptureError  # noqa: E402
from minimal.portal import ScreenCast  # noqa: E402


def _capture(width=1920, height=1080, fd=None, serial=991, node_id=42):
    """A PortalCapture with the handshake bypassed, so only the pipeline is exercised.

    The fd is real (a devnull descriptor) rather than a made-up number: close()
    closes it, and closing a number this process does not own would take out an
    unrelated descriptor — which is exactly what an earlier version of this
    helper did.
    """
    if fd is None:
        fd = os.open(os.devnull, os.O_RDONLY)
    cap = cw.PortalCapture.__new__(cw.PortalCapture)
    cap.monitor_idx = 0
    cap._log = lambda *_: None
    cap._gst = "gst-launch-1.0"
    cap._proc = None
    cap._stderr = None
    cap._sc = ScreenCast(fd=fd, node_id=node_id, serial=serial, width=width,
                         height=height, restore_token=None, session_path="/x")
    cap.width, cap.height = width, height
    return cap


# --- the pipeline ----------------------------------------------------------

def test_pipeline_hands_pipewiresrc_the_fd():
    cap = _capture()
    args = cap._pipeline_args()
    assert "pipewiresrc" in args
    assert f"fd={cap._sc.fd}" in args
    cap.close()


def test_pipeline_targets_the_stream_by_serial():
    args = _capture()._pipeline_args()
    assert "target-object=991" in args
    assert not any(a.startswith("path=") for a in args), (
        "the node id is deprecated for targeting once a serial is published")


def test_pipeline_uses_the_node_id_when_there_is_no_serial():
    args = _capture(serial=None)._pipeline_args()
    assert "path=42" in args


def test_pipeline_asks_for_rgba_at_the_portal_size():
    args = _capture(width=2560, height=1440)._pipeline_args()
    caps = [a for a in args if a.startswith("video/x-raw")]
    assert len(caps) == 1
    assert "format=RGBA" in caps[0]
    assert "width=2560" in caps[0] and "height=1440" in caps[0]
    assert "pixel-aspect-ratio=1/1" in caps[0]


def test_pipeline_drops_stale_frames():
    """A mirror wants the newest frame, not a backlog of old ones."""
    args = _capture()._pipeline_args()
    joined = " ".join(args)
    assert "queue" in args and "max-size-buffers=1" in args and "leaky=downstream" in args


def test_pipeline_writes_raw_frames_to_our_stdout():
    args = _capture()._pipeline_args()
    assert args[-2:] == ["fdsink", "fd=1"]


def test_pipeline_is_quiet_by_default():
    assert "-q" in _capture()._pipeline_args()


# --- failure modes ---------------------------------------------------------

def test_requirements_names_the_missing_gstreamer(monkeypatch):
    monkeypatch.setattr(cw.shutil, "which", lambda _: None)
    usable, why = cw.requirements()
    assert usable is False
    assert "gst-launch-1.0" in why


def test_requirements_names_a_missing_pipewiresrc(monkeypatch):
    monkeypatch.setattr(cw.shutil, "which", lambda name: "/usr/bin/" + name)

    class _Fail:
        returncode = 1
        stdout = stderr = ""

    monkeypatch.setattr(cw.subprocess, "run", lambda *a, **k: _Fail())
    usable, why = cw.requirements()
    assert usable is False
    assert "pipewiresrc" in why


def test_grab_refuses_when_the_pipeline_is_not_running():
    cap = _capture()
    with pytest.raises(CaptureError, match="not running"):
        cap.grab()


def test_grab_explains_a_truncated_frame_with_the_pipeline_stderr(tmp_path):
    """A caps negotiation failure shows up as a short read. Say so, with GStreamer's own words."""
    cap = _capture(width=4, height=4)
    err = tmp_path / "gst.log"
    err.write_text("WARNING: erroneous pipeline: could not link pipewiresrc0\n"
                   "no element \"videoconvert\"\n")

    class _Stdout:
        def read(self, _n):
            return b""              # the child died: EOF straight away

    class _Proc:
        stdout = _Stdout()

    cap._proc = _Proc()
    cap._stderr = err
    with pytest.raises(CaptureError) as exc:
        cap.grab()
    msg = str(exc.value)
    assert "0 of 64 bytes" in msg
    assert "could not link pipewiresrc0" in msg, "the pipeline's stderr must come through"


def test_grab_assembles_a_frame_across_short_reads():
    """read() may return less than asked for; a frame must not be truncated."""
    cap = _capture(width=2, height=2)          # needs 16 bytes
    payload = bytes(range(16))

    class _Stdout:
        def __init__(self):
            self._chunks = [payload[:5], payload[5:6], payload[6:]]

        def read(self, _n):
            return self._chunks.pop(0) if self._chunks else b""

    class _Proc:
        stdout = _Stdout()

    cap._proc = _Proc()
    frame = cap.grab()
    assert frame.shape == (2, 2, 4)
    assert frame.dtype == np.uint8
    assert frame.reshape(-1).tolist() == list(payload)


def test_constructor_refuses_clearly_when_requirements_are_missing(monkeypatch):
    monkeypatch.setattr(cw.shutil, "which", lambda _: None)
    with pytest.raises(CaptureError, match="Wayland capture is not available"):
        cw.PortalCapture()


def test_close_is_safe_without_a_pipeline():
    cap = _capture()
    fd_before = cap._sc.fd
    cap.close()
    cap.close()
    assert cap._proc is None
    assert cap._sc.fd == -1
    assert fd_before >= 0


def test_window_capture_asks_the_portal_for_a_window(monkeypatch):
    """--source window must ask SelectSources for a WINDOW, not a screen.

    That flag alone decides what the portal offers the user, so getting it wrong
    silently captures the whole desktop and the cheaper thing we were after
    never happens — no error, just the old behaviour and the old cost. Asserted
    on the call the constructor actually makes.
    """
    from minimal.portal import SOURCE_MONITOR, SOURCE_WINDOW

    seen: list[dict] = []

    class _Session:
        width, height = 1280, 720

        def close(self):
            pass

    monkeypatch.setattr(cw, "requirements", lambda: (True, ""))
    monkeypatch.setattr(cw, "open_screencast",
                        lambda **kw: (seen.append(kw), _Session())[1])
    monkeypatch.setattr(cw.PortalCapture, "_start_pipeline", lambda self: None)

    cap = cw.PortalCapture(source=SOURCE_WINDOW)
    assert seen[-1]["types"] == SOURCE_WINDOW
    assert cap.source == SOURCE_WINDOW
    assert (cap.width, cap.height) == (1280, 720)

    cw.PortalCapture()                    # the default is still a whole screen
    assert seen[-1]["types"] == SOURCE_MONITOR