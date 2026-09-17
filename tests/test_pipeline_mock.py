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
from minimal.worker import FLOW_H, FLOW_W, Worker, work_size

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


# --- work-size rules ------------------------------------------------------

@pytest.mark.parametrize("w,h,expect_w,expect_h", [
    (1920, 1080, 1920, 1080),   # at or under the ceiling: unchanged
    (2560, 1440, 2560, 1440),   # exactly the ceiling
    (3840, 2160, 2560, 1440),   # 4K scales down to the ceiling
    (100, 100, 100, 100),       # small frames pass through
    (101, 101, 101, 101),       # odd at 1:1: the frame, unrounded
])
def test_work_size(w, h, expect_w, expect_h):
    assert work_size(w, h) == (expect_w, expect_h)


def test_work_size_never_exceeds_the_source():
    """The work resolution must never be larger than the frame it came from."""
    for w, h in [(640, 480), (1920, 1080), (1000, 700), (101, 539)]:
        ww, wh = work_size(w, h)
        assert ww <= w and wh <= h


@pytest.mark.parametrize("scale,expect_w,expect_h", [
    (1.0, 2560, 1440),   # full resolution
    (0.5, 1280, 720),    # half in each axis: a quarter of the pixels
    (0.75, 1920, 1080),
])
def test_work_scale_is_the_performance_dial(scale, expect_w, expect_h):
    """The product's `work_scale`, and the reason it exists here.

    The network works on a fraction of the frame and the worker scales the
    result back to full, so lowering the scale leaves the output size alone and
    takes the neural cost down with the square of it. That is the lever for
    frame rate; it is not a way to get more resolution.
    """
    assert work_size(2560, 1440, scale) == (expect_w, expect_h)


def test_work_scale_never_exceeds_the_source():
    """Whatever the scale, the network is never given more pixels than exist."""
    for scale in (0.25, 0.5, 1.0):
        for w, h in [(640, 480), (1920, 1080), (3840, 2160), (101, 539)]:
            ww, wh = work_size(w, h, scale)
            assert ww <= w and wh <= h, f"scale {scale} on {w}x{h} gave {ww}x{wh}"


def test_work_scale_rounds_down_and_floors():
    """A downscale rounds down (never up onto the frame) and floors at 64."""
    assert work_size(1000, 700, 0.999) == (998, 698)  # 999 -> 998, 699 -> 698
    assert work_size(100, 100, 0.01) == (64, 64)      # floored, not vanished


def test_a_work_scale_below_one_switches_on_nr_small(fake_capture, fake_display,
                                                     mock_worker_cmd):
    """The scale only does anything with the product's nr_small mode.

    Shrinking the work size on its own is a no-op — the feature is handed the
    full screen either way, which is the trap the upstream source records
    ("handing it the full screen ... is why work_scale never bought anything").
    So a scale below 1 must tell the worker the real frame size AND set
    NS_NR_SMALL, and the default path must leave both untouched.
    """
    from minimal.worker import worker_env

    full = Pipeline(capture=fake_capture, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO)
    assert full.nr_small is False
    assert (full.worker.full_w, full.worker.full_h) == (0, 0)
    assert "NS_NR_SMALL" not in worker_env({})

    small = Pipeline(capture=fake_capture, display=fake_display, headless=True,
                     worker_cmd=mock_worker_cmd, worker_cwd=REPO, work_scale=0.5)
    assert small.nr_small is True
    assert (small.worker.full_w, small.worker.full_h) == (small.width, small.height)
    assert small.work_w * 2 == full.work_w
    assert worker_env({}, nr_small=True)["NS_NR_SMALL"] == "1"


def test_the_scaled_path_still_returns_full_size_frames(fake_capture, fake_display,
                                                       mock_worker_cmd):
    """Colour in at full size, motion at the work size, output back at full size.

    That is the whole point of the mode: the neural cost falls but everything
    downstream still sees full-resolution frames.
    """
    pipe = Pipeline(capture=fake_capture, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO, work_scale=0.5)
    passed = pipe.run(frames=2)
    assert passed["frames_done"] == 2
    assert passed["frames_skipped"] == 0
    assert passed["after"].shape[:2] == (pipe.height, pipe.width)


def test_motion_small_sends_the_field_at_flow_size():
    """MOTS: the flag is set and the payload is the flow size, not the work size.

    Checked at the wire level rather than through a run because the mock refuses
    a small motion field (it has no MOTS scaler and says so instead of quietly
    desyncing). The real worker is what actually upscales it, on the GPU.
    """
    import io
    import struct

    from protocol import FRAME_FLAG_MOTION_SMALL, FRAME_FMT, send_frame
    from minimal.worker import FLOW_H, FLOW_W

    class Stub:
        def __init__(self):
            self.stdin = io.BytesIO()

    head = struct.calcsize(FRAME_FMT)
    rgba = np.zeros((720, 1280, 4), dtype=np.uint8)
    motion = np.zeros((FLOW_H, FLOW_W, 2), dtype=np.float16)

    stub = Stub()
    send_frame(stub, 3, rgba, motion, False, 0, None, motion_small=True)
    raw = stub.stdin.getvalue()
    _, index, _reset, flags, _pts = struct.unpack(FRAME_FMT, raw[:head])
    assert index == 3
    assert flags & FRAME_FLAG_MOTION_SMALL, "the flag the worker reads is missing"
    # Colour first, then motion — the payload is colour + field, so the field
    # starts after the frame, not right after the header.
    colour_bytes = len(rgba.tobytes())
    assert raw[head + colour_bytes:] == motion.tobytes()
    assert len(raw) - head == colour_bytes + FLOW_W * FLOW_H * 4

    # And the default path must be untouched: full-size field, no flag.
    full = np.zeros((720, 1280, 2), dtype=np.float16)
    stub = Stub()
    send_frame(stub, 3, rgba, full, False, 0, None, motion_small=False)
    raw = stub.stdin.getvalue()
    _, _index, _reset, flags, _pts = struct.unpack(FRAME_FMT, raw[:head])
    assert not flags & FRAME_FLAG_MOTION_SMALL
    assert len(raw) - head == colour_bytes + 1280 * 720 * 4


def test_motion_small_shrinks_what_goes_down_the_pipe():
    """The point of it: the inbound bytes per frame drop by nearly half."""
    full = 1280 * 720 * 4 + 1280 * 720 * 4
    small = 1280 * 720 * 4 + FLOW_W * FLOW_H * 4
    assert small < full * 0.55, "a small motion field should halve the frame"
    assert (full - small) / 1e6 > 3.0  # ~3.5 MB saved per frame at 720p


def test_the_capture_split_is_reported_without_being_double_counted(
        fake_capture, fake_display, mock_worker_cmd):
    """A 325ms grab means opposite things depending on where it goes.

    If the wait dominates, the compositor is delivering slowly and nothing
    downstream can help. If the read dominates, it is our copy. The split must
    be reported, and it must NOT be added into the frame total — those are the
    same milliseconds as the capture stage.
    """
    import time

    real_grab = fake_capture.grab

    def slow_grab():
        """A grab that really takes 330ms, of which 300 is waiting."""
        time.sleep(0.30)
        fake_capture.last_wait = 0.30        # the frame arriving
        frame = real_grab()
        time.sleep(0.03)
        fake_capture.last_read = 0.03        # our copy of it
        return frame

    fake_capture.grab = slow_grab
    pipe = Pipeline(capture=fake_capture, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO)
    passed = pipe.run(frames=3)
    t = passed["timing"]

    assert t["capture_wait"] == pytest.approx(0.30, abs=0.02)
    assert t["capture_read"] == pytest.approx(0.03, abs=0.02)
    # The capture stage covers both halves, so the total must be built without
    # them: adding them would count the grab twice and overstate the fps.
    assert t["total"] == pytest.approx(
        t["capture"] + t["send"] + t["recv"] + t["display"])
    assert t["total"] < t["capture"] + t["capture_wait"]
    assert t["capture"] >= t["capture_wait"] + t["capture_read"] - 0.005


def test_a_source_that_cannot_split_says_so(fake_capture, fake_display,
                                            mock_worker_cmd):
    """No producer to wait for means no split, rather than a split of zeros."""
    fake_capture.last_wait = None
    fake_capture.last_read = None
    pipe = Pipeline(capture=fake_capture, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO)
    t = pipe.run(frames=2)["timing"]
    assert "capture_wait" not in t
    assert "capture_read" not in t


def test_the_capture_split_separates_a_stocked_pipe_from_a_slow_producer():
    """The split is only worth printing if it actually discriminates.

    Checked against two real producers driving the real read path (no portal —
    the object is built directly, since only the pipe matters here):

      a stocked pipe          -> we just copy it, so `read` is small
      a dribbling producer    -> the bytes arrive slowly, so `read` carries it

    The first version of this used a plain buffered read, which blocks for the
    whole request and reported read 0.0ms for both. Without this test that
    would have looked like a measurement.
    """
    import subprocess
    import sys

    from minimal.capture_wayland import PortalCapture

    w, h = 320, 180
    need = w * h * 4

    def grab_from(writer: str):
        proc = subprocess.Popen([sys.executable, "-c", writer],
                                stdout=subprocess.PIPE)
        cap = object.__new__(PortalCapture)     # no portal needed for this
        cap.width, cap.height = w, h
        cap._proc = proc
        cap._stderr = None
        cap.last_wait = cap.last_read = None
        out = cap.grab()
        proc.wait()
        return out, cap

    frame, cap = grab_from(
        f"import sys\nsys.stdout.buffer.write(b'\\x7f' * {need})\n"
        f"sys.stdout.buffer.flush()\n")
    assert frame.shape == (h, w, 4)
    assert cap.last_read is not None and cap.last_read < 0.10, (
        f"a stocked pipe should copy quickly, read was {cap.last_read}")

    # Four chunks with a pause after each: the producer, not us, sets the pace.
    frame, cap = grab_from(
        f"import sys, time\n"
        f"for _ in range(4):\n"
        f"    sys.stdout.buffer.write(b'\\x7f' * ({need} // 4))\n"
        f"    sys.stdout.buffer.flush()\n"
        f"    time.sleep(0.08)\n")
    assert frame.shape == (h, w, 4)
    assert cap.last_read is not None and cap.last_read > 0.15, (
        f"a slow producer should show up in read, read was {cap.last_read}")


def test_bypass_is_a_real_no_ngx_control():
    """BYPASS carries its own flag, and it is not the same as zeroed strengths.

    Zeroed strengths may still run the network; this tells the worker to skip
    NGX altogether, which is the only way to price the network against the
    texture path. Checked on the wire so the flag cannot be dropped silently and
    turn the control into a duplicate of `baseline`.
    """
    import io
    import struct

    from protocol import FRAME_FLAG_BYPASS, FRAME_FLAG_MOTION_SMALL, FRAME_FMT, send_frame

    class Stub:
        def __init__(self):
            self.stdin = io.BytesIO()

    head = struct.calcsize(FRAME_FMT)
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)
    motion = np.zeros((4, 4, 2), dtype=np.float16)

    stub = Stub()
    send_frame(stub, 0, rgba, motion, False, 0, None, bypass=True)
    flags = struct.unpack(FRAME_FMT, stub.stdin.getvalue()[:head])[3]
    assert flags & FRAME_FLAG_BYPASS, "the worker would not know to skip NGX"
    assert not flags & FRAME_FLAG_MOTION_SMALL

    stub = Stub()
    send_frame(stub, 0, rgba, motion, False, 0, None)
    flags = struct.unpack(FRAME_FMT, stub.stdin.getvalue()[:head])[3]
    assert not flags & FRAME_FLAG_BYPASS


def test_bypass_reaches_the_worker_and_still_runs(fake_capture, fake_display,
                                                  mock_worker_cmd):
    """Off by default, set when asked, and the loop still completes."""
    def build(**kw):
        return Pipeline(capture=fake_capture, display=fake_display, headless=True,
                        worker_cmd=mock_worker_cmd, worker_cwd=REPO, **kw)

    plain = build()
    assert plain.bypass is False and plain.worker.bypass is False

    off = build(bypass=True)
    assert off.bypass is True and off.worker.bypass is True
    passed = off.run(frames=2)
    assert passed["frames_done"] == 2
    assert passed["frames_skipped"] == 0


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


def test_saved_pair_comes_from_the_same_iteration(fake_capture, fake_display,
                                                  mock_worker_cmd, tmp_path):
    """--save-before and --save-after must describe ONE frame.

    Saving the first input against the last output measures whatever moved on
    screen in between as though it were the pass. On the synthetic test card,
    whose only moving part is a bar, that turned a 15.8/255 difference into
    48.7/255 — three times the effect actually being measured.

    FakeCapture changes its blue channel by +3 per grab, so the first and last
    inputs are distinguishable: over 5 frames the last input is grab #5.
    """
    from tests.conftest import FakeCapture

    pipe = Pipeline(capture=fake_capture, display=fake_display,
                    headless=True, worker_cmd=mock_worker_cmd,
                    worker_cwd=REPO)
    before_png, after_png = tmp_path / "before.png", tmp_path / "after.png"
    summary = pipe.run(frames=5, save_before=str(before_png),
                       save_after=str(after_png))

    assert before_png.exists() and after_png.exists()

    src = FakeCapture(320, 180)
    for _ in range(4):
        src.grab()
    fifth = src.grab()          # what frame index 4 was fed

    assert np.array_equal(summary["before"], fifth), (
        "the saved input is not the one from the same iteration as the output — "
        "it looks like the first frame was kept instead")


def test_pipeline_reports_worker_death(fake_capture, fake_display):
    """A worker that dies mid-run must be reported, not silently looped."""
    cmd = [sys.executable, str(REPO / "tests" / "mock_worker.py"), "--fail", "2"]
    pipe = Pipeline(capture=fake_capture, display=fake_display,
                    headless=True, worker_cmd=cmd, worker_cwd=REPO)
    with pytest.raises(RuntimeError, match="worker died"):
        pipe.run(frames=6)


def test_timing_covers_every_stage(fake_capture, fake_display, mock_worker_cmd):
    """A frame step is measured in four places, and they add up.

    The point of the breakdown is that "4.2 fps" is not actionable on its own:
    the fix is completely different depending on whether the time is lost in the
    capture, in our bytes down the pipe, or waiting on the worker. A stage that
    silently stops being timed makes the report say the frame is cheap.
    """
    pipe = Pipeline(capture=fake_capture, display=fake_display,
                    headless=True, worker_cmd=mock_worker_cmd, worker_cwd=REPO)
    passed = pipe.run(frames=3, save_before=None, save_after=None)
    t = passed["timing"]

    for stage in ("capture", "send", "recv", "display"):
        assert stage in t, f"{stage} is not being timed"
        assert t[stage] > 0, f"{stage} recorded no time at all"
    assert t["count"] == 3
    assert t["total"] == pytest.approx(
        t["capture"] + t["send"] + t["recv"] + t["display"])
    assert 0 < t["fps"] < 10_000


def test_the_stage_times_fit_inside_the_wall_clock(fake_capture, fake_display,
                                                   mock_worker_cmd):
    """Summing to more than the run took would mean a stage is counted twice."""
    pipe = Pipeline(capture=fake_capture, display=fake_display,
                    headless=True, worker_cmd=mock_worker_cmd, worker_cwd=REPO)
    passed = pipe.run(frames=3)
    assert passed["timing"]["total"] <= passed["seconds"], (
        "the stage times add up to more than the run took")


def test_run_uses_the_one_frame_step(fake_capture, fake_display, mock_worker_cmd):
    """`run` must not carry its own copy of the sequence.

    It did, and a matched-pair fix landed in one copy and not the other. Now
    there is a single step, so this checks that a run really goes through it:
    `last_input` is only set by process_one.
    """
    pipe = Pipeline(capture=fake_capture, display=fake_display,
                    headless=True, worker_cmd=mock_worker_cmd, worker_cwd=REPO)
    passed = pipe.run(frames=2)
    assert pipe.last_input is not None, "run did not go through process_one"
    assert np.array_equal(passed["before"], pipe.last_input)


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