"""Reading a process's CPU share, and reporting it as unknown rather than zero.

The number matters because the capture chain's CPU never appears in the frame
time: it is work that happens while the worker waits. At 2560x1440 the same
frame cost `send` 114.2ms arriving through the portal against 67.3ms produced
synthetically, and none of that gap was in the grab. If this reader is wrong,
that whole line of investigation is wrong with it.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from minimal.cpu import cpu_share, process_cpu_seconds  # noqa: E402


def test_a_busy_process_is_about_one_core():
    proc = subprocess.Popen([sys.executable, "-c", "while True: pass"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(0.3)
        before = process_cpu_seconds(proc.pid)
        time.sleep(0.5)
        after = process_cpu_seconds(proc.pid)
        share = cpu_share(before, after, 0.5)
        assert share is not None
        assert 0.8 < share < 1.3, f"a busy loop should be ~1 core, got {share:.2f}"
    finally:
        proc.kill()
        proc.wait()


def test_an_executable_whose_name_has_a_space_is_read_correctly(tmp_path):
    """/proc/<pid>/stat field 2 is in parentheses and may contain spaces.

    Counting the fields after it from a whitespace split of the whole line puts
    utime and stime in the wrong place — and this is not hypothetical: the
    reader is run against a process whose comm really does have a space here.
    """
    link = tmp_path / "a b"
    link.symlink_to(sys.executable)
    proc = subprocess.Popen([str(link), "-c", "while True: pass"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(0.3)
        comm = Path(f"/proc/{proc.pid}/comm").read_text().strip()
        assert " " in comm, "this test is pointless without a space in the name"

        before = process_cpu_seconds(proc.pid)
        time.sleep(0.5)
        after = process_cpu_seconds(proc.pid)
        share = cpu_share(before, after, 0.5)
        assert share is not None
        assert 0.8 < share < 1.3, f"got {share:.2f} — the fields are misaligned"
    finally:
        proc.kill()
        proc.wait()


def test_an_idle_process_is_near_zero():
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"])
    try:
        time.sleep(0.3)
        before = process_cpu_seconds(proc.pid)
        time.sleep(0.4)
        after = process_cpu_seconds(proc.pid)
        assert (after - before) < 0.1
    finally:
        proc.kill()
        proc.wait()


def test_a_missing_process_is_unknown_not_zero():
    """A fabricated zero would read as "the chain did nothing"."""
    assert process_cpu_seconds(999_999) is None
    assert process_cpu_seconds(None) is None


def test_cpu_share_needs_both_samples():
    assert cpu_share(None, 1.0, 1.0) is None
    assert cpu_share(1.0, None, 1.0) is None
    assert cpu_share(1.0, 2.0, 0.0) is None       # no wall time, no share
    assert cpu_share(1.0, 2.0, 2.0) == pytest.approx(0.5)


def test_the_summary_reports_the_capture_cpu_when_the_source_can(
        fake_capture, fake_display, mock_worker_cmd):
    """A source that can report its CPU gets measured over the run."""
    from minimal.loop import Pipeline

    calls = []

    def cpu_seconds():
        calls.append(time.monotonic())
        return time.monotonic() - calls[0]

    fake_capture.cpu_seconds = cpu_seconds
    pipe = Pipeline(capture=fake_capture, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO)
    summary = pipe.run(frames=3)
    cc = summary["capture_cpu"]
    assert cc is not None
    assert cc["share"] is not None
    assert cc["wall"] > 0


def test_the_end_reading_is_taken_before_the_capture_is_closed(
        fake_capture, fake_display, mock_worker_cmd):
    """The bug this shipped with: run() closed the capture, then sampled it.

    PortalCapture.close() drops the pipeline handle, so the end reading came
    back None and every run printed "pid None" with "the reading failed" — the
    measurement was taken after the thing it measures was gone. The fake here
    behaves the same way, so the ordering is pinned rather than assumed.
    """
    import time as _time

    from minimal.loop import Pipeline

    state = {"t0": _time.monotonic(), "closed": False}

    def cpu_seconds():
        return None if state["closed"] else _time.monotonic() - state["t0"]

    def close():
        state["closed"] = True          # exactly what PortalCapture does

    fake_capture.cpu_seconds = cpu_seconds
    fake_capture.pipeline_pid = 12345
    fake_capture.close = close

    pipe = Pipeline(capture=fake_capture, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO)
    cc = pipe.run(frames=3)["capture_cpu"]

    assert cc is not None
    assert cc["share"] is not None, (
        "the end reading was taken after close(); sample it in the finally "
        "block BEFORE the capture is closed")
    assert cc["share"] > 0
    assert cc["pid"] == 12345


def test_a_source_with_no_cpu_reading_reports_none(fake_capture, fake_display,
                                                   mock_worker_cmd):
    """No measurement is None, never a zero that reads as "did nothing"."""
    from minimal.loop import Pipeline

    assert not hasattr(fake_capture, "cpu_seconds")
    pipe = Pipeline(capture=fake_capture, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO)
    assert pipe.run(frames=2)["capture_cpu"] is None
