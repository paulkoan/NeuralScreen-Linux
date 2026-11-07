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
