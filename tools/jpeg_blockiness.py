#!/usr/bin/env python3
"""Measure JPEG blockiness and edge coherence in a frame pair.

Edge-filter energy is the wrong instrument for "did we restore a compressed
frame": JPEG ringing *raises* edge energy, so a sharper-looking edge histogram
can mean more artifacts, not more detail. What compression actually leaves is
an 8x8 grid, so measure that directly.

blockiness  = mean |neighbour difference| across 8-pixel boundaries divided by
              the same across interior pixels. A clean frame has no preference
              for the grid -> ratio ~= 1.0. JPEG at q20 leaves a visible grid
              -> ratio > 1.0. Restoring detail should lower it toward 1.0.

coherence   = fraction of strong gradients that continue along their axis.
              Compression breaks edges into blocks and makes them incoherent;
              real edges stay coherent. Unlike raw edge energy, this rises when
              detail is genuinely recovered.

Decoding goes through ffmpeg to raw rgb24 rather than PIL: the repo venv has no
PIL and PYTHONPATH injects a 3.14 site-packages whose _imaging will not load in
a 3.13 interpreter. ffmpeg + numpy.fromfile has no such coupling.

usage: jpeg_blockiness.py BEFORE.png AFTER.png
"""
import subprocess
import sys

import numpy as np


def load(path):
    """Decode any image ffmpeg understands into a float64 HxWx3 array."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True)
    w, h = [int(x) for x in probe.stdout.strip().split(",")[:2]]
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-pix_fmt", "rgb24",
         "-f", "rawvideo", "-"],
        capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.uint8)
    if a.size != w * h * 3:
        sys.exit("%s: expected %d bytes, got %d" % (path, w * h * 3, a.size))
    return a.reshape(h, w, 3).astype(np.float64)


def blockiness(a):
    """8x8 boundary-vs-interior neighbour-difference ratio."""
    g = a.mean(axis=2)
    dh = np.abs(np.diff(g, axis=1))   # d[y, x] = |g[y, x+1] - g[y, x]|
    dv = np.abs(np.diff(g, axis=0))
    cols = np.arange(dh.shape[1])
    rows = np.arange(dv.shape[0])
    bx = dh[:, cols % 8 == 7].mean()
    ix = dh[:, cols % 8 != 7].mean()
    by = dv[rows % 8 == 7, :].mean()
    iy = dv[rows % 8 != 7, :].mean()
    return 0.5 * (bx / ix + by / iy)


def edge_coherence(a, thresh=12.0):
    """Fraction of strong gradients that continue coherently along their axis."""
    g = a.mean(axis=2)
    gx = np.abs(np.diff(g, axis=1))[:-1, :]
    gy = np.abs(np.diff(g, axis=0))[:, :-1]
    gx2 = np.abs(np.diff(g, axis=1))[1:, :]
    gy2 = np.abs(np.diff(g, axis=0))[:, 1:]
    strong = (gx > thresh) | (gy > thresh)
    if not strong.any():
        return 0.0
    cont = ((gx > thresh) & (gx2 > thresh * 0.6)) | ((gy > thresh) & (gy2 > thresh * 0.6))
    return float(cont[strong].mean())


def detail_ratio(a):
    """Global variance over 3x3-blurred variance: high = detail survives."""
    g = a.mean(axis=2)
    bl = np.zeros_like(g)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            bl += np.roll(np.roll(g, dy, 0), dx, 1)
    bl /= 9.0
    return float(g.var() / max(bl.var(), 1e-9))


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    bpath, apath = sys.argv[1], sys.argv[2]
    b, a = load(bpath), load(apath)
    if b.shape != a.shape:
        sys.exit("size mismatch: %s vs %s" % (b.shape, a.shape))

    print("before %s" % bpath)
    print("after  %s" % apath)
    print("size   %dx%d" % (b.shape[1], b.shape[0]))
    print()
    for name, arr in (("before", b), ("after ", a)):
        print("%s  blockiness %.4f   coherence %.4f   detail %.4f"
              % (name, blockiness(arr), edge_coherence(arr), detail_ratio(arr)))
    print()

    d = np.abs(a - b).max(axis=2)
    print("mean abs diff per channel  %s" % np.abs(a - b).mean(axis=(0, 1)).round(3))
    print("changed pixels >2: %.2f%%   >8: %.2f%%"
          % (100.0 * (d > 2).mean(), 100.0 * (d > 8).mean()))
    print()

    bl_b, bl_a = blockiness(b), blockiness(a)
    co_b, co_a = edge_coherence(b), edge_coherence(a)
    verdict = []
    if bl_a < bl_b * 0.99:
        verdict.append("blockiness down %.1f%% (grid reduced)" % (100 * (bl_b - bl_a) / bl_b))
    elif bl_a > bl_b * 1.01:
        verdict.append("blockiness up %.1f%% (grid worse)" % (100 * (bl_a - bl_b) / bl_b))
    else:
        verdict.append("blockiness flat")
    if co_a > co_b * 1.01:
        verdict.append("coherence up %.1f%% (edges better)" % (100 * (co_a - co_b) / co_b))
    elif co_a < co_b * 0.99:
        verdict.append("coherence down %.1f%% (edges worse)" % (100 * (co_b - co_a) / co_b))
    else:
        verdict.append("coherence flat")
    print("VERDICT: " + "; ".join(verdict))


if __name__ == "__main__":
    main()
