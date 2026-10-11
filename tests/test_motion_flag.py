"""FRAME_FLAG_NO_MOTION: the frame is header and colour, and nothing else.

At 2560x1440 the motion field is 14.7MB of float16 — as much as the colour — and the MVP
sends a field of zeros. A worker that does not read it should not be sent it, and a stream
that carries the flag must also carry no bytes, or the sender and the receiver disagree
about where the next frame starts.
"""
import io
import struct

import numpy as np

from protocol import FRAME_FLAG_NO_MOTION, FRAME_FMT, send_frame

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


def test_no_motion_frame_is_header_and_colour_only():
    worker = FakeWorker()
    rgba = np.zeros((H, W, 4), np.uint8)
    motion = np.zeros((H, W, 2), np.float16)

    send_frame(worker, 1, rgba, motion, True, 0, no_motion=True)
    data = worker.stdin.getvalue()

    assert has_flag(frame_flags(data), FRAME_FLAG_NO_MOTION), "the flag is not set"
    assert len(data) == HEADER + W * H * 4, (
        f"a no-motion frame was {len(data)} bytes: the motion field went out anyway "
        f"(expected {HEADER + W * H * 4})")


def test_the_motion_field_still_goes_out_without_the_flag():
    """The flag is a choice, not a new default: the Wine worker needs the field."""
    worker = FakeWorker()
    rgba = np.zeros((H, W, 4), np.uint8)
    motion = np.zeros((H, W, 2), np.float16)

    send_frame(worker, 1, rgba, motion, True, 0)
    data = worker.stdin.getvalue()

    assert not has_flag(frame_flags(data), FRAME_FLAG_NO_MOTION)
    assert len(data) == HEADER + W * H * 4 + W * H * 4, len(data)


def test_the_two_forms_are_the_same_size_apart_from_the_motion_field():
    """Off by even one byte and every later frame in the stream is misaligned."""
    sizes = []
    for no_motion in (False, True):
        worker = FakeWorker()
        send_frame(worker, 1, np.zeros((H, W, 4), np.uint8), np.zeros((H, W, 2), np.float16),
                   True, 0, no_motion=no_motion)
        sizes.append(len(worker.stdin.getvalue()))
    assert sizes[0] - sizes[1] == W * H * 4, sizes
