"""Defaults that change a run's comparability must be off by default.

`--gil-switch-ms` was added at 1ms, which is not CPython's 5ms - so every run after it would have
been measured with a different interpreter configuration than every run before it, with nothing in
the summary to say so. The experiment that justified the flag answered "no": the recv split moved
0.2ms at 1ms, inside the noise, because the client-side handoff it was aimed at does not exist.
A knob that buys nothing and changes every measurement belongs off, and this is the test that says
so rather than a comment that nobody reads.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from minimal.__main__ import build_parser   # noqa: E402
from minimal.loop import Pipeline           # noqa: E402


def test_the_gil_knob_is_off_by_default():
    args = build_parser().parse_args([])
    assert args.gil_switch_ms == 0.0, (
        "a non-zero default silently reconfigures the interpreter for every run, which makes it "
        "incomparable with the runs already on record")


def test_asking_for_it_still_works():
    args = build_parser().parse_args(["--gil-switch-ms", "1"])
    assert args.gil_switch_ms == 1.0


def test_interpolation_is_off_by_default():
    """It costs a hold inside the frame and a readback in the worker; neither is free."""
    args = build_parser().parse_args([])
    assert args.interpolate is False
    assert args.interp_pace_ms == 8.0


def test_shared_memory_is_on_by_default():
    """14.7MB each way at 1440p, and the pipe path under-reports by 7.5-13ms on the shapes
    measured. A transport that costs 7.5ms a frame is not a thing to opt into."""
    assert build_parser().parse_args([]).shm is True


def test_the_pipe_path_is_still_reachable():
    """The record's numbers before 2026-11-02 are pipe numbers, and comparing the two
    transports is the only remaining reason to want the slower one."""
    assert build_parser().parse_args(["--no-shm"]).shm is False
    assert build_parser().parse_args(["--shm"]).shm is True


def test_a_worker_that_refuses_shared_memory_still_runs(fake_capture, fake_display,
                                                        mock_worker_cmd):
    """The reason the default is safe: asking cannot cost a run.

    The mock refuses SHMI outright, exactly as the Wine worker does. The refusal has to be fast
    (it raises on the SACK rather than waiting out the timeout) and the frames have to keep
    flowing down the pipe, because otherwise every run against a worker that has not learned
    the handshake would fail on a default it never asked about.
    """
    import time

    started = time.monotonic()
    pipe = Pipeline(capture=fake_capture, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO, shm=True)
    summary = pipe.run(frames=2)
    elapsed = time.monotonic() - started

    assert summary["frames_done"] == 2
    assert pipe.worker.shm is not None and not pipe.worker.shm.negotiated, (
        "the mock refuses SHMI, so this run must have stayed on the pipe")
    assert elapsed < 10.0, (
        f"the refusal took {elapsed:.1f}s - it is waiting out a timeout instead of reading the "
        f"refusal, and every test and every Wine run would pay it")
