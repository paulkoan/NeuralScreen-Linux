# The saved burst — what `--save-burst` writes and how to read it

A single `--save-before`/`--save-after` pair is one frame looked at twice. It cannot
answer the question the history half of the port asks: what the motion field was doing
across the burst, and whether the pass's output tracks it. That needs every frame's
colour on both sides of the pass and the motion field that went with each one, in a
layout a downstream run can open without knowing which run made it.

`python -m minimal ... --save-burst DIR` writes that. The mechanism lives in
`minimal/loop.py` (`BurstWriter`); the reader every downstream analysis should use is
`tools/read_burst.py`.

## Layout

```
DIR/
  manifest.json                        what is in here, and the resolution it was taken at
  frames/
    frame_000000_before.png            the colour frame the pass was given
    frame_000000_after.png             the colour frame it returned
    frame_000001_before.png
    frame_000001_after.png
    ...
  motion/
    frame_000000_motion.npz            `numpy.load(p)["motion"]`, float16 HxWx2
    frame_000001_motion.npz
    ...
```

Frame indices are zero-based and contiguous up to `frames_saved - 1`. A frame whose
input was not kept is not written; `frames_saved` counts what is actually on disk, and
`frames_dropped` counts frames the writer's queue could not accept.

## manifest.json

```json
{
  "format": "neuralscreen-burst/1",
  "frames_saved": 120,
  "frames_dropped": 0,
  "width": 2560,
  "height": 1440,
  "frames_dir": "frames",
  "motion_dir": "motion",
  "frame_pattern": "frame_{index:06d}_before.png / frame_{index:06d}_after.png",
  "motion_pattern": "frame_{index:06d}_motion.npz",
  "motion_shape": [1440, 2560, 2],
  "motion_dtype": "float16",
  "seconds": 14.2,
  "note": "...",
  "errors": [],
  "capture_split": {"wait_ms": 0.1, "read_ms": 27.4, "frames": 120}
}
```

* `width`/`height` are the **capture** resolution — the size the colour frames are.
  The motion field is at the worker's motion size (`motion_shape`), which at work scale
  1.0 is the same as the frame; the manifest records it so a reader never has to assume.
* `capture_split` is present only when the source splits its own grab (portal/window
  captures). A synthetic source has no "waiting for the frame" half, and the key is left
  out rather than filled with zeros.
* `errors` is a list of strings; a non-empty list means some frames failed to encode and
  the burst is shorter than the run.

## Reading it

```python
from tools.read_burst import load_burst, load_manifest

manifest = load_manifest("runs/done/r.../burst")
for index, before, after, motion in load_burst("runs/done/r.../burst"):
    # before/after: HxWx3 uint8 (alpha dropped; the frames are opaque)
    # motion:      HxWx2 float16, the field sent with that frame
    ...
```

Or from the shell, as a sanity check:

```sh
tools/read_burst.py runs/done/r2026-10-27-f/burst
tools/read_burst.py runs/done/r2026-10-27-f/burst --index 0
```

`load_burst` refuses a burst whose manifest and directory disagree: a manifest that
promises 120 frames and a directory with 12 would otherwise produce a mean over 12 and
call it the burst. It raises `BurstError` naming the missing file.

## Why PNG and npz, and why a thread

* PNG for the colour: lossless, and `tools/frame_diff.py` already reads PNG, so an
  analysis can diff a burst's frames with the same tool that diffs a single pair.
* npz for the motion: a zero field compresses to a few KB; as raw float16 at 1440p it is
  14.7 MB per frame. `numpy.savez_compressed` keeps the file small and the array typed.
* The writer encodes on its own thread with a bounded queue. A PNG encode at 1440p costs
  ~40 ms and the capture loop runs at ~120 ms/frame; saving inline would inflate the
  `capture split` a live run exists to measure. A frame the queue cannot accept is
  dropped and counted, never waited for.

## What a downstream run gets that it did not have before

Before this, the only saved evidence of a run was one before/after pair. That is enough
to say the pass changed pixels; it is not enough to say *what the motion was doing* when
it did. The burst keeps the field per frame, so the history half's reprojection and the
five-tap filter can finally be measured against a real field rather than the zero field
every fixture run has sent.
