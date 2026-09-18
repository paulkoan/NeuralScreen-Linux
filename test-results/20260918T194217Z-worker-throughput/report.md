# Worker throughput, no client in the way — 20260918T194217Z

**RESULT: NO USABLE FIT (R^2 0.745). The points do not lie on a line, so the**

## What this is

The worker fed a byte-identical stream as fast as it will take one, with
its results discarded rather than read, so nothing in the process is
waiting on a round trip. Every other number this project has includes
the client's strictly serial loop — send a frame, wait for that frame —
which is what this removes.

Each size runs a discarded warm-up pass first, then N, 2N and 3N frames.
The per-frame cost is the slope of a least-squares fit through those three
points; the intercept is the startup. Three points rather than two because
a line through two points fits anything — and because the first version of
this used two, and the cold wineserver start landed on one of them: 60
frames came in faster than 30, which is impossible. The fit's R^2 and
residuals are printed, and a poor fit is refused rather than quoted.

The pipe floor is measured on this box in the same run, not assumed: 8
bytes per pixel in (RGBA8 colour plus two float16 motion channels) and 4
bytes per pixel back.

## 1280x720

```
  size: 1280x720   bypass: False
  bytes per frame across the pipe: 11.1 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 4991 MB/s  ->  floor 2.2 ms/frame  (451.3 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   2.224s   (worker exit 0)
    30 frames:  18.896s   (worker exit 0)
    60 frames:   1.830s   (worker exit 0)
    90 frames:   1.945s   (worker exit 0)
  fit over 3 points: -282.52 ms/frame  =  nan fps   (startup 24.51s, R^2 0.7449)
      30 frames: actual  18.896s  fit says  16.032s  off by +2.863s
      60 frames: actual   1.830s  fit says   7.557s  off by -5.727s
      90 frames: actual   1.945s  fit says  -0.919s  off by +2.863s
  the bytes alone, at this box's pipe rate: 2.2 ms/frame
  this is -127.50x that
  RESULT: NO USABLE FIT (R^2 0.745). The points do not lie on a line, so the
```

## 2560x1440

```
  size: 2560x1440   bypass: False
  bytes per frame across the pipe: 44.2 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 7306 MB/s  ->  floor 6.1 ms/frame  (165.1 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   1.538s   (worker exit 0)
    30 frames:   2.340s   (worker exit 0)
    60 frames:   2.980s   (worker exit 0)
    90 frames:   3.751s   (worker exit 0)
  fit over 3 points: 23.51 ms/frame  =  42.5 fps   (startup 1.61s, R^2 0.9972)
      30 frames: actual   2.340s  fit says   2.318s  off by +0.022s
      60 frames: actual   2.980s  fit says   3.023s  off by -0.043s
      90 frames: actual   3.751s  fit says   3.729s  off by +0.022s
  the bytes alone, at this box's pipe rate: 6.1 ms/frame
  this is 3.88x that
  RESULT: THE WORKER IS THE WALL (3.9x the pipe). It took
```

## How to read it

- **At the pipe's rate** → the worker keeps up with its own pipe once
  nothing waits on it. The pipeline's 12-18fps is then the client loop,
  not the worker, and the proven shared-file transport (~4x one way, see
  `experiments/mmap_bridge/`) lifts that ceiling directly.
- **Well above the pipe's rate** → the worker is the wall. It took longer
  than the pipe needs for the same bytes with nothing else running, so no
  client change and no faster transport moves it; only a host we write
  would.

Both sizes matter: 720p is where a slow worker shows up alone, 1440p is
where the pipe starts to hide it.

Full output: `raw/feed_*.log`, and each run's worker stderr in
`raw/feed_*.worker.log`.
