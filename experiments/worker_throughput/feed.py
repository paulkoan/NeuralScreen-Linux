#!/usr/bin/env python3
"""Feed the worker a stream as fast as it will take one, and time it.

Every number this project has for the pipeline includes the client: a strictly
serial loop that sends a frame and then waits for that frame's result. That is a
round-trip measurement, not a throughput one, and the two differ by exactly the
thing being investigated. This is the throughput one — no per-frame handshake, no
capture, no display, and no reading of results as they arrive (the worker's
stdout goes to /dev/null, so it never blocks on a result nobody is taking).

The stream is built with the client's own code — minimal.worker.stream_header and
protocol.send_frame — so it is byte-identical to what a real run sends rather
than a second implementation that might be rejected on frame 0. A frame is 8
bytes per pixel in (RGBA8 colour + two float16 motion channels) and 4 bytes per
pixel back, so at the measured ~1.1 GB/s of a pipe the floor per frame is about
10ms at 1280x720 and 40ms at 2560x1440 — whatever the loop does around it.

Startup is not what we are measuring (NGX init is a second or two), so every run
happens twice, with N frames and with 2N, and the per-frame cost is the
difference over N: the startup and the exit cancel exactly.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from minimal.loop import DEFAULT_PARAMS  # noqa: E402
from minimal.worker import (default_launcher, stream_header, work_size,  # noqa: E402
                            worker_env)
from protocol import send_frame  # noqa: E402

NATIVE = REPO / "native"

# The worker's own --test harness uses two warm-up frames; matching it keeps the
# two paths comparable and keeps the first-frame NGX cost out of the run.
WARMUP = 2


class Sink:
    """Stands in for the Popen object: send_frame only ever touches .stdin."""

    def __init__(self, stream):
        self.stdin = stream


def bytes_per_frame(w: int, h: int) -> int:
    """What actually crosses the pipe, both ways, for one frame."""
    return w * h * 8 + w * h * 4


def run_once(frames: int, w: int, h: int, bypass: bool, log: Path):
    ww, wh = work_size(w, h, 1.0)
    with open(log, "wb") as errlog:
        proc = subprocess.Popen(
            default_launcher(),
            cwd=str(NATIVE),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,   # nobody is reading results: that is the point
            stderr=errlog,
            env=worker_env(),
        )
        assert proc.stdin is not None
        proc.stdin.write(stream_header(ww, wh, WARMUP, DEFAULT_PARAMS))
        proc.stdin.flush()

        sink = Sink(proc.stdin)
        rgba = np.zeros((wh, ww, 4), dtype=np.uint8)
        motion = np.zeros((wh, ww, 2), dtype=np.float16)

        started = time.monotonic()
        for i in range(frames):
            send_frame(sink, i, rgba, motion, reset=(i == 0), pts=0, bypass=bypass)
        proc.stdin.close()
        try:
            rc = proc.wait(timeout=180)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = -9
        elapsed = time.monotonic() - started
    return elapsed, rc


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="feed.py", description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--size", default="2560x1440", help="WxH, the frame the worker is handed")
    ap.add_argument("--frames", type=int, default=30,
                    help="frames in the short run; the long run gets twice this")
    ap.add_argument("--bypass", action="store_true", help="NR off: skip NGX entirely")
    ap.add_argument("--log", default="/tmp/nsb_feed_worker.log")
    args = ap.parse_args(argv)

    try:
        w, h = (int(v) for v in args.size.lower().split("x"))
    except ValueError:
        print(f"bad --size: {args.size!r} is not WxH", file=sys.stderr)
        return 2

    log = Path(args.log)
    n = args.frames
    print(f"  size: {w}x{h}   frames: {n} then {2 * n}   bypass: {args.bypass}")
    print(f"  bytes per frame across the pipe: {bytes_per_frame(w, h) / 1e6:.1f} MB "
          f"(8/pixel in, 4/pixel back)", flush=True)

    t_short, rc1 = run_once(n, w, h, args.bypass, log)
    print(f"  {n:3d} frames: {t_short:7.3f}s   (worker exit {rc1})", flush=True)
    t_long, rc2 = run_once(2 * n, w, h, args.bypass, log)
    print(f"  {2 * n:3d} frames: {t_long:7.3f}s   (worker exit {rc2})", flush=True)

    if rc1 != 0 or rc2 != 0:
        print(f"  the worker did not exit cleanly ({rc1}, {rc2}) — the log is {log}",
              file=sys.stderr)

    delta = t_long - t_short
    if delta <= 0:
        print("  the longer run was not slower — the difference cannot give a "
              "per-frame cost. Nothing to report.", file=sys.stderr)
        return 1

    per_frame_ms = 1000 * delta / n
    fps = 1000 / per_frame_ms
    floor_ms = bytes_per_frame(w, h) / 1.1e6     # ~1.1 GB/s pipe, measured here
    ratio = per_frame_ms / floor_ms
    print()
    print(f"  derived per frame: {per_frame_ms:.2f} ms  =  {fps:.1f} fps")
    print(f"  the pipe alone would be: {floor_ms:.1f} ms/frame at ~1.1 GB/s "
          f"= {1000 / floor_ms:.1f} fps")
    print(f"  this run is {ratio:.2f}x the pipe floor")
    print()
    # There are only two possibilities, and the ratio says which. The pipe is a
    # floor, not a target: a run cannot come in *under* it, so being near it means
    # the pipe is the constraint and being well above it means something else is
    # — and the only something else in this process is the worker.
    if ratio <= 1.3:
        print("  RESULT: AT THE PIPE'S RATE. With no handshake and no client in "
              "the way, the")
        print("  worker saturates the pipe — so the pipeline's much lower rate is "
              "the client's")
        print("  serial loop, and a faster transport (mmap_bridge, proven ~4x one "
              "way) lifts")
        print("  this ceiling directly.")
    else:
        print("  RESULT: THE WORKER IS THE WALL. It took "
              f"{ratio:.1f}x longer than the pipe")
        print("  needs for the same bytes, with nothing else in the process, so it "
              "is not the")
        print("  handshake, not the transport and not the client. A shared-memory "
              "transport")
        print("  would save the pipe's own share and no more.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))