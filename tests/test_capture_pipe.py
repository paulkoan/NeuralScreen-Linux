"""The frame pipe's buffer is a capture knob, not a detail.

At 2560x1440 one RGBA frame is 14.7 MB. The kernel's default pipe hands it over 64 KiB at a
time, so the producer and the consumer alternate 230 times a frame and the whole capture leg
runs at ~1.3 GB/s. Measured here, same drain loop: 12.70 ms/frame at the 64 KiB default,
8.90 ms at 1 MiB. `_enlarge_pipe` asks for 1 MiB (/proc/sys/fs/pipe-max-size on stock Linux)
and takes whatever it is granted - and a refusal must not break the capture, because a capture
at the old speed still works.
"""
import fcntl
import os
from types import SimpleNamespace

import numpy as np

from minimal.capture import CaptureError
from minimal.capture_wayland import PIPE_BYTES, PortalCapture


class _FakeCapture:
    """Enough of a capture for _enlarge_pipe: a pipe to ask about and a log to write to."""

    def __init__(self, stdout=None):
        self._proc = SimpleNamespace(stdout=stdout) if stdout is not None else None
        self.log: list[str] = []

    def _log(self, message):
        self.log.append(message)


def _pipe_pair():
    """A pipe whose read end is a buffered file, as subprocess.PIPE produces."""
    read_fd, write_fd = os.pipe()
    return os.fdopen(read_fd, "rb", -1), write_fd


def test_the_pipe_is_enlarged_and_the_grant_is_recorded():
    stream, write_fd = _pipe_pair()
    try:
        capture = _FakeCapture(stream)
        PortalCapture._enlarge_pipe(capture)
    finally:
        os.close(write_fd)
    granted = fcntl.fcntl(stream.fileno(), fcntl.F_GETPIPE_SZ)
    assert capture.pipe_bytes == granted, "the log has to record what the kernel granted"
    assert granted >= 65536
    assert capture.log, "a silent resize is indistinguishable from a failed one"
    assert "pipe buffer" in capture.log[-1]


def test_a_refused_resize_leaves_the_capture_alone():
    """F_SETPIPE_SZ can be refused, and a refusal is not a failure."""
    capture = _FakeCapture(SimpleNamespace(fileno=lambda: -1))
    PortalCapture._enlarge_pipe(capture)          # must not raise
    assert not getattr(capture, "pipe_bytes", 0), "nothing was granted, so nothing is claimed"
    assert capture.log and "unchanged" in capture.log[-1]


def test_no_pipeline_yet_is_not_an_error():
    PortalCapture._enlarge_pipe(_FakeCapture(None))


def test_the_report_names_the_buffer_the_number_was_measured_against():
    """`read` means different things at different buffer sizes, so the buffer ships with it."""
    from minimal.loop import Pipeline

    class Fake:
        timings = {"send": [0.001] * 5, "recv": [0.002] * 5}
        capture_split = {"wait": [0.0003] * 5, "read": [0.0131] * 5}
        capture = SimpleNamespace(pipe_bytes=PIPE_BYTES)

    out = Pipeline.timing_summary(Fake())
    assert out["capture_pipe_bytes"] == PIPE_BYTES
    assert out["capture_read"] == 0.0131


def test_a_capture_with_no_pipe_reports_nothing_extra():
    from minimal.loop import Pipeline

    class Fake:
        timings = {"send": [0.001] * 5, "recv": [0.002] * 5}
        capture_split = {"wait": [0.0003] * 5, "read": [0.0131] * 5}

    out = Pipeline.timing_summary(Fake())
    assert "capture_pipe_bytes" not in out


def test_the_resize_does_not_touch_the_bytes():
    """A buffer size is a transport setting; the frame it carries is unchanged."""
    frame = np.arange(64 * 48 * 4, dtype=np.uint8).reshape(48, 64, 4)
    for want in (PIPE_BYTES, 65536):
        stream, write_fd = _pipe_pair()
        try:
            capture = _FakeCapture(stream)
            PortalCapture._enlarge_pipe(capture)
            os.write(write_fd, frame.tobytes())
            got = stream.read(frame.nbytes)
        finally:
            os.close(write_fd)
            stream.close()
        assert np.frombuffer(got, dtype=np.uint8).reshape(48, 64, 4).tolist() == frame.tolist()

class _FakePipeCapture(PortalCapture):
    """A capture whose only real part is the pipeline's stdout.

    Subclasses the real thing so grab() and _read_frame() are the production code, with
    __init__ replaced to skip the portal handshake.
    """

    def __init__(self, stream, width=8, height=6):
        self.width, self.height = width, height
        self._proc = SimpleNamespace(stdout=stream)
        self._stderr = None
        self.last_wait = None

    def _log(self, message):
        pass


def test_a_frame_is_read_straight_into_its_own_buffer():
    """One copy, not two: the array the caller keeps is the array the pipe filled."""
    width, height = 64, 48
    frame = np.arange(height * width * 4, dtype=np.uint8).reshape(height, width, 4)
    stream, write_fd = _pipe_pair()
    try:
        capture = _FakePipeCapture(stream, width, height)
        os.write(write_fd, frame.tobytes())
        got = PortalCapture._read_frame(capture, frame.nbytes)
    finally:
        os.close(write_fd)
        stream.close()
    assert got.shape == (height, width, 4) and got.dtype == np.uint8
    assert got.tolist() == frame.tolist()
    assert capture.last_wait is not None, "the first byte's arrival is still timed"


def test_the_grab_reports_wait_and_read_separately():
    """The split is the whole point of the loop and must survive readinto1."""
    width, height = 64, 48
    frame = np.zeros((height, width, 4), dtype=np.uint8)
    stream, write_fd = _pipe_pair()
    try:
        capture = _FakePipeCapture(stream, width, height)
        os.write(write_fd, frame.tobytes())
        got = PortalCapture.grab(capture)
    finally:
        os.close(write_fd)
        stream.close()
    assert got.shape == (height, width, 4)
    assert capture.last_wait is not None and capture.last_read is not None
    assert capture.last_wait >= 0 and capture.last_read >= 0


def test_a_pipeline_that_ends_mid_frame_says_how_far_it_got():
    width, height = 64, 48
    stream, write_fd = _pipe_pair()
    try:
        capture = _FakePipeCapture(stream, width, height)
        os.write(write_fd, b"\x00" * 100)
        os.close(write_fd)                     # EOF part-way through the frame
        write_fd = None
        try:
            PortalCapture._read_frame(capture, width * height * 4)
        except CaptureError as exc:
            assert "100 of" in str(exc), f"the error must name the shortfall: {exc}"
        else:
            raise AssertionError("a short frame must not be returned as a frame")
    finally:
        stream.close()
        if write_fd is not None:
            os.close(write_fd)


def test_the_read_does_not_need_readinto1():
    """BufferedReader has readinto1; anything else must still work (read + copy)."""
    width, height = 32, 24
    frame = np.arange(height * width * 4, dtype=np.uint8).reshape(height, width, 4)
    read_fd, write_fd = os.pipe()
    try:
        stream = os.fdopen(read_fd, "rb", 0)          # unbuffered: no readinto1
        assert not hasattr(stream, "readinto1")
        capture = _FakePipeCapture(stream, width, height)
        os.write(write_fd, frame.tobytes())
        got = PortalCapture._read_frame(capture, frame.nbytes)
    finally:
        os.close(write_fd)
        stream.close()
    assert got.tolist() == frame.tolist()
