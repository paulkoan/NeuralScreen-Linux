"""The prefetch drain: what it buys, and what it must not hide.

The box measured the same grab at 12.8-13.4ms with nothing else running and
~238ms inside the MVP's loop. That is not the compositor being slow, it is the
loop only reading a frame after the worker has finished the previous one — and a
screencast whose client stops consuming stops producing. These tests pin the two
things that follow: the consumer gets the NEWEST frame, and an old one it never
saw is reported as dropped rather than silently processed late.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from minimal.prefetch import Prefetch  # noqa: E402


class FakeSource:
    """Numbered frames, so a consumer can tell which one it got."""

    def __init__(self, delay: float = 0.0, fail_after: int | None = None):
        self.resolution = (4, 4)
        self.delay = delay
        self.fail_after = fail_after
        self.n = 0
        self.closed = False

    def grab(self) -> np.ndarray:
        if self.delay:
            time.sleep(self.delay)
        if self.fail_after is not None and self.n >= self.fail_after:
            raise RuntimeError("the producer died")
        self.n += 1
        return np.full((4, 4, 4), self.n % 251, dtype=np.uint8)

    def close(self) -> None:
        self.closed = True


def test_grab_blocks_only_until_the_first_frame():
    """A slow producer delays the first grab, not every one."""
    src = FakeSource(delay=0.05)
    pf = Prefetch(src)
    try:
        t0 = time.monotonic()
        frame = pf.grab()
        first = time.monotonic() - t0
        assert frame.shape == (4, 4, 4)
        assert first >= 0.04, "the first grab must wait for a frame to exist"
    finally:
        pf.close()


def test_the_newest_frame_wins_and_the_skipped_ones_are_counted():
    """The whole point: a consumer that was busy gets the current frame.

    Without this the loop processes a stale frame and the staleness grows with
    however long the worker took, which is the latency the prefetch is for.
    """
    src = FakeSource()                      # produces as fast as it can
    pf = Prefetch(src)
    try:
        pf.grab()                           # let it get going
        time.sleep(0.05)                    # the consumer goes away for a while
        latest = int(pf.grab()[0, 0, 0])
        stats = pf.stats()

        assert stats["dropped"] > 0, "a running producer should have outrun us"
        assert stats["drained"] >= latest, "the drain should have seen it"
        # Sampling the newest, not the one that happened to be queued first.
        assert latest == stats["drained"] % 251, (
            f"got frame {latest}, newest drained was {stats['drained']}")
    finally:
        pf.close()


def test_the_age_reports_how_stale_the_frame_was():
    """The age is the latency the capture adds, so it is reported, not hidden."""
    src = FakeSource(delay=0.02)
    pf = Prefetch(src)
    try:
        pf.grab()
        fresh = pf.stats()["age"]
        assert 0.0 <= fresh < 0.5, f"a just-arrived frame should be young: {fresh}"
    finally:
        pf.close()


def test_a_dead_producer_is_raised_not_looped_on():
    """A frozen frame that looks like progress is worse than a stopped run."""
    src = FakeSource(fail_after=2)
    pf = Prefetch(src)
    try:
        with pytest.raises(RuntimeError, match="the producer died"):
            for _ in range(50):
                pf.grab()
                time.sleep(0.01)
    finally:
        pf.close()


def test_close_stops_the_thread_and_closes_the_source():
    src = FakeSource()
    pf = Prefetch(src)
    pf.grab()
    before = threading.active_count()
    pf.close()
    assert src.closed
    assert not pf._thread.is_alive()
    # The drain thread is gone, not merely stopped cooperatively.
    assert threading.active_count() <= before


def test_no_capture_split_is_reported():
    """The portal's wait/read split does not apply once the drain owns the read.

    Reporting a split of zeros would be a measurement that means nothing, which
    is the mistake this whole area keeps making.
    """
    src = FakeSource()
    pf = Prefetch(src)
    try:
        assert pf.last_wait is None and pf.last_read is None
    finally:
        pf.close()


def test_the_pipeline_reports_prefetch_stats(fake_capture, fake_display,
                                             mock_worker_cmd):
    """A run through the loop carries the drain's numbers into the summary."""
    from minimal.loop import Pipeline

    pf = Prefetch(fake_capture)
    try:
        pipe = Pipeline(capture=pf, display=fake_display, headless=True,
                        worker_cmd=mock_worker_cmd, worker_cwd=REPO)
        passed = pipe.run(frames=3)
        stats = passed["prefetch"]
        assert stats is not None
        assert stats["taken"] == 3
        assert stats["drained"] >= 3
    finally:
        pf.close()
