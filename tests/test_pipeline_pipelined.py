"""The pipelined loop: several frames in flight instead of one.

The serial loop is covered by the existing mock tests. What is new here is that
replies have to pair with sends when more than one frame is outstanding:

  * the worker answers in order, so a reply belongs to the oldest send — and the
    code has to check that rather than assume it;
  * a saved before/after pair still has to come from ONE iteration, which is
    harder when the input of the frame being answered is no longer the input
    most recently captured;
  * a stall has to stop the run and name itself, not hang, and not quietly pair
    the wrong frames.

The last two are tested with a stub worker because they are failure paths: a
fixture that produces them is not a fixture that behaves like the real worker.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from minimal.loop import Pipeline  # noqa: E402
from tests.mock_worker import _transform  # noqa: E402

W, H = 8, 4


class IndexedCapture:
    """Every frame it hands out is identifiable by its own index.

    `grab` fills the frame with the call number, so which capture produced any
    given array is recoverable afterwards — which is what makes it possible to
    tell a matched pair from a straddling one.
    """

    def __init__(self, w: int = W, h: int = H):
        self.resolution = (w, h)
        self.width, self.height = w, h
        self.n = 0

    def grab(self) -> np.ndarray:
        frame = np.full((self.height, self.width, 4), self.n % 251, dtype=np.uint8)
        self.n += 1
        return frame

    def close(self) -> None:
        pass


class StubWorker:
    """Just enough of Worker for the pipelined loop's failure paths."""

    def __init__(self, replies=None, stall_after: int | None = None):
        self.logs: list[str] = []
        self.proc = None
        self.sent: list[int] = []
        self._replies = list(replies or [])
        self._stall_after = stall_after
        self._taken = 0

    def start(self) -> None:
        pass

    def is_alive(self) -> bool:
        return True

    def send(self, index, rgba, motion, reset, pts=0) -> None:
        self.sent.append(index)

    def recv_any(self, timeout=None):
        if self._stall_after is not None and self._taken >= self._stall_after:
            raise TimeoutError("stub: no reply")
        if not self._replies:
            raise TimeoutError("stub: no replies left")
        self._taken += 1
        return self._replies.pop(0)

    def stop(self, timeout=None):
        return 0


def make_pipeline(capture, display, **kw) -> Pipeline:
    return Pipeline(capture=capture, display=display, headless=True, **kw)


def test_removing_the_per_frame_copy_does_not_change_a_byte():
    """send_frame used to write rgba.tobytes() — a fresh 14.7MB allocation and copy
    per frame at 1440p, and another for the motion field — and now writes the
    array's own buffer. A single differing byte would be silently misparsed
    pixels on the worker's side, so this pins the wire format."""
    import io
    import struct

    from protocol import FRAME_FMT, FRAME_MAGIC, send_frame

    class Sink:
        def __init__(self, buf):
            self.stdin = buf

    rgba = np.arange(W * H * 4, dtype=np.uint8).reshape(H, W, 4)
    motion = np.arange(W * H * 2, dtype=np.float16).reshape(H, W, 2)
    buf = io.BytesIO()
    send_frame(Sink(buf), 3, rgba, motion, reset=False, pts=3)
    got = buf.getvalue()

    header = struct.calcsize(FRAME_FMT)
    assert got[:header] == struct.pack(FRAME_FMT, FRAME_MAGIC, 3, 0, 0, 3)
    assert got[header:] == rgba.tobytes() + motion.tobytes(), (
        "the frame written to the pipe changed — this is the worker's input")


def test_the_pipelined_loop_finishes_every_frame(fake_display, mock_worker_cmd):
    """With four frames in flight, every frame still gets sent and answered."""
    capture = IndexedCapture()
    pipe = make_pipeline(capture, fake_display, send_ahead=4,
                         worker_cmd=mock_worker_cmd, worker_cwd=REPO)
    summary = pipe.run(frames=8)

    assert summary["send_ahead"] == 4
    assert summary["frames_attempted"] == 8
    assert summary["frames_done"] == 8, summary
    assert summary["frames_skipped"] == 0
    assert summary["stalls"] == 0
    assert summary["fps"] > 0


def test_the_pipelined_loop_still_keeps_a_matched_pair(fake_display, mock_worker_cmd,
                                                       tmp_path):
    """The pair must be one iteration's input and output.

    With frames in flight, the input of the frame being answered is no longer the
    input most recently captured — so this is exactly where a pair could start
    straddling two frames, which is the bug that once inflated a diff from
    15.8/255 to 48.7/255.
    """
    capture = IndexedCapture()
    after_png = tmp_path / "after.png"
    pipe = make_pipeline(capture, fake_display, send_ahead=4,
                         worker_cmd=mock_worker_cmd, worker_cwd=REPO)
    summary = pipe.run(frames=8, save_after=str(after_png))

    before, after = summary["before"], summary["after"]
    assert before is not None and after is not None
    # The output is the mock's transform of ITS OWN input, and nothing else.
    assert np.array_equal(after, np.frombuffer(
        _transform(before.tobytes()), dtype=np.uint8).reshape(before.shape)), (
        "the saved pair straddles two frames")
    # And the pair belongs to the last frame consumed, which is the last one sent.
    assert int(before[0, 0, 0]) == (8 - 1) % 251, (
        f"the pair's input is frame {int(before[0, 0, 0])}, not the last one")


def test_a_reply_for_the_wrong_frame_stops_the_run(fake_display):
    """The pairing is checked, not assumed.

    If the worker ever answers out of order — or a stall leaves a reply in the
    queue — every reply after that belongs to a different frame than the caller
    thinks, and a run that continued would report one frame's result against
    another frame's input as if it were a measurement.
    """
    capture = IndexedCapture()
    worker = StubWorker(replies=[(7, np.zeros((H, W, 4), np.uint8))])
    pipe = make_pipeline(capture, fake_display, send_ahead=2)
    pipe.worker = worker

    with pytest.raises(RuntimeError) as exc:
        pipe.run(frames=4)
    assert "answered frame 7" in str(exc.value)
    assert "pairing" in str(exc.value)


def test_a_stall_is_counted_and_named_not_hung(fake_display):
    """Round 29 caught the worker going silent for eighteen seconds mid-run.

    The loop has to stop and say so: not wait forever, and not carry on pairing
    replies that cannot be attributed.
    """
    capture = IndexedCapture()
    worker = StubWorker(replies=[(0, np.zeros((H, W, 4), np.uint8))],
                        stall_after=1)
    pipe = make_pipeline(capture, fake_display, send_ahead=2, frame_timeout=0.1)
    pipe.worker = worker

    with pytest.raises(RuntimeError) as exc:
        pipe.run(frames=6)
    message = str(exc.value)
    assert "stalled" in message
    assert "frame 1" in message, message
    assert pipe.stalls == 1, "the stall has to be counted, not just raised"


def test_the_serial_loop_is_the_default_and_unchanged(fake_display):
    """send_ahead=1 must keep the loop the MVP has always run."""
    capture = IndexedCapture()
    pipe = make_pipeline(capture, fake_display)
    assert pipe.send_ahead == 1
    assert pipe.stalls == 0


@pytest.mark.parametrize("value,expected", [(1, 1), (4, 4), (0, 1), (-3, 1)])
def test_send_ahead_is_clamped_to_at_least_one(value, expected, fake_display):
    """Zero or negative would mean no window at all, which is not a pipeline."""
    pipe = make_pipeline(IndexedCapture(), fake_display, send_ahead=value)
    assert pipe.send_ahead == expected