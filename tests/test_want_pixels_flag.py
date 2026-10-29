"""FRAME_FLAG_WANT_PIXELS: ask for the pixels, or do not pay for them.

A reply carrying pixels costs the worker a full-resolution readback plus a full-resolution
write - 14.7MB each at 1440p, measured at 12.8ms of a 37ms frame. The wire has had the flag
for a while; what it did not have was a sender that ever set it, so every headless benchmark
paid for a channel it threw away. These tests pin both halves: the flag rides the header when
it is asked for, and it is absent when it is not.
"""
import io
import struct

import numpy as np

from protocol import FRAME_FLAG_WANT_PIXELS, FRAME_FMT, send_frame

W = H = 32
HEADER = struct.calcsize(FRAME_FMT)


class FakeWorker:
    """Only what send_frame touches: a stdin with the Popen surface it uses."""

    def __init__(self):
        self.stdin = io.BytesIO()


def frame_flags(data: bytes) -> int:
    return struct.unpack(FRAME_FMT, data[:HEADER])[3]


def has_flag(flags: int, flag: int) -> bool:
    """One bit of the reserved field."""
    return bool((flags // flag) % 2)


def test_want_pixels_sets_the_flag():
    worker = FakeWorker()
    send_frame(worker, 1, np.zeros((H, W, 4), np.uint8), np.zeros((H, W, 2), np.float16),
               True, 0, want_pixels=True)
    assert has_flag(frame_flags(worker.stdin.getvalue()), FRAME_FLAG_WANT_PIXELS)


def test_no_want_pixels_leaves_the_flag_clear():
    """The default is off on the wire even though Worker.send defaults it on for display
    callers: a sender that says nothing must not silently opt into the expensive channel."""
    worker = FakeWorker()
    send_frame(worker, 1, np.zeros((H, W, 4), np.uint8), np.zeros((H, W, 2), np.float16),
               True, 0)
    assert not has_flag(frame_flags(worker.stdin.getvalue()), FRAME_FLAG_WANT_PIXELS)


def test_the_flag_does_not_move_the_frame_bytes():
    """Asking for pixels changes the header only: the colour still starts where it did."""
    plain = FakeWorker()
    asked = FakeWorker()
    rgba = np.arange(W * H * 4, dtype=np.uint8).reshape(H, W, 4)
    motion = np.zeros((H, W, 2), np.float16)
    send_frame(plain, 7, rgba, motion, False, 0)
    send_frame(asked, 7, rgba, motion, False, 0, want_pixels=True)
    assert plain.stdin.getvalue()[HEADER:] == asked.stdin.getvalue()[HEADER:]