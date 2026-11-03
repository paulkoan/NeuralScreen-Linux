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