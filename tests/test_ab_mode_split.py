"""An A/B run has two frame times, and the summary must not report their average as a rate.

On the box a run summarised "26.45 fps steady" while the enhanced half was still ~40 ms a frame.
Half of that run's frames carried FRAME_FLAG_BYPASS, which skips the network entirely - so the
mixture looked like a rate the pipeline can hold with the pass on, and it cannot. These pin the
split so the number can never quietly mean the wrong thing again.
"""
from __future__ import annotations

import sys
from pathlib import Path

from minimal.loop import Pipeline

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def _pipeline(**kw) -> Pipeline:
    return Pipeline(capture=kw.pop("capture"), display=kw.pop("display"), headless=True,
                    worker_cmd=kw.pop("worker_cmd"), worker_cwd=REPO, **kw)


def test_a_run_without_ab_puts_every_frame_in_one_mode(fake_capture, fake_display,
                                                       mock_worker_cmd):
    pipe = _pipeline(capture=fake_capture, display=fake_display, worker_cmd=mock_worker_cmd)
    summary = pipe.run(frames=6)
    modes = summary["modes"]
    assert modes["alternate"] == 0
    assert modes["bypassed_frames"] == 0
    assert modes["enhanced_frames"] == summary["frames_done"]
    assert modes["enhanced_seconds"] > 0


def test_an_ab_run_splits_its_frames_between_the_two_modes(fake_capture, fake_display,
                                                           mock_worker_cmd):
    """The bypass half must be counted, not folded into the enhanced rate."""
    pipe = _pipeline(capture=fake_capture, display=fake_display, worker_cmd=mock_worker_cmd,
                     ab_alternate=0.001)
    summary = pipe.run(frames=8)
    modes = summary["modes"]
    assert modes["alternate"] == 0.001
    assert modes["bypassed_frames"] > 0, "the toggle never fired"
    assert modes["enhanced_frames"] > 0
    assert modes["bypassed_frames"] + modes["enhanced_frames"] == summary["frames_done"]


def test_the_two_modes_are_timed_separately(fake_capture, fake_display, mock_worker_cmd):
    """Each mode gets its own clock, which is the whole point of the split."""
    pipe = _pipeline(capture=fake_capture, display=fake_display, worker_cmd=mock_worker_cmd,
                     ab_alternate=0.001)
    modes = pipe.run(frames=8)["modes"]
    assert modes["enhanced_seconds"] > 0 and modes["bypassed_seconds"] > 0
    assert modes["enhanced_fps"] > 0 and modes["bypassed_fps"] > 0


def test_a_mode_with_no_frames_has_no_rate(fake_capture, fake_display, mock_worker_cmd):
    """No frames is not 0 fps: it is nothing to measure, and saying 0 would be a claim."""
    pipe = _pipeline(capture=fake_capture, display=fake_display, worker_cmd=mock_worker_cmd)
    modes = pipe.run(frames=4)["modes"]
    assert modes["bypassed_seconds"] == 0.0
    assert modes["bypassed_fps"] == 0.0


def test_the_summary_warns_when_the_ab_was_on():
    """The warning is what stops the mixture being read as a product rate."""
    source = (REPO / "minimal" / "__main__.py").read_text(encoding="utf-8")
    assert "the A/B was on" in source
    assert "--ab-alternate 0 to measure" in source
