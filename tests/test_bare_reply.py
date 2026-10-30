"""A bare reply is a completed frame when nothing asked for pixels.

The loop used to treat every None reply as "the worker skipped this evaluation". Once a run can
legitimately decline the pixel channel, a bare header is normal traffic - and counting it as
skipped would report a healthy 120-frame run as 120 skipped frames, which is exactly the kind of
number that has already cost this project a day. These pin both halves of the rule.
"""
from pathlib import Path

import pytest

from minimal.loop import Pipeline

REPO = Path(__file__).resolve().parent.parent


class QuietWorker:
    """Answers every frame with no pixels, the way a gated port does."""

    def __init__(self):
        self.sent = []
        self.logs = []
        self.proc = None

    def start(self):
        pass

    def is_alive(self):
        return True

    def send(self, index, rgba, motion, reset, pts=0, want_pixels=True, bgra=False):
        self.sent.append((index, want_pixels))

    def recv(self, index, timeout=None):
        return None

    def stop(self, timeout=None):
        return 0


@pytest.fixture
def quiet(fake_capture, fake_display, mock_worker_cmd):
    def make(want_pixels: bool) -> Pipeline:
        pipe = Pipeline(capture=fake_capture, display=fake_display, headless=True,
                        worker_cmd=mock_worker_cmd, worker_cwd=REPO,
                        want_pixels=want_pixels)
        pipe.worker = QuietWorker()
        return pipe
    return make


def test_a_bare_reply_is_a_completed_frame_without_pixels(quiet):
    summary = quiet(want_pixels=False).run(frames=3)
    assert summary["frames_done"] == 3
    assert summary["frames_skipped"] == 0, (
        "a no-pixel run must not report its own frames as skipped evaluations")


def test_a_bare_reply_is_still_a_skip_when_pixels_were_wanted(quiet):
    """The other direction: if we asked, silence is a real miss and must be counted."""
    summary = quiet(want_pixels=True).run(frames=3)
    assert summary["frames_done"] == 0
    assert summary["frames_skipped"] == 3


def test_the_loop_sends_the_pipeline_flag(quiet):
    pipe = quiet(want_pixels=False)
    pipe.run(frames=2)
    assert pipe.worker.sent, "nothing was sent"
    assert all(flag is False for _, flag in pipe.worker.sent)