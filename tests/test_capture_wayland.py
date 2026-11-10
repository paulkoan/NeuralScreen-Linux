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


def _capture(width=1920, height=1080, fd=None, serial=991, node_id=42, transport=cw.PIPE):
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
    cap.source = cw.SOURCE_MONITOR
    cap.video_scale = True
    cap.transport = transport
    cap.shm_poll = 0.0002
    cap.shm_timeout = 30.0
    cap._log = lambda *_: None
    cap._gst = "gst-launch-1.0"
    cap._proc = None
    cap._stderr = None
    cap._shm_fd = None
    cap._frame_offset = 0
    cap._punch_failed = False
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


def test_the_newest_frame_queue_sits_ahead_of_the_expensive_pair():
    """Where the drop happens is the cost.

    Downstream of videoconvert/videoscale, the chain converts and scales every frame the
    compositor produces and only then discards it: r2026-11-08-1080p-window-b spent 8.52 s
    of CPU across a 9.50 s window to present 120 frames, 90% of one core, busy while the
    worker wanted the CPU for its own frame. Ahead of the pair the queue holds raw PipeWire
    buffers and the expensive elements see only the frames the pipe actually takes.

    The caps are identical either way, so this cannot be caught by comparing output - it is
    purely an ordering assertion, which is why it is asserted on the argument list.
    """
    args = _capture()._pipeline_args()
    assert args.count("queue") == 1, "one queue, so what it holds is unambiguous"
    drop = args.index("leaky=downstream")
    assert drop < args.index("videoconvert"), "the queue must come before videoconvert"
    assert drop < args.index("videoscale"), "the queue must come before videoscale"
    assert drop < args.index("fdsink")
    # The sink is still the last word, and the caps still ride between the scale and it.
    assert args[-2:] == ["fdsink", "fd=1"]
    caps_i = next(i for i, a in enumerate(args) if a.startswith("video/x-raw"))
    assert args.index("videoscale") < caps_i < args.index("fdsink")


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


def test_videoscale_is_in_the_pipeline_by_default():
    """It is deliberate: the portal's size and the stream's can disagree."""
    args = _capture()._pipeline_args()
    assert "videoscale" in args
    assert args.index("videoscale") > args.index("videoconvert")


def test_videoscale_can_be_dropped():
    """--capture-no-scale removes one 14.7MB pass from a 33%-of-a-core chain.

    The chain measured 33% of a core at 2560x1440 — about 42ms of CPU per frame
    — which is the same order as the penalty the worker's `send` pays when the
    source is the portal rather than a synthetic card. This is the one element
    of it we can delete without changing anything else.
    """
    cap = _capture()
    cap.video_scale = False
    args = cap._pipeline_args()
    assert "videoscale" not in args
    # Everything else must be untouched: the conversion, the caps and the
    # newest-frame queue are not optional.
    assert "videoconvert" in args
    assert "fdsink" in args
    assert any("format=RGBA" in a for a in args)
    assert "leaky=downstream" in args


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

class _SizedSession:
    """A portal stream that reports the size the compositor gave it (or 0x0)."""

    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        # _pipeline_args() reads both; the pipeline itself is never started in these tests
        # (_start_pipeline is stubbed), so the fd only has to exist.
        self.fd = -1
        self.pipewire_target = ["path=/x"]
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _stub_portal(monkeypatch, session):
    from minimal.portal import SOURCE_WINDOW  # noqa: F401  (imported for the tests below)
    monkeypatch.setattr(cw, "requirements", lambda: (True, ""))
    monkeypatch.setattr(cw, "open_screencast", lambda **kw: session)
    monkeypatch.setattr(cw.PortalCapture, "_start_pipeline", lambda self: None)


def test_a_window_stream_reporting_no_size_takes_the_requested_one(monkeypatch):
    """KDE reports 0x0 for a window, and that is not a refusal.

    The size for a window is negotiated later, over PipeWire; the portal reports one for a
    screen. Our gst pipeline has to name the dimensions it scales to, so the request fills
    the gap — measured on the box as `stream node=259 serial=None 0x0` followed by "the
    portal did not report a stream size", which pointed at the portal rather than at us.
    """
    from minimal.portal import SOURCE_WINDOW

    session = _SizedSession(0, 0)
    _stub_portal(monkeypatch, session)
    logged: list[str] = []
    cap = cw.PortalCapture(source=SOURCE_WINDOW, width=2560, height=1440,
                           log=logged.append)
    assert (cap.width, cap.height) == (2560, 1440)
    assert any("no size" in line for line in logged), (
        "it has to say where the size came from, not use it quietly")


def test_a_stream_reporting_no_size_and_no_request_names_the_flag(monkeypatch):
    """Refusing is still right when nobody named a size — but the message has to be usable."""
    from minimal.portal import SOURCE_WINDOW

    session = _SizedSession(0, 0)
    _stub_portal(monkeypatch, session)
    with pytest.raises(CaptureError, match="--size"):
        cw.PortalCapture(source=SOURCE_WINDOW)
    assert session.closed, "a session it cannot use should be closed, not left open"


def test_a_named_size_wins_over_the_reported_one(monkeypatch):
    """--size is the run's frame size, not a hint: the pipeline scales to it.

    This is the lever, so it is worth a test rather than a note. The pass costs the square of
    the resolution, so running it internally at 1080p on a 1440p screen and letting the present
    stretch the result back up is ~7 ms a frame (19.5 ms / 51 fps against 26.4 / 38, both with
    the pixel channel over shared memory). It only works if the frame the pass sees is 1080p,
    which means the portal's reported 2560x1440 has to lose to the request — videoscale is
    already in the chain, so nothing new pays for the resize. The reverse was the old rule and
    it made NEURALSCREEN_SIZE=1920x1080 a no-op on a screen source (and on any compositor that
    reports a window's size), which read as the lever not working rather than as a precedence
    bug.
    """
    session = _SizedSession(2560, 1440)
    _stub_portal(monkeypatch, session)
    logged: list[str] = []
    cap = cw.PortalCapture(width=1920, height=1080, log=logged.append)
    assert (cap.width, cap.height) == (1920, 1080), (
        "the pass's resolution is what the run asked for")
    caps = [a for a in cap._pipeline_args() if a.startswith("video/x-raw")]
    assert "width=1920" in caps[0] and "height=1080" in caps[0], (
        "the pipeline has to be told which size to scale to, or the frame arrives at 1440p")
    assert any("scales to it" in line for line in logged), (
        "a frame that is not the size the compositor reported is worth saying out loud")


def test_the_reported_size_is_the_default_when_nothing_is_named(monkeypatch):
    """A screen reports its own size; with no request there is nothing to prefer over it."""
    session = _SizedSession(1280, 720)
    _stub_portal(monkeypatch, session)
    cap = cw.PortalCapture()
    assert (cap.width, cap.height) == (1280, 720)


# --- the frame transport ---------------------------------------------------

def test_the_pipe_is_the_default_transport():
    """Every number in the plan was measured on this route, so it stays the default."""
    args = _capture()._pipeline_args()
    assert args[-2:] == ["fdsink", "fd=1"]
    assert "shmsink" not in args


def test_the_shared_memory_transport_writes_into_the_memfd_not_the_pipe():
    """The chain changes only its end: one sink swapped for another, same caps, same queue.

    At 1080p the pipe moved 8.3 MB a frame for 5.1 ms of a 30.5 ms frame (1.6 GB/s, pipe speed)
    and it has been at /proc/sys/fs/pipe-max-size since the capture leg was priced, so the sink
    is the only thing on this leg with headroom left. Asserted on the argument list, because the
    difference is not visible in any frame - the two routes produce identical pixels.
    """
    cap = _capture(transport=cw.SHM)
    cap._shm_fd = 7                 # the builder only formats the number; nothing here uses it
    args = cap._pipeline_args()
    assert args[-3:] == ["fdsink", "fd=7", "sync=false"]
    assert "fd=1" not in args
    assert "shmsink" not in args, (
        "shmsink hands the segment over its own socket protocol, which a Python client would "
        "have to reimplement; the memfd is the route that can be read from here")
    # One variable apart, so a run of each is comparable: everything upstream is identical.
    # The PipeWire fd and the frame fds are the two numbers that legitimately differ.
    def _without_fds(rest):
        return [a for a in rest if not a.startswith("fd=")]

    assert _without_fds(args[:-3]) == _without_fds(_capture()._pipeline_args()[:-2])


def test_a_shared_memory_pipeline_without_a_memfd_refuses_to_be_built():
    """A missing memfd must not silently leave `fdsink fd=1` in an shm run's argument list."""
    cap = _capture(transport=cw.SHM)
    with pytest.raises(CaptureError, match="memfd"):
        cap._pipeline_args()


def test_an_unknown_transport_is_refused_by_name():
    """--capture-transport dma-buf must be a refusal, not a run on the default."""
    with pytest.raises(CaptureError, match="capture transport"):
        cw.PortalCapture(transport="dma-buf")


def test_a_shared_memory_frame_is_read_at_the_writers_offsets():
    """The chain writes sequentially, so frame N starts at N * frame_size - that is the framing.

    A pipe hands a reader a byte stream with no boundaries in it; a memory file the writer only
    ever appends to has them, as long as the reader keeps its own offset. This drives the read
    path against a real memfd written exactly the way fdsink writes one.
    """
    cap = _capture(width=4, height=4, transport=cw.SHM)      # a frame is 64 bytes
    cap._shm_fd = os.memfd_create("nsl-test", 0)
    first = bytes(range(64))
    second = bytes(range(64, 128))
    os.write(cap._shm_fd, first)
    os.write(cap._shm_fd, second)

    a = cap.grab()
    b = cap.grab()

    assert a.tobytes() == first and b.tobytes() == second, "each frame comes from its own offset"
    assert cap._frame_offset == 128, "the reader's offset is what marks the next frame"
    assert cap.last_wait is not None and cap.last_read is not None, (
        "the wait/read split the report prints has to exist on this route too")
    cap.close()
    assert cap._shm_fd is None


def test_a_shared_memory_frame_smaller_than_a_page_is_still_read():
    """The release is page-granular; a frame that cannot fill one must not be released away."""
    cap = _capture(width=2, height=2, transport=cw.SHM)      # 16 bytes
    cap._shm_fd = os.memfd_create("nsl-test", 0)
    payload = bytes(range(16))
    os.write(cap._shm_fd, payload)
    assert cap.grab().tobytes() == payload
    assert cap._punch_failed is False, "nothing to punch is not a punch that failed"
    cap.close()


def test_a_shared_memory_frame_that_never_arrives_says_so(tmp_path):
    """A chain that dies mid-run must not leave grab() waiting: the deadline ends it, with
    GStreamer's own words, the way the pipe route reports a truncated frame."""
    cap = _capture(width=4, height=4, transport=cw.SHM)
    cap.shm_timeout = 0.05
    cap._shm_fd = os.memfd_create("nsl-test", 0)
    err = tmp_path / "gst.log"
    err.write_text('WARNING: erroneous pipeline: no element "fdsink"\n')
    cap._stderr = err

    with pytest.raises(CaptureError) as exc:
        cap.grab()
    msg = str(exc.value)
    assert "no whole frame into shared memory" in msg
    assert "0 of 64 bytes" in msg
    assert "no element" in msg, "the pipeline's stderr must come through"
    cap.close()


class _FakeProc:
    def __init__(self):
        self.pid = 4242
        self.stdout = None          # the shm spawn sends stdout to /dev/null


def test_a_memfd_that_cannot_be_created_falls_back_to_the_pipe(monkeypatch):
    """One line, then the route that works - and never silently.

    A shared-memory chain that cannot start must not cost the run, but a fallback nobody is told
    about is worse than none: the frame times would be read as the new transport's.
    """
    cap = _capture(transport=cw.SHM)
    logged: list[str] = []
    cap._log = logged.append
    seen: list[list[str]] = []

    def _popen(args, **kw):
        seen.append(list(args))
        return _FakeProc()

    def _no_memfd(*_a, **_k):
        raise OSError(38, "Function not implemented")

    monkeypatch.setattr(cw.subprocess, "Popen", _popen)
    monkeypatch.setattr(cw.os, "memfd_create", _no_memfd)
    cap._start_pipeline()

    assert cap.transport == cw.PIPE
    assert seen[-1][-2:] == ["fdsink", "fd=1"]
    assert sum("falling back to the pipe" in line for line in logged) == 1, (
        "once, not once per attempt and not never")
    cap.close()


def test_a_shared_memory_chain_that_cannot_start_falls_back_to_the_pipe(monkeypatch):
    """Popen failing on the memfd route: the memfd is dropped and the pipe chain is started."""
    cap = _capture(transport=cw.SHM)
    logged: list[str] = []
    cap._log = logged.append
    seen: list[list[str]] = []

    def _popen(args, **kw):
        seen.append(list(args))
        if len(seen) == 1:
            raise OSError(13, "Permission denied")
        return _FakeProc()

    monkeypatch.setattr(cw.subprocess, "Popen", _popen)
    cap._start_pipeline()

    assert cap.transport == cw.PIPE
    assert seen[0][-1] == "sync=false", "the first attempt was the memfd chain"
    assert seen[-1][-2:] == ["fdsink", "fd=1"]
    assert cap._shm_fd is None, "the memfd of the chain that did not start is closed"
    assert any("falling back to the pipe" in line for line in logged)
    cap.close()


def test_a_shared_memory_run_says_which_transport_it_is_on(monkeypatch):
    """The report has to name the route, or a comparison of the two is guesswork."""
    cap = _capture(transport=cw.SHM)
    logged: list[str] = []
    cap._log = logged.append
    monkeypatch.setattr(cw.subprocess, "Popen", lambda args, **kw: _FakeProc())
    cap._start_pipeline()

    assert cap.transport == cw.SHM
    assert any("shared memory (memfd fd=" in line for line in logged)
    assert not any("pipe buffer" in line for line in logged), (
        "there is no pipe to size on this route")
    cap.close()
