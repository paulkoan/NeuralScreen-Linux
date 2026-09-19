# Worker throughput, no client in the way — 20260919T085959Z

**RESULT: NO USABLE FIT (R^2 0.742). The points do not lie on a line, so the**

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

## 1280x720 — results DISCARDED (/dev/null)

```
  size: 1280x720   bypass: False   results: discarded
  bytes per frame across the pipe: 11.1 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 6355 MB/s  ->  floor 1.7 ms/frame  (574.7 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   2.368s   (worker exit 0)
    30 frames:  12.504s   (worker exit 0)
    60 frames:   1.939s   (worker exit 0)
    90 frames:   2.046s   (worker exit 0)
  fit over 3 points: -174.30 ms/frame  =  nan fps   (startup 15.95s, R^2 0.7423)
      30 frames: actual  12.504s  fit says  10.725s  off by +1.779s
      60 frames: actual   1.939s  fit says   5.496s  off by -3.557s
      90 frames: actual   2.046s  fit says   0.267s  off by +1.779s
  the bytes alone, at this box's pipe rate: 1.7 ms/frame
  this is -100.16x that
  RESULT: NO USABLE FIT (R^2 0.742). The points do not lie on a line, so the
```

## 1280x720 — results READ like the client reads them

```
  size: 1280x720   bypass: False   results: read like the client
  bytes per frame across the pipe: 11.1 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 4771 MB/s  ->  floor 2.3 ms/frame  (431.4 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   1.530s   (worker exit 0)
    30 frames:  21.232s   (worker exit 0)
    60 frames:   2.062s   (worker exit 0)
    90 frames:   2.380s   (worker exit 0)
  fit over 3 points: -314.21 ms/frame  =  nan fps   (startup 27.41s, R^2 0.7374)
      30 frames: actual  21.232s  fit says  17.985s  off by +3.248s
      60 frames: actual   2.062s  fit says   8.558s  off by -6.496s
      90 frames: actual   2.380s  fit says  -0.868s  off by +3.248s
  the bytes alone, at this box's pipe rate: 2.3 ms/frame
  this is -135.55x that
  RESULT: NO USABLE FIT (R^2 0.737). The points do not lie on a line, so the
```

## 2560x1440 — results DISCARDED (/dev/null)

```
  size: 2560x1440   bypass: False   results: discarded
  bytes per frame across the pipe: 44.2 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 4815 MB/s  ->  floor 9.2 ms/frame  (108.8 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   1.700s   (worker exit 0)
    30 frames:   2.335s   (worker exit 0)
    60 frames:   3.159s   (worker exit 0)
    90 frames:   4.062s   (worker exit 0)
  fit over 3 points: 28.79 ms/frame  =  34.7 fps   (startup 1.46s, R^2 0.9993)
      30 frames: actual   2.335s  fit says   2.322s  off by +0.013s
      60 frames: actual   3.159s  fit says   3.185s  off by -0.026s
      90 frames: actual   4.062s  fit says   4.049s  off by +0.013s
  the bytes alone, at this box's pipe rate: 9.2 ms/frame
  this is 3.13x that
  RESULT: THE WORKER IS THE WALL (3.1x the pipe). It took
```

## 2560x1440 — results READ like the client reads them

```
  size: 2560x1440   bypass: False   results: read like the client
  bytes per frame across the pipe: 44.2 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 4903 MB/s  ->  floor 9.0 ms/frame  (110.8 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   1.866s   (worker exit 0)
    30 frames:   2.615s   (worker exit 0)
    60 frames:   3.667s   (worker exit 0)
    90 frames:   4.845s   (worker exit 0)
  fit over 3 points: 37.17 ms/frame  =  26.9 fps   (startup 1.48s, R^2 0.9989)
      30 frames: actual   2.615s  fit says   2.594s  off by +0.021s
      60 frames: actual   3.667s  fit says   3.709s  off by -0.042s
      90 frames: actual   4.845s  fit says   4.824s  off by +0.021s
  the bytes alone, at this box's pipe rate: 9.0 ms/frame
  this is 4.12x that
  RESULT: THE WORKER IS THE WALL (4.1x the pipe). It took
```

## The comparison this run exists for

Each size runs twice: once with the worker's results discarded, once with
them read the way the pipeline reads them — its own `WorkerReader` on its
own thread, in index order, display skipped. Everything else is identical:
the same stream, the same sizes, the same three-point fit.

The pipeline reports ~45ms a frame in `send` while this harness — with
results discarded — says the same worker does 23.5ms at 1440p and under
4ms at 720p. Reading the results is the one thing the pipeline does per
frame that the harness did not do, so if the READ pass is far slower than
the DISCARD pass, the pacing is in our own result path.

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
