"""GPU utilisation while a run is in progress.

The worker reports how long each frame took; it cannot say whether the GPU was busy or idle
during that time. Both matter and they answer different questions: a frame that takes 14 ms while
the GPU sits at 30% is a frame we could make faster with better code, while the same frame at 98%
means the device is already the limit and the work has to come out of it.

The probe is the runner's own - `tools/gpu_status.py`, loaded by path so there is one copy of the
nvidia-smi query rather than two that drift.
"""
from __future__ import annotations

import importlib.util
import threading
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools" / "gpu_status.py"


def load_probe():
    """The first working probe from tools/gpu_status.py, or None when neither is available."""
    try:
        spec = importlib.util.spec_from_file_location("ns_gpu_status", TOOLS)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        return None
    for name in ("nvidia_smi", "rocm_smi"):
        fn = getattr(module, name, None)
        if fn is None:
            continue
        try:
            if fn() is not None:
                return fn
        except Exception:
            continue
    return None


class GpuSampler:
    """Poll the GPU on a thread for the life of a run, then summarise.

    Sampling never raises into the caller: a machine without nvidia-smi, or one where the query
    starts failing mid-run, still gets a frame report - the GPU numbers are a diagnostic, not a
    measurement the run depends on.
    """

    # One second, not the obvious tenth: each sample is an nvidia-smi process, and on this box
    # one takes ~60 ms - polling four times a second would spend a quarter of a core watching
    # rather than measuring.
    def __init__(self, interval: float = 1.0, probe=None, log=None):
        self.interval = max(0.1, float(interval))
        self._probe = probe if probe is not None else load_probe()
        self._log = log
        self.samples: list[dict] = []
        self.errors = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def available(self) -> bool:
        return self._probe is not None

    def start(self) -> "GpuSampler":
        if self._probe is None:
            return self
        self._thread = threading.Thread(target=self._run, name="gpu-sampler", daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                reading = self._probe()
                if reading:
                    reading["at"] = time.monotonic()
                    self.samples.append(reading)
            except Exception:
                self.errors += 1
            self._stop.wait(self.interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def summary(self) -> dict:
        """What the samples say: utilisation spread, memory, clock."""
        if not self.samples:
            return {
                "available": False,
                "reason": ("nvidia-smi/rocm-smi not found" if self._probe is None
                           else f"no samples ({self.errors} failed readings)"),
            }

        def values(key):
            return [s[key] for s in self.samples if s.get(key) is not None]

        util = values("util_percent")
        mem = values("mem_used_mib")
        total = values("mem_total_mib")
        clock = values("clock_sm_mhz")
        out = {
            "available": True,
            "samples": len(self.samples),
            "errors": self.errors,
            "seconds": (self.samples[-1]["at"] - self.samples[0]["at"]
                        if len(self.samples) > 1 else 0.0),
            "name": self.samples[-1].get("name"),
        }
        if util:
            out["util_mean"] = sum(util) / len(util)
            out["util_min"] = min(util)
            out["util_max"] = max(util)
        if mem:
            out["mem_mean_mib"] = sum(mem) / len(mem)
            out["mem_max_mib"] = max(mem)
        if total:
            out["mem_total_mib"] = max(total)
        if clock:
            out["clock_max_mhz"] = max(clock)
        return out

    def describe(self) -> str:
        """One line for the report, or why there is no line."""
        s = self.summary()
        if not s.get("available"):
            return f"gpu: no reading ({s.get('reason')})"
        parts = [f"util mean {s['util_mean']:.0f}% "
                 f"(min {s['util_min']}, max {s['util_max']})"] if "util_mean" in s else \
                ["util unavailable"]
        if "mem_mean_mib" in s:
            total = s.get("mem_total_mib")
            mem = f"vram {s['mem_mean_mib'] / 1024:.1f}"
            if total:
                mem += f"/{total / 1024:.1f} GiB"
            mem += f" (peak {s['mem_max_mib'] / 1024:.1f})"
            parts.append(mem)
        if "clock_max_mhz" in s:
            parts.append(f"sm clock max {s['clock_max_mhz']:.0f} MHz")
        parts.append(f"{s['samples']} samples over {s['seconds']:.0f}s")
        return "gpu: " + "; ".join(parts)
