#!/usr/bin/env python3
"""Feed the worker a stream as fast as it will take one, and time it.

Every number this project has for the pipeline includes the client: a strictly
serial loop that sends a frame and then waits for that frame's result. That is a
round-trip measurement, not a throughput one, and the two differ by exactly the
thing being investigated. This is the throughput one — no per-frame handshake, no
capture, no display, and no reading of results as they arrive (the worker's stdout
is discarded, so it never blocks on a result nobody is taking).

The stream is built with the client's own code — minimal.worker.stream_header and
protocol.send_frame — so the worker gets a byte-identical stream rather than a
second implementation of the protocol.

Three things this had to learn the hard way:

* **A warm-up pass first.** The first `wine` invocation pays the cold prefix and
  wineserver start — seconds of it — and in the first version of this that landed
  on a measured pass: 60 frames came in *faster* than 30, which is impossible, and
  the derived figure was meaningless.
* **Three points, not two.** A line through two points fits anything, which the
  size sweep already taught. The per-frame cost is the slope of a least-squares
  fit through N, 2N and 3N frames; the intercept is the startup, and the residuals
  and R^2 say whether the fit is worth reading at all.
* **A measured pipe rate.** The floor the verdict compares against has to be
  measured on the machine it is talking about, by writing to a reader that does
  nothing else.
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


def pipe_rate_mbs(mb: int = 200) -> float:
    """What a pipe sustains here, measured rather than assumed.

    The figure this project has been quoting (1.1 GB/s) came from a Python-side
    copy on another box, and the first version of this tool took it on trust. The
    verdict turns on the comparison, so it has to be measured on this machine, by
    a reader that does nothing else.
    """
    proc = subprocess.Popen(["cat"], stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL)
    assert proc.stdin is not None
    block = bytes(1 << 20)
    started = time.monotonic()
    for _ in range(mb):
        proc.stdin.write(block)
    proc.stdin.close()
    proc.wait(timeout=120)
    elapsed = time.monotonic() - started
    return mb / elapsed if elapsed > 0 else float("nan")


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
            rc = proc.wait(timeout=300)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = -9
        elapsed = time.monotonic() - started
    return elapsed, rc


def fit(points: list[tuple[int, float]]):
    """Least squares of seconds against frames. Returns (ms/frame, startup s, r2)."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res / ss_tot if ss_tot else float("nan")
    return slope * 1000.0, intercept, r2


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="feed.py",
                                 description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--size", default="2560x1440",
                    help="WxH, the frame the worker is handed")
    ap.add_argument("--frames", type=int, default=25,
                    help="the short run; the others get 2x and 3x this")
    ap.add_argument("--bypass", action="store_true", help="NR off: skip NGX entirely")
    ap.add_argument("--log", default="/tmp/nsb_feed_worker.log")
    args = ap.parse_args(argv)

    try:
        w, h = (int(v) for v in args.size.lower().split("x"))
    except ValueError:
        print(f"bad --size: {args.size!r} is not WxH", file=sys.stderr)
        return 2

    log = Path(args.log)
    bpf = bytes_per_frame(w, h)
    n = args.frames
    runs = [n, 2 * n, 3 * n]

    print(f"  size: {w}x{h}   bypass: {args.bypass}")
    print(f"  bytes per frame across the pipe: {bpf / 1e6:.1f} MB "
          f"(8/pixel in, 4/pixel back)", flush=True)

    rate = pipe_rate_mbs()
    floor_ms = bpf / (rate * 1000.0)
    print(f"  pipe rate on this box: {rate:.0f} MB/s  ->  floor "
          f"{floor_ms:.1f} ms/frame  ({1000 / floor_ms:.1f} fps)", flush=True)

    print("\n  warm-up pass (its time is the cold start and is not measured):",
          flush=True)
    t_warm, rc_warm = run_once(5, w, h, args.bypass, log)
    print(f"    5 frames: {t_warm:7.3f}s   (worker exit {rc_warm})", flush=True)

    points = []
    for frames in runs:
        elapsed, rc = run_once(frames, w, h, args.bypass, log)
        print(f"  {frames:4d} frames: {elapsed:7.3f}s   (worker exit {rc})", flush=True)
        if rc != 0:
            print(f"    the worker exited {rc}; its stderr is {log}", file=sys.stderr)
        points.append((frames, elapsed))

    slope_ms, startup_s, r2 = fit(points)
    fps = 1000.0 / slope_ms if slope_ms > 0 else float("nan")
    print()
    print(f"  fit over {len(points)} points: {slope_ms:.2f} ms/frame  =  "
          f"{fps:.1f} fps   (startup {startup_s:.2f}s, R^2 {r2:.4f})")
    for frames, elapsed in points:
        predicted = startup_s + (slope_ms / 1000.0) * frames
        print(f"    {frames:4d} frames: actual {elapsed:7.3f}s  fit says "
              f"{predicted:7.3f}s  off by {elapsed - predicted:+.3f}s")
    print(f"  the bytes alone, at this box's pipe rate: {floor_ms:.1f} ms/frame")
    print(f"  this is {slope_ms / floor_ms:.2f}x that")
    print()

    if not (r2 > 0.98):
        print(f"  RESULT: NO USABLE FIT (R^2 {r2:.3f}). The points do not lie on a "
              f"line, so the")
        print("  slope is not a per-frame cost — the startup is not constant, or "
              "something else")
        print("  changed between runs. Nothing here should be quoted; re-run it.")
        return 1

    # The pipe is a floor, not a target: bytes cannot cross faster than it
    # allows, so a slope near the floor means the pipe is the constraint, and a
    # slope well above it means something else in the process is.
    if slope_ms / floor_ms <= 1.3:
        print("  RESULT: AT THE PIPE'S RATE. With no handshake and no client in "
              "the way the")
        print("  worker keeps up with its own pipe, so the pipeline's much lower "
              "rate is the")
        print("  client's serial loop — and a faster transport (mmap_bridge, proven "
              "~4x one")
        print("  way) lifts this ceiling directly.")
    else:
        print(f"  RESULT: THE WORKER IS THE WALL ({slope_ms / floor_ms:.1f}x the "
              f"pipe). It took")
        print("  longer than the bytes need with nothing else in the process, so it "
              "is not the")
        print("  handshake, not the transport and not the client. A shared-memory")
        print("  transport saves the pipe's own share and no more.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))