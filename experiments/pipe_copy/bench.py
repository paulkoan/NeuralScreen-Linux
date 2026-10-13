#!/usr/bin/env python3
"""How long does one frame take to copy out of an already-stocked pipe?

This is the `read` half of the capture split — the part of a grab that is ours —
measured on its own, with no compositor, no GStreamer and no worker in the way:
a writer thread keeps an `os.pipe` full of a frame, and the reader drains it
with the *same loop* `minimal/capture_wayland.py` uses (`read1` until the frame
is complete) and times itself.

Why it exists: the project has quoted "13-19ms to copy a 14.7MB frame out of a
stocked pipe (1108 MB/s)" since round 14, and that number had no script behind
it. It is also the number the capture split's `read` half should agree with, so
a disagreement is a finding rather than a rounding error to argue about.

    experiments/pipe_copy/bench.py [rounds]

Needs numpy only to build the payload; writes nothing and touches nothing
outside its own process.
"""

from __future__ import annotations

import os
import sys
import threading
import time

import numpy as np

# 2560x1440 is the GeForce Now target's frame; 1280x720 and 128x128 are the two
# sizes the gate uses to separate per-pixel cost from fixed cost.
SIZES = [(2560, 1440), (1280, 720), (128, 128)]


def _writer(fd: int, payload: bytes, stop: threading.Event) -> None:
    """Keep the pipe stocked: rewrite the frame until told to stop.

    Blocking here is the point — a full pipe is what "stocked" means, and the
    reader must never see an empty one.
    """
    view = memoryview(payload)
    while not stop.is_set():
        try:
            os.write(fd, view)
        except (BrokenPipeError, OSError):
            return


def _drain(fd: int, need: int) -> float:
    """Read exactly `need` bytes the way the capture does; return seconds.

    Buffered, because that is what `subprocess.PIPE` hands the capture — and
    `read1` is a `BufferedReader` method, so an unbuffered `FileIO` has no
    `read1` at all. Using `read` here instead would block for the whole request
    and swallow the split, which is the bug round 14 found and fixed.
    """
    buf = os.fdopen(fd, "rb")
    got = 0
    chunks: list[bytes] = []
    t0 = time.monotonic()
    while got < need:
        chunk = buf.read1(need - got)
        if not chunk:
            break
        chunks.append(chunk)
        got += len(chunk)
    dt = time.monotonic() - t0
    buf.close()
    return dt


def main(rounds: int = 9) -> int:
    print(f"rounds per size: {rounds}   python {sys.version.split()[0]}   "
          f"numpy {np.__version__}")
    for width, height in SIZES:
        need = width * height * 4
        payload = bytes(np.random.default_rng(1).integers(0, 256, need, dtype=np.uint8))
        times = []
        for _ in range(rounds):
            read_fd, write_fd = os.pipe()
            stop = threading.Event()
            threading.Thread(target=_writer, args=(write_fd, payload, stop),
                             daemon=True).start()
            time.sleep(0.05)          # let the writer get ahead of the reader
            times.append(_drain(read_fd, need))
            stop.set()
            os.close(write_fd)
        mb = need / 1e6
        best = min(times)
        median = sorted(times)[len(times) // 2]
        print(f"  {width}x{height}  {mb:6.2f} MB   best {1000 * best:6.2f}ms   "
              f"median {1000 * median:6.2f}ms   ->  {mb / median:6.0f} MB/s")
        print(f"      every round: {[round(1000 * t, 2) for t in times]} ms")
    print()
    print("Read this against the capture split's `read` half: a 2560x1440 grab "
          "can be no faster than this, and a `read` far above it means the "
          "bytes arrived slowly rather than being drained at memory speed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 9))
