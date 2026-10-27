#!/usr/bin/env python3
"""Read a saved burst directory into frames, colour and motion.

    tools/read_burst.py BURST_DIR [--index N]

The pipeline's `--save-burst DIR` writes what a live session produced in a form
a downstream analysis run can open without knowing the run that made it:

    DIR/manifest.json          what is in here, and the resolution it was taken at
    DIR/frames/frame_000000_before.png   the colour frame the pass was given
    DIR/frames/frame_000000_after.png    the colour frame it returned
    DIR/motion/frame_000000_motion.npz   the motion field sent with that frame
                                        (`numpy.load(...)["motion"]`, float16 HxWx2)

This module is the reader for that layout. It is deliberately the only place
that knows the file names: a downstream run imports `load_burst()` and gets
arrays back, so a layout change is one edit here rather than in every analysis.
It also refuses a burst whose manifest disagrees with the files on disk — a
manifest that promises 120 frames and a directory with 12 is worse than no
manifest, because it reads as a measurement.

Exit codes: 0 read, 2 the directory is not a burst or is inconsistent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

FORMAT = "neuralscreen-burst/1"


class BurstError(Exception):
    """The directory is not a burst, or the manifest does not match it."""


def load_manifest(root: str | Path) -> dict:
    """The burst's manifest, checked for the format this reader understands."""
    root = Path(root)
    path = root / "manifest.json"
    if not path.is_file():
        raise BurstError(f"{root} has no manifest.json — not a burst")
    try:
        manifest = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise BurstError(f"{path} is not JSON: {exc}") from exc
    fmt = manifest.get("format")
    if fmt != FORMAT:
        raise BurstError(
            f"{path} says format {fmt!r}; this reader reads {FORMAT!r}")
    return manifest


def _png(path: Path) -> np.ndarray:
    """Load a PNG as an HxWx3 uint8 array, without requiring a video driver."""
    import pygame
    surface = pygame.image.load(str(path))
    # surfarray gives WxH; the pipeline's frames are HxW, so transpose back.
    return np.asarray(pygame.surfarray.array3d(surface)).transpose(1, 0, 2)


def load_burst(root: str | Path, indices: list[int] | None = None):
    """Yield ``(index, before, after, motion)`` for a saved burst.

    before/after are HxWx3 uint8 colour frames (the alpha channel is dropped —
    the pipeline's frames are opaque RGBA and PNG keeps them that way), motion is
    the float16 HxWx2 field that was sent with the frame. ``indices`` selects a
    subset; the default is every frame the manifest names.

    Raises BurstError if the manifest and the directory disagree, rather than
    yielding a short or padded sequence: a silently short burst is a wrong
    measurement.
    """
    root = Path(root)
    manifest = load_manifest(root)
    saved = int(manifest["frames_saved"])
    width, height = manifest.get("width"), manifest.get("height")
    frames_dir = root / manifest.get("frames_dir", "frames")
    motion_dir = root / manifest.get("motion_dir", "motion")

    order = list(range(saved)) if indices is None else list(indices)
    for index in order:
        if not 0 <= index < saved:
            raise BurstError(f"frame {index} is outside 0..{saved - 1}")
        before_png = frames_dir / f"frame_{index:06d}_before.png"
        after_png = frames_dir / f"frame_{index:06d}_after.png"
        motion_npz = motion_dir / f"frame_{index:06d}_motion.npz"
        for path in (before_png, after_png, motion_npz):
            if not path.is_file():
                raise BurstError(
                    f"manifest says {saved} frames but {path} is missing — "
                    f"the burst is incomplete")
        before = _png(before_png)
        after = _png(after_png)
        with np.load(motion_npz) as data:
            motion = data["motion"]
        if width and height and before.shape[:2] != (height, width):
            raise BurstError(
                f"frame {index} is {before.shape[:2]}, manifest says "
                f"{(height, width)}")
        yield index, before, after, motion


def _summary(manifest: dict) -> str:
    split = manifest.get("capture_split") or {}
    split_text = ""
    if split:
        split_text = (f"  capture split wait {split.get('wait_ms')}ms "
                      f"read {split.get('read_ms')}ms")
    return (f"{manifest['frames_saved']} frames, "
            f"{manifest.get('width')}x{manifest.get('height')}"
            f"{split_text}")


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:]]
    index = None
    if "--index" in args:
        i = args.index("--index")
        try:
            index = int(args[i + 1])
        except (IndexError, ValueError):
            print("--index needs a number", file=sys.stderr)
            return 2
        del args[i:i + 2]
    if len(args) != 1:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2

    root = Path(args[0])
    try:
        manifest = load_manifest(root)
        print(f"burst: {root} — {_summary(manifest)}")
        if manifest.get("frames_dropped"):
            print(f"  dropped: {manifest['frames_dropped']}")
        for i, before, after, motion in load_burst(
                root, [index] if index is not None else None):
            delta = float(np.abs(after.astype(np.int16)
                                 - before.astype(np.int16)).mean())
            print(f"  frame {i}: colour {before.shape[1]}x{before.shape[0]}, "
                  f"motion {motion.shape} {motion.dtype}, "
                  f"mean |after-before| {delta:.2f}/255")
    except BurstError as exc:
        print(f"not a readable burst: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
