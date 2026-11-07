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
