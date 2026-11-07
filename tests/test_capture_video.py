"""The video source: the whole pipeline's frames, from a file, the same every run.

Every live run so far has been a different session - the same unchanged pipeline read 15.8, 17.1,
17.3 and 20.9 fps depending on what the stream was showing and what else the box was doing - so a
change in one of those numbers is not evidence of anything. These tests are about the properties
that make a file worth using instead: the frames are the file's frames, in the file's order, the
size is what was asked for, and two runs of the same file are the same run.

They decode real video with PyAV rather than mocking it, because the failure modes here are all in
the decoder: a view into a buffer the decoder reuses, a rewind that does not rewind, a reformat
that silently keeps the wrong size. ffmpeg and PyAV are both present on this box and on the GPU box,
so a skip here means something is genuinely missing.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from minimal.capture import CaptureError, VideoCapture, open_capture   # noqa: E402

pytest.importorskip("av", reason="PyAV is the decoder this source is built on")

FRAMES = 24
NATIVE = (320, 180)


@pytest.fixture(scope="module")
def clip(tmp_path_factory) -> Path:
    """A short clip with moving content, so consecutive frames are provably different."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not installed, so no clip can be made")
    path = tmp_path_factory.mktemp("clip") / "card.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", f"testsrc=size={NATIVE[0]}x{NATIVE[1]}:rate=30",
         "-frames:v", str(FRAMES), "-pix_fmt", "yuv420p", str(path)],
        check=True, capture_output=True)
    return path


def test_the_frames_are_the_clip(clip):
    cap = VideoCapture(clip)
    assert cap.resolution == NATIVE
    frame = cap.grab()
    assert frame.shape == (NATIVE[1], NATIVE[0], 4)
    assert frame.dtype == np.uint8
    cap.close()


def test_a_writable_copy_comes_back(clip):
    """A view into the decoder's buffer is a frame that rots a few frames later."""
    cap = VideoCapture(clip)
    frame = cap.grab()
    assert frame.flags.writeable
    frame[0, 0, 0] = frame[0, 0, 0]           # must not fault, and must not touch the decoder
    later = cap.grab()
    assert later is not frame
    cap.close()


def test_frames_advance_in_the_file_order(clip):
    cap = VideoCapture(clip)
    frames = [cap.grab() for _ in range(6)]
    cap.close()
    assert not all(np.array_equal(frames[0], f) for f in frames[1:]), (
        "every frame identical — testsrc moves, so this is a decode that is not advancing")


def test_two_runs_of_the_same_file_are_the_same_run(clip):
    """The reason this source exists: the frames must not depend on the session."""
    a = VideoCapture(clip)
    b = VideoCapture(clip)
    for i in range(12):
        assert np.array_equal(a.grab(), b.grab()), f"frame {i} differs between two reads"
    a.close()
    b.close()


def test_the_file_loops_rather_than_ending(clip):
    """The replay is periodic: the second pass repeats the first, frame for frame.

    The period is measured rather than assumed. ffmpeg wrote 19 decodable frames for the 24 that
    were asked for, and a test that hard-codes the request instead of the result fails on a fact
    about the encoder while looking like a fact about the loop.
    """
    cap = VideoCapture(clip)
    seq = [cap.grab() for _ in range(60)]
    cap.close()
    assert cap.loops >= 1, "the file never rewound"
    period = next((k for k in range(1, len(seq)) if np.array_equal(seq[k], seq[0])), None)
    assert period, "the clip never came back to its first frame"
    for j in range(period):
        assert np.array_equal(seq[period + j], seq[j]), (
            f"frame {j} of the second pass differs from the first — the replay is not periodic")


def test_a_target_size_is_honoured(clip):
    cap = VideoCapture(clip, width=640, height=360)
    assert cap.resolution == (640, 360)
    assert cap.grab().shape == (360, 640, 4)
    cap.close()


def test_a_missing_file_says_so():
    with pytest.raises(CaptureError, match="cannot open video"):
        VideoCapture("/nonexistent/nope.mp4")


def test_the_source_is_reachable_through_open_capture(clip):
    cap = open_capture("video", input_video=clip, width=None, height=None)
    assert isinstance(cap, VideoCapture)
    cap.close()


def test_video_without_a_path_is_refused():
    with pytest.raises(CaptureError, match="--input-video"):
        open_capture("video")


def test_the_stats_name_what_was_replayed(clip):
    cap = VideoCapture(clip)
    for _ in range(3):
        cap.grab()
    stats = cap.stats()
    cap.close()
    assert stats["source"] == "video" and stats["path"] == str(clip)
    assert stats["frames_decoded"] >= 4


def test_the_cli_offers_the_source_and_the_path():
    source = (REPO / "minimal" / "__main__.py").read_text(encoding="utf-8")
    assert '"video"' in source
    assert "--input-video" in source
    assert "input_video=args.input_video" in source


def test_the_source_drives_the_whole_loop(clip, fake_display, mock_worker_cmd):
    """Through the real Pipeline against the protocol-speaking mock worker.

    The point of the source is that a whole run can be made from a file, so this has to prove it
    reaches the loop as a source - not just that it decodes.
    """
    from minimal.loop import Pipeline

    cap = VideoCapture(clip)
    pipe = Pipeline(capture=cap, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO, want_pixels=False)
    summary = pipe.run(frames=6)
    assert summary["frames_done"] == 6, summary
    assert summary["frames_skipped"] == 0
    assert summary["timing"]["capture"] > 0, "the capture leg must have been timed"


def test_the_video_source_is_not_read_as_a_prefetch_wrapper(clip, fake_display, mock_worker_cmd):
    """A source with `stats` was read as a drain report, and the run died on its last line.

    The queue run r2026-11-07-videosrc did all 120 frames, shut its worker down cleanly, and then
    exited 1 with KeyError: 'drained' - the summary printed the video's stats as though they were
    the prefetch wrapper's. Only the wrapper reports a drain.
    """
    from minimal.loop import Pipeline

    cap = VideoCapture(clip)
    pipe = Pipeline(capture=cap, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO, want_pixels=False)
    summary = pipe.run(frames=4)
    assert summary["prefetch"] is None, "the video source is not a prefetch wrapper"
    assert summary["source"]["path"] == str(clip)
    assert summary["source"]["frames_decoded"] >= 4


def test_the_summary_reports_which_file_was_replayed():
    """A timing from a file says nothing without the file, so the run has to name it."""
    source = (REPO / "minimal" / "__main__.py").read_text(encoding="utf-8")
    assert "source: replayed" in source
