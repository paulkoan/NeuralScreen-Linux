"""A generated mid-frame is a second reply for the same index, and it must not be confused
with the frame the client asked for.

The client is strictly one-send-one-reply: `recv(index)` waits for that index and drops
anything else, so a second reply for the same index would either be read as the next frame's
result or silently dropped, and every frame after it would pair with the wrong picture. These
tests pin the routing: the mid-frame goes to its own map, the enhanced frame goes to the queue,
the presented order is mid-then-real, and a run that did not ask for one is untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from minimal.loop import Pipeline

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

MARKER = bytes([0xAB, 0xCD, 0xEF, 0x01])


def _pipeline(fake_capture, fake_display, mock_worker_cmd, **kw):
    return Pipeline(capture=fake_capture, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO, **kw)


def _starts_with_marker(frame: np.ndarray) -> bool:
    return bytes(frame[0, 0, :4]) == MARKER


def test_the_mid_frame_is_presented_before_its_own_frame(fake_capture, fake_display,
                                                         mock_worker_cmd):
    pipe = _pipeline(fake_capture, fake_display, mock_worker_cmd,
                     interpolate=True, interp_pace=0.0)
    summary = pipe.run(frames=4)
    shown = fake_display.frames
    assert len(shown) == 8, f"expected a mid and a real frame per iteration, got {len(shown)}"
    for pair in range(4):
        assert _starts_with_marker(shown[2 * pair]), (
            f"iteration {pair}: the mid-frame must go first, so it is seen between the "
            f"previous frame and this one")
        assert not _starts_with_marker(shown[2 * pair + 1]), (
            "the frame the client sent must come back unchanged")
    assert summary["interp_shown"] == 4
    assert summary["frames_done"] == 4, "a generated frame is not a computed one"


def test_the_window_path_presents_the_mid_too(fake_capture, fake_display, mock_worker_cmd):
    """`--send-ahead N` presents a mid-frame per frame, in the same order.

    The window path collected mid-frames into the map and presented none of them, because the
    presentation lived only in the serial loop: `--send-ahead 2 --interpolate` asked for every
    mid, paid for it, and showed nothing. A run like that is indistinguishable from the feature
    being off unless the presented count is read, and it is the path a throughput run uses.
    """
    pipe = _pipeline(fake_capture, fake_display, mock_worker_cmd,
                     interpolate=True, interp_pace=0.0, send_ahead=2)
    summary = pipe.run(frames=6)
    shown = fake_display.frames
    assert summary["frames_done"] == 6
    assert summary["interp_shown"] == 6, "every frame was answered with a mid-frame"
    assert len(shown) == 12, f"expected a mid and a real frame per frame, got {len(shown)}"
    for pair in range(6):
        assert _starts_with_marker(shown[2 * pair]), (
            f"iteration {pair}: the mid must still go first with two frames in flight")
        assert not _starts_with_marker(shown[2 * pair + 1])


def test_the_window_path_keeps_the_mid_for_saving(fake_capture, fake_display,
                                                  mock_worker_cmd, tmp_path):
    saved = tmp_path / "mid.png"
    pipe = _pipeline(fake_capture, fake_display, mock_worker_cmd,
                     interpolate=True, interp_pace=0.0, send_ahead=2)
    pipe.run(frames=4, save_mid=str(saved))
    assert pipe.last_mid is not None and bytes(pipe.last_mid[0, 0, :4]) == MARKER
    assert saved.exists()


def test_without_the_flag_nothing_changes(fake_capture, fake_display, mock_worker_cmd):
    """The default path must be byte-for-byte what it was: one present per frame."""
    pipe = _pipeline(fake_capture, fake_display, mock_worker_cmd)
    summary = pipe.run(frames=4)
    assert len(fake_display.frames) == 4
    assert not any(_starts_with_marker(f) for f in fake_display.frames)
    assert summary["interp_shown"] == 0


def test_the_mid_frame_costs_a_stage_of_its_own(fake_capture, fake_display, mock_worker_cmd):
    """The hold that makes it visible comes out of the frame's own time, so it is reported."""
    pipe = _pipeline(fake_capture, fake_display, mock_worker_cmd,
                     interpolate=True, interp_pace=0.002)
    summary = pipe.run(frames=3)
    timing = summary["timing"]
    assert "interp" in timing and len(pipe.timings["interp"]) == 3
    assert timing["interp"] >= 0.002, timing["interp"]
    assert timing["total"] > timing["capture"] + timing["send"] + timing["recv"]


def test_a_worker_that_ignores_the_flag_is_not_a_stall(fake_capture, fake_display,
                                                       mock_worker_cmd):
    """The port may not know the flag yet; that must read as "no mid-frame", not as a hang."""
    pipe = _pipeline(fake_capture, fake_display, mock_worker_cmd,
                     interpolate=True, interp_pace=0.0)
    pipe.worker.want_interp = False          # as a worker without the feature would behave
    summary = pipe.run(frames=3)
    assert summary["frames_done"] == 3
    assert summary["interp_shown"] == 0
    assert len(fake_display.frames) == 3


def test_the_flag_reaches_the_wire():
    """Both sides of the handshake: the request bit and the reply bit are different bits."""
    import protocol
    assert protocol.FRAME_FLAG_WANT_INTERP != 0
    assert protocol.OUT_FLAG_INTERPOLATED != 0
    assert not (protocol.FRAME_FLAG_WANT_INTERP & protocol.OUT_FLAG_INTERPOLATED)
    for name in ("FRAME_FLAG_SHM", "FRAME_FLAG_WANT_PIXELS", "FRAME_FLAG_MOTION_SMALL",
                 "FRAME_FLAG_NO_COLOR", "FRAME_FLAG_BYPASS", "FRAME_FLAG_NO_MOTION",
                 "FRAME_FLAG_SPLIT", "FRAME_FLAG_COLOR_BGRA"):
        assert not (protocol.FRAME_FLAG_WANT_INTERP & getattr(protocol, name)), name
    # And the reply bit must not collide with the NGX failure family it shares a field with.
    assert not (protocol.OUT_FLAG_INTERPOLATED & 0xB0000000)


def test_the_mid_frame_has_a_slot_of_its_own():
    """Two pixel slots, not one.

    The worker generates a mid-frame and then the real one, in that order, in one iteration.
    With a single slot the second write can land before this side has copied the first: the
    seqlock makes that a lost mid-frame rather than a corrupt one, but the presented rate
    would fall with nothing in either log to say why - so the mid-frame gets its own section,
    named after the pixel channel's with an `m` on the end, and the reply's flag says which
    of the two the worker just wrote.
    """
    import os
    import protocol

    shm = protocol.SharedFrameBuffer(16, 16, 16, 16)
    shm.open_out(16, 16)
    mid_name = shm.out_mid_name
    assert mid_name == shm.out_name + "m", "the worker finds the second slot by that name"
    assert shm.has_out() and shm.has_out(mid=True)

    real = np.full((16, 16, 4), 11, np.uint8)
    mid = np.full((16, 16, 4), 222, np.uint8)
    shm._out_buf[:] = real          # the worker's publication, seqlock left even
    shm._out_mid_buf[:] = mid
    assert shm.read_out().tolist() == real.tolist()
    assert shm.read_out(mid=True).tolist() == mid.tolist(), (
        "the mid-frame slot must hold its own frame, not the pixel channel's")

    shm.close_out()
    assert not shm.has_out() and not shm.has_out(mid=True)
    if os.name != "nt":
        assert not os.path.exists(f"/dev/shm/{mid_name}"), "the mid-frame's name is dropped"
    shm.close()


def test_a_mid_reply_copies_from_the_mid_slot():
    """The reply's flag decides which section is copied.

    Reading the pixel channel for a mid reply would present the previous frame twice, which
    looks like interpolation and is not - so this pins the routing at the reader, where the
    two replies for one index are told apart.
    """
    import os
    import struct
    import types
    import protocol

    shm = protocol.SharedFrameBuffer(8, 8, 8, 8)
    shm.open_out(8, 8)
    real = np.full((8, 8, 4), 11, np.uint8)
    mid = np.full((8, 8, 4), 222, np.uint8)
    shm._out_buf[:] = real
    shm._out_mid_buf[:] = mid

    read_fd, write_fd = os.pipe()
    worker = types.SimpleNamespace(stdout=os.fdopen(read_fd, "rb"))
    reader = protocol.WorkerReader(worker, 8, 8, shm)
    head = struct.pack(protocol.OUT_FMT, protocol.OUT_MAGIC, 7, 1,
                       protocol.OUT_BYTES_IN_SHM, protocol.OUT_FLAG_INTERPOLATED, 0)
    body = struct.pack(protocol.OUT_FMT, protocol.OUT_MAGIC, 7, 1,
                       protocol.OUT_BYTES_IN_SHM, 0, 0)
    os.write(write_fd, head + body)     # mid first, then the frame it belongs to
    os.close(write_fd)

    index, payload = reader._queue.get(timeout=5)
    assert index == 7 and payload.tolist() == real.tolist()
    assert reader.take_interp(7).tolist() == mid.tolist()
    assert reader.interp_frames == 1
    assert reader.take_interp(7) is None, "a mid-frame is shown once"
    worker.stdout.close()
    shm.close_out()
    shm.close()
