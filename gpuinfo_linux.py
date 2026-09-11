"""GPU detection for Linux — nvidia-smi instead of nvapi64.dll.

Replaces the Windows gpuinfo.py that uses nvapi64.dll with a subprocess call
to nvidia-smi. Returns the same interface: probe() -> list[dict], describe() -> str.
"""

from __future__ import annotations

import json
import subprocess
import sys


def probe() -> list[dict]:
    """Detect NVIDIA GPUs via nvidia-smi.

    Returns a list of dicts, one per GPU:
        {"index": int, "name": str, "driver_version": str}

    When nvidia-smi is not available or fails, returns a single placeholder
    entry so the rest of the program does not crash.
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,driver_version",
             "--format=json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return _fallback()
        data = json.loads(result.stdout)
        gpus = data.get("gpus", [])
        if not gpus:
            return _fallback()
        return gpus
    except (FileNotFoundError, subprocess.TimeoutExpired,
            json.JSONDecodeError, OSError):
        return _fallback()


def _fallback() -> list[dict]:
    """Return a single placeholder GPU entry."""
    return [{
        "index": 0,
        "name": "NVIDIA GPU (nvidia-smi unavailable)",
        "driver_version": "?",
    }]


def describe(gpus: list[dict]) -> str:
    """Return a short string describing the detected GPUs.

    Example: "GPU 0: RTX 5070 Ti (driver 570.86.15)"
    """
    if not gpus:
        return ""
    return "; ".join(
        f"GPU {g['index']}: {g['name']} "
        f"(driver {g.get('driver_version', '?')})"
        for g in gpus
    )


if __name__ == "__main__":
    gpus = probe()
    print(describe(gpus) or "no GPU detected")
    for g in gpus:
        print(f"  index={g['index']}  name={g['name']}  "
              f"driver={g.get('driver_version', '?')}")