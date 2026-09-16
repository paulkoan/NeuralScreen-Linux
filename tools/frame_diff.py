#!/usr/bin/env python3
"""Compare a before/after frame pair and say whether the pass did anything.

    tools/frame_diff.py BEFORE.png AFTER.png

Exit codes:
  0  the after frame differs from the before frame, blank-free, meaningfully
  1  it does not — byte-identical, blank, or below the floor
  3  the pair could not be read or does not line up

The floor exists because "different" is too weak on its own. A no-op pass that
returns the input, and a pass that writes a black frame, both exit 0 and both
produce a file. The only way to tell whether work happened is to measure it.
"""

from __future__ import annotations

import sys

import cv2
import numpy as np

# Below this mean absolute difference (0-255 scale) the frames are, for the
# purposes of this gate, unchanged. Byte-identical is caught separately.
FLOOR = 0.05

# A frame whose channel standard deviation is under this is a flat fill, not a
# picture. A black capture and a failed pass both look like this.
BLANK_STD = 0.5


def load(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        print(f"could not read {path}")
        raise SystemExit(3)
    return img[:, :, ::-1].astype(np.float32)      # BGR -> RGB


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: frame_diff.py BEFORE.png AFTER.png", file=sys.stderr)
        return 3

    a, b = load(argv[1]), load(argv[2])
    if a.shape != b.shape:
        print(f"shape mismatch: before={a.shape} after={b.shape}")
        return 3

    mad = float(np.abs(a - b).mean())
    mse = float(((a - b) ** 2).mean())
    psnr = float("inf") if mse == 0 else 10.0 * np.log10((255.0 ** 2) / mse)
    before_blank = bool(a.std() < BLANK_STD)
    after_blank = bool(b.std() < BLANK_STD)
    identical = bool(np.array_equal(a, b))

    print(f"size              {a.shape[1]}x{a.shape[0]}")
    print(f"mean abs diff     {mad:.4f}  (0 = byte-identical)")
    print(f"p99 abs diff      {float(np.percentile(np.abs(a - b), 99)):.2f}")
    print(f"PSNR              {psnr if psnr != float('inf') else 'inf'}")
    print(f"before is blank   {before_blank}")
    print(f"after is blank    {after_blank}")
    print(f"after == before   {identical}")

    if identical:
        print("VERDICT the pass returned the input unchanged")
        return 1
    if after_blank:
        print("VERDICT the output is blank")
        return 1
    if mad < FLOOR:
        print(f"VERDICT changed by only {mad:.4f}/255 — too little to be a pass")
        return 1
    print(f"VERDICT the pass changed the frame (mean abs diff {mad:.4f}/255)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
