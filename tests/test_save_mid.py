"""A mid-frame has to be visible in an artifact, or a wrong warp can only be seen live.

`--save-after` writes a real frame; the generated mid-frame - the whole point of the flag - was
written nowhere. That made the picture checkable only by sitting in front of the screen while the
run happened, which is useless for a queued run and useless for anyone who is not at the box.

These tests pin three things: that `--save-mid` writes the mid-frame and not the frame beside it,
that it writes nothing (and says so) when no mid-frame arrives rather than producing a
real frame wearing the mid's name, and that asking for interpolation implies asking for pixels -
because a mid-frame is a pixel reply, and a run that asks for neither reports zero mids for a
reason that has nothing to do with the feature working.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from minimal.__main__ import build_parser, wants_pixels
from minimal.loop import Pipeline, _save_rgba

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

MARKER = bytes([0xAB, 0xCD, 0xEF, 0x01])


def parse(*argv):
    return build_parser().parse_args(list(argv))


# --- the flag that makes the run able to answer at all ---------------------------------------

def test_interpolating_means_asking_for_pixels():
    """The worker's midPath is wantInterp && wantPixels, so one without the other is a null."""
    args = parse("--headless", "--interpolate")
    assert wants_pixels(args), (
        "a headless --interpolate run would ask for no pixels, get no mid-frames, and report "
        "zero mids - which reads as a broken feature rather than as an unasked question")


def test_saving_a_mid_also_means_asking_for_pixels():
    assert wants_pixels(parse("--headless", "--save-mid", "m.png"))


def test_a_plain_headless_run_still_asks_for_none():
    """The reason the list exists: 29.5MB a frame the caller throws away."""
    assert not wants_pixels(parse("--headless"))


def test_a_window_run_asks_for_them():
    assert wants_pixels(parse())


def test_the_other_savers_still_ask_for_them():
    for argv in (["--headless", "--save-after", "a.png"],
                 ["--headless", "--save-before", "b.png"],
                 ["--headless", "--save-diff", "d.png"],
                 ["--headless", "--report-diff"]):
        assert wants_pixels(parse(*argv)), argv


# --- what lands on disk ----------------------------------------------------------------------

def _pipeline(fake_capture, fake_display, mock_worker_cmd, **kw):
    return Pipeline(capture=fake_capture, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO, **kw)


def test_the_saved_mid_is_the_mid_frame(fake_capture, fake_display, mock_worker_cmd, tmp_path):
    saved = tmp_path / "mid.png"
    pipe = _pipeline(fake_capture, fake_display, mock_worker_cmd,
                     interpolate=True, interp_pace=0.0)
    summary = pipe.run(frames=3, save_mid=str(saved))

    assert summary["interp_shown"] == 3
    assert saved.exists(), "the mid-frame was generated and not written anywhere"
    assert pipe.last_mid is not None
    assert bytes(pipe.last_mid[0, 0, :4]) == MARKER, "that is a real frame, not the mid"

    # The same array written through the same writer is the same file - so the pixels on disk
    # are the mid-frame's, not the neighbouring real frame's.
    expected = tmp_path / "expected.png"
    _save_rgba(str(expected), pipe.last_mid)
    assert saved.read_bytes() == expected.read_bytes()


def test_the_saved_mid_is_not_the_real_frame(fake_capture, fake_display, mock_worker_cmd,
                                             tmp_path):
    """The failure this guards against is silent: a real frame under the mid's filename."""
    mid_path, after_path = tmp_path / "mid.png", tmp_path / "after.png"
    pipe = _pipeline(fake_capture, fake_display, mock_worker_cmd,
                     interpolate=True, interp_pace=0.0)
    pipe.run(frames=3, save_mid=str(mid_path), save_after=str(after_path))
    assert mid_path.read_bytes() != after_path.read_bytes()


def test_no_mid_frame_means_no_file_and_no_failure(fake_capture, fake_display,
                                                   mock_worker_cmd, tmp_path):
    """A worker that does not know the flag replies once. That is not an error and must not
    leave a real frame sitting under the mid-frame's name."""
    saved = tmp_path / "mid.png"
    pipe = _pipeline(fake_capture, fake_display, mock_worker_cmd,
                     interpolate=True, interp_pace=0.0)
    pipe.worker.want_interp = False          # as a worker without the feature behaves
    summary = pipe.run(frames=3, save_mid=str(saved))
    assert summary["frames_done"] == 3
    assert summary["interp_shown"] == 0
    assert pipe.last_mid is None
    assert not saved.exists(), "nothing arrived, so nothing should be written under that name"


def test_the_mid_is_kept_only_when_one_arrives(fake_capture, fake_display, mock_worker_cmd):
    pipe = _pipeline(fake_capture, fake_display, mock_worker_cmd)
    pipe.run(frames=2)
    assert pipe.last_mid is None, "a run that did not ask must not hold a frame"


def test_the_mid_is_the_frame_before_the_one_that_was_served(fake_capture, fake_display,
                                                             mock_worker_cmd):
    """The mid's own claim: it is the previous frame's content, moved along the field a half
    frame. The mock's mid differs from the frame it accompanies, which is the least it can do -
    an "interpolated" frame identical to the frame before it is not interpolating."""
    pipe = _pipeline(fake_capture, fake_display, mock_worker_cmd,
                     interpolate=True, interp_pace=0.0)
    pipe.run(frames=4)
    mid = np.asarray(pipe.last_mid)
    assert mid.shape[2] == 4 and mid.dtype == np.uint8
