"""`recv` has to be separable into "our copy" and "waiting for the worker".

The client's recv stage is the largest number in a run and it is opaque: it holds the
worker's own time, the cross-process handoff and the copy of the frame out of the shared
section. A 14.7MB copy at host memory rate is ~1.5ms, so a recv of 28.6ms beside a worker
total of 19.7ms cannot be read as "the worker is slow" until the copy is taken out of it.

The reader thread already makes that copy (it must: one slot, overwritten next frame), so
it times it there and the summary reports it beside recv. These tests pin the contract that
matters: the split appears when there is data, and its absence is never reported as 0.
"""
from types import SimpleNamespace

from minimal.loop import Pipeline




class _FakeReader:
    def __init__(self, copy_ms=None):
        self.copy_ms = copy_ms or []


class _FakeWorker:
    def __init__(self, reader=None):
        self.reader = reader


def _pipeline(reader=None):
    """The smallest object timing_summary needs. It reads only self.timings."""
    pipe = Pipeline.__new__(Pipeline)
    pipe.timings = {k: [0.010] * 8 for k in ("capture", "send", "recv", "display")}
    pipe.capture_split = {"wait": [], "read": []}
    pipe.worker = _FakeWorker(reader) if reader is not None else None
    return pipe


def test_the_copy_is_reported_beside_recv():
    reader = _FakeReader([0.0012, 0.0015, 0.0014, 0.0013, 0.0016, 0.0015])
    out = _pipeline(reader).timing_summary()
    assert "recv_copy" in out, "a run with pixels must say what its copy cost"
    assert abs(out["recv_copy"] - 0.0015) < 1e-9, out["recv_copy"]
    assert out["recv_copy_min"] <= out["recv_copy"] <= out["recv_copy_max"]


def test_no_copy_data_means_no_claim():
    """A pipe-path run copies nothing out of a section, so it must not report a copy of 0."""
    out = _pipeline(_FakeReader([])).timing_summary()
    assert "recv_copy" not in out
    out = _pipeline().timing_summary()
    assert "recv_copy" not in out


def test_too_few_samples_is_not_a_median():
    """Five samples is the bar the other spreads use; below it a median is one frame's luck."""
    out = _pipeline(_FakeReader([0.001, 0.002, 0.003, 0.004])).timing_summary()
    assert "recv_copy" not in out
