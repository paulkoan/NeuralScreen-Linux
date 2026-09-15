"""M1 — the pipeline works end to end against the mock worker.

No GPU, no Wine: the mock in tests/mock_worker.py speaks the real binary
protocol and applies a known transform, so these tests prove the whole Python
side (capture -> send -> receive -> display) before a real worker is involved.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from minimal.loop import DEFAULT_PARAMS, Pipeline
from minimal.worker import Worker, work_size

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


# --- work-size rules ------------------------------------------------------

@pytest.mark.parametrize("w,h,expect_w,expect_h", [
    (1920, 1080, 1920, 1080),   # at or under the ceiling: unchanged
    (2560, 1440, 2560, 1440),   # exactly the ceiling
    (3840, 2160, 2560, 1440),   # 4K scales down to the ceiling
    (100, 100, 100, 100),       # small frames pass through
    (101, 101, 100, 100),       # odd sizes round down to even
])
def test_work_size(w, h, expect_w, expect_h):
    assert work_size(w, h) == (expect_w, expect_h)


def test_work_size_never_exceeds_the_source():
    """The work resolution must never be larger than the frame it came from."""
    for w, h in [(640, 480), (1920, 1080), (1000, 700)]:
        ww, wh = work_size(w, h)
        assert ww <= w and wh <= h


# --- the worker wrapper ---------------------------------------------------

def test_worker_starts_and_sends_its_header(mock_worker_cmd):
    w = Worker(320, 180, 320, 180, DEFAULT_PARAMS, warmup=2, cmd=mock_worker_cmd)
    w.start()
    try:
        assert w.wait_for_alive(3.0), (
            "the mock worker exited immediately:\n  " + "\n  ".join(w.logs))
    finally:
        code = w.stop()
    assert code == 0, f"the worker exited {code}; logs:\n  " + "\n  ".join(w.logs)


def test_one_frame_round_trip(mock_worker_cmd):
    """One frame in, one processed frame out, of the same size."""
    w = Worker(320, 180, 320, 180, DEFAULT_PARAMS, cmd=mock_worker_cmd)
    w.start()
    try:
        frame = np.full((180, 320, 4), 40, dtype=np.uint8)
        frame[..., 3] = 255
        motion = np.zeros((180, 320, 2), dtype=np.float16)
        w.send(0, frame, motion, reset=True, pts=0)
        out = w.recv(0, timeout=10.0)
    finally:
        w.stop()

    assert out is not None, "the worker returned no pixels"
    assert out.shape == (180, 320, 4)
    assert out.dtype == np.uint8
    # The mock reverses R and B and adds 8: both are observable.
    assert out[0, 0, 0] == 40 + 8, f"R was not the reversed B: {out[0, 0]}"
    assert out[0, 0, 2] == 40 + 8
    assert not np.array_equal(out, frame), "the result is identical to the input"


def test_frame_indices_are_paired(mock_worker_cmd):
    """Sending N frames returns N results, in order."""
    w = Worker(160, 96, 160, 96, DEFAULT_PARAMS, cmd=mock_worker_cmd)
    w.start()
    try:
        motion = np.zeros((96, 160, 2), dtype=np.float16)
        for i in range(4):
            frame = np.full((96, 160, 4), 20 + i, dtype=np.uint8)
            frame[..., 3] = 255
            w.send(i, frame, motion, reset=(i == 0), pts=i)
            out = w.recv(i, timeout=10.0)
            assert out is not None, f"frame {i} returned nothing"
            assert out[0, 0, 0] == 20 + i + 8, f"wrong frame came back for index {i}"
    finally:
        w.stop()


def test_stop_terminates_the_worker(mock_worker_cmd):
    w = Worker(160, 96, 160, 96, DEFAULT_PARAMS, cmd=mock_worker_cmd)
    w.start()
    assert w.wait_for_alive(2.0)
    code = w.stop()
    assert code == 0
    assert not w.is_alive()


# --- the full pipeline, mocked -------------------------------------------

def test_pipeline_runs_n_frames(fake_capture, fake_display, mock_worker_cmd):
    pipe = Pipeline(capture=fake_capture, display=fake_display,
                    headless=True, worker_cmd=mock_worker_cmd,
                    worker_cwd=REPO)
    summary = pipe.run(frames=3)

    assert summary["frames_attempted"] == 3
    assert summary["frames_done"] == 3, (
        f"{summary['frames_skipped']} frames were skipped")
    assert summary["worker_exit"] == 0
    assert len(fake_display.frames) == 3
    assert fake_capture.closed and fake_display.closed


def test_pipeline_frames_differ_frame_to_frame(fake_capture, fake_display,
                                               mock_worker_cmd):
    """The output must track the input — a frozen frame would not."""
    pipe = Pipeline(capture=fake_capture, display=fake_display,
                    headless=True, worker_cmd=mock_worker_cmd,
                    worker_cwd=REPO)
    summary = pipe.run(frames=3)

    frames = summary["after"], fake_display.frames
    shown = fake_display.frames
    assert len(shown) == 3
    assert not np.array_equal(shown[0], shown[1]), "consecutive frames are identical"
    assert shown[0].shape == shown[1].shape == (180, 320, 4)
    assert frames[0].shape == shown[2].shape


def test_pipeline_reports_worker_death(fake_capture, fake_display):
    """A worker that dies mid-run must be reported, not silently looped."""
    cmd = [sys.executable, str(REPO / "tests" / "mock_worker.py"), "--fail", "2"]
    pipe = Pipeline(capture=fake_capture, display=fake_display,
                    headless=True, worker_cmd=cmd, worker_cwd=REPO)
    with pytest.raises(RuntimeError, match="worker died"):
        pipe.run(frames=6)


def test_pipeline_quits_on_display_event(fake_capture, mock_worker_cmd):
    """A quit event from the display stops the loop."""
    from tests.conftest import FakeDisplay
    display = FakeDisplay()
    display.quit_after = 2
    pipe = Pipeline(capture=fake_capture, display=display,
                    headless=True, worker_cmd=mock_worker_cmd,
                    worker_cwd=REPO)
    summary = pipe.run(frames=0)
    assert summary["frames_done"] == 2, "the quit event did not stop the loop"