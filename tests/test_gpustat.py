"""GPU utilisation during a run: a diagnostic that must never break the run.

The worker's timings say how long a frame took. Whether the GPU was busy while it took it decides
what to do next, so the sampler has to be trustworthy - and it has to be harmless when the probe
is missing or starts failing mid-run, because it is the one part of a run that is not the product.
"""
from __future__ import annotations

import time

import pytest

import minimal.gpustat as gpustat
from minimal.gpustat import GpuSampler


def _reading(util=50, mem=2048, total=16376, clock=2610, name="RTX 4080 SUPER"):
    return {"name": name, "util_percent": util, "mem_used_mib": mem,
            "mem_total_mib": total, "clock_sm_mhz": clock}


def _no_probe(monkeypatch):
    monkeypatch.setattr(gpustat, "load_probe", lambda: None)


def test_no_probe_is_reported_as_such_not_as_zero(monkeypatch):
    """ "0% utilisation" and "we could not ask" are different claims."""
    _no_probe(monkeypatch)
    sampler = GpuSampler()
    assert sampler.available is False
    sampler.start()          # a no-op: nothing to ask
    sampler.stop()
    assert sampler.summary()["available"] is False
    assert "no reading" in sampler.describe()


def test_the_summary_reports_the_spread_not_just_the_mean():
    readings = [_reading(util=u) for u in (10, 80, 90, 40)]
    it = iter(readings)
    sampler = GpuSampler(interval=0.05, probe=lambda: next(it, None))
    sampler.start()
    time.sleep(0.3)
    sampler.stop()

    summary = sampler.summary()
    assert summary["available"] is True
    assert summary["samples"] >= 3
    utils = [s["util_percent"] for s in sampler.samples]
    assert summary["util_mean"] == pytest.approx(sum(utils) / len(utils))
    assert summary["util_min"] == min(utils)
    assert summary["util_max"] == max(utils)


def test_memory_and_clock_come_through():
    sampler = GpuSampler(interval=0.05, probe=lambda: _reading())
    sampler.start()
    time.sleep(0.15)
    sampler.stop()
    summary = sampler.summary()
    assert summary["mem_max_mib"] == 2048
    assert summary["mem_total_mib"] == 16376
    assert summary["clock_max_mhz"] == 2610
    text = sampler.describe()
    assert "GiB" in text and "MHz" in text


def test_a_failing_probe_does_not_reach_the_caller():
    def boom():
        raise RuntimeError("nvidia-smi went away")

    sampler = GpuSampler(interval=0.05, probe=boom)
    sampler.start()          # must not raise
    time.sleep(0.15)
    sampler.stop()
    assert sampler.errors > 0
    assert sampler.summary()["available"] is False


def test_a_probe_returning_nothing_is_not_a_sample():
    sampler = GpuSampler(interval=0.05, probe=lambda: None)
    sampler.start()
    time.sleep(0.15)
    sampler.stop()
    assert sampler.samples == []
    assert "no samples" in sampler.describe()


def test_stopping_is_idempotent_and_the_thread_ends():
    sampler = GpuSampler(interval=0.05, probe=lambda: _reading())
    sampler.start()
    time.sleep(0.1)
    sampler.stop()
    sampler.stop()
    assert sampler._thread is not None and not sampler._thread.is_alive()


def test_the_cli_offers_it():
    source = open("minimal/__main__.py", encoding="utf-8").read()
    assert '"--report-gpu"' in source and "pipe.gpu.describe()" in source
