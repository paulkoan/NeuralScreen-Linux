"""Is the client's frame write limited by Python, or by the reader?

The gate reports `send` at 88-112ms a frame at 2560x1440, which is 29.5MB of
colour+zero-motion — about 330 MB/s. Python writes 1MB blocks to a pipe at
7 GB/s on this box, so 330 MB/s needs explaining: either our own write path is
slow at frame size, or the write is gated by whoever is reading.

`cat > /dev/null` is the fastest possible reader. If a frame write into cat is
fast, then the worker's read is the gate and no client change fixes it. If it is
slow, it is ours.

This runs on the analysis box and needs no GPU, no Wine and no worker.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from minimal.worker import work_size  # noqa: E402
from protocol import send_frame  # noqa: E402


class Sink:
    def __init__(self, stream):
        self.stdin = stream


def time_writes(w: int, h: int, frames: int, reader_cmd: list[str]):
    ww, wh = work_size(w, h, 1.0)
    rgba = np.zeros((wh, ww, 4), dtype=np.uint8)
    motion = np.zeros((wh, ww, 2), dtype=np.float16)
    bpf = w * h * 8

    proc = subprocess.Popen(reader_cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL)
    assert proc.stdin is not None
    sink = Sink(proc.stdin)
    # One warm frame, so the first write does not carry the pipe's setup.
    send_frame(sink, 0, rgba, motion, reset=True, pts=0)

    started = time.monotonic()
    for i in range(frames):
        send_frame(sink, i, rgba, motion, reset=False, pts=i)
    elapsed = time.monotonic() - started
    proc.stdin.close()
    proc.wait(timeout=60)

    per_frame_ms = 1000 * elapsed / frames
    return per_frame_ms, bpf / 1e6 / (elapsed / frames)


def main() -> int:
    print("  the client's write path, with the fastest reader there is")
    print(f"  {'reader':<18}{'frame':>10}{'ms/frame':>10}{'MB/s':>10}")
    for w, h in ((1280, 720), (2560, 1440)):
        for name, cmd in (("cat>/dev/null", ["cat"]),
                          ("dd bs=1M", ["dd", "of=/dev/null", "bs=1M",
                                        "status=none"])):
            ms, mbs = time_writes(w, h, 20, cmd)
            print(f"  {name:<18}{f'{w}x{h}':>10}{ms:>10.2f}{mbs:>10.0f}")

    print()
    print("  for reference, the 1440p pipeline's `send` was 88-112ms a frame.")
    print("  a frame is 8 bytes/pixel: 29.5MB at 2560x1440, half of it the")
    print("  zero motion field this MVP sends because it has no real vectors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())