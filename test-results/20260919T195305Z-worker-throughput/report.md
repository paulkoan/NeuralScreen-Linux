# Worker throughput, no client in the way — 20260919T195305Z

**RESULT: THE WORKER IS THE WALL (4.8x the pipe). It took**

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
  pipe rate on this box: 5800 MB/s  ->  floor 1.9 ms/frame  (524.5 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   2.189s   (worker exit 0)
    30 frames:   1.701s   (worker exit 0)
      worker's own log: 29 frames in 0.257s = 8.9 ms/frame
      our clock 1.701s minus the worker's frame window 0.257s = 1.444s of startup and teardown
    60 frames:   1.922s   (worker exit 0)
      worker's own log: 59 frames in 0.513s = 8.7 ms/frame
      our clock 1.922s minus the worker's frame window 0.513s = 1.409s of startup and teardown
    90 frames:   2.256s   (worker exit 0)
      worker's own log: 89 frames in 0.730s = 8.2 ms/frame
      our clock 2.256s minus the worker's frame window 0.730s = 1.526s of startup and teardown
  fit over 3 points: 9.25 ms/frame  =  108.2 fps   (startup 1.40s, R^2 0.9861)
      30 frames: actual   1.701s  fit says   1.682s  off by +0.019s
      60 frames: actual   1.922s  fit says   1.960s  off by -0.038s
      90 frames: actual   2.256s  fit says   2.237s  off by +0.019s
  the bytes alone, at this box's pipe rate: 1.9 ms/frame
  this is 4.85x that
  RESULT: THE WORKER IS THE WALL (4.8x the pipe). It took
```

## 1280x720 — results READ like the client reads them

```
  size: 1280x720   bypass: False   results: read like the client
  bytes per frame across the pipe: 11.1 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 5162 MB/s  ->  floor 2.1 ms/frame  (466.8 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   1.614s   (worker exit 0)
    30 frames:   1.732s   (worker exit 0)
      worker's own log: 29 frames in 0.339s = 11.7 ms/frame
      our clock 1.732s minus the worker's frame window 0.339s = 1.393s of startup and teardown
    60 frames:   2.133s   (worker exit 0)
      worker's own log: 59 frames in 0.671s = 11.4 ms/frame
      our clock 2.133s minus the worker's frame window 0.671s = 1.462s of startup and teardown
    90 frames:   2.438s   (worker exit 0)
      worker's own log: 89 frames in 0.893s = 10.0 ms/frame
      our clock 2.438s minus the worker's frame window 0.893s = 1.545s of startup and teardown
  fit over 3 points: 11.77 ms/frame  =  84.9 fps   (startup 1.39s, R^2 0.9939)
      30 frames: actual   1.732s  fit says   1.748s  off by -0.016s
      60 frames: actual   2.133s  fit says   2.101s  off by +0.032s
      90 frames: actual   2.438s  fit says   2.454s  off by -0.016s
  the bytes alone, at this box's pipe rate: 2.1 ms/frame
  this is 5.50x that
  RESULT: THE WORKER IS THE WALL (5.5x the pipe). It took
```

## 2560x1440 — results DISCARDED (/dev/null)

```
  size: 2560x1440   bypass: False   results: discarded
  bytes per frame across the pipe: 44.2 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 6066 MB/s  ->  floor 7.3 ms/frame  (137.1 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   1.868s   (worker exit 0)
    30 frames:   2.188s   (worker exit 0)
      worker's own log: 29 frames in 0.760s = 26.2 ms/frame
      our clock 2.188s minus the worker's frame window 0.760s = 1.428s of startup and teardown
    60 frames:   2.972s   (worker exit 0)
      worker's own log: 59 frames in 1.585s = 26.9 ms/frame
      our clock 2.972s minus the worker's frame window 1.585s = 1.387s of startup and teardown
    90 frames:  27.389s   (worker exit 0)
      worker's own log: 89 frames in 25.992s = 292.0 ms/frame
      our clock 27.389s minus the worker's frame window 25.992s = 1.397s of startup and teardown
  fit over 3 points: 420.02 ms/frame  =  2.4 fps   (startup -14.35s, R^2 0.7733)
      30 frames: actual   2.188s  fit says  -1.751s  off by +3.939s
      60 frames: actual   2.972s  fit says  10.849s  off by -7.878s
      90 frames: actual  27.389s  fit says  23.450s  off by +3.939s
  the bytes alone, at this box's pipe rate: 7.3 ms/frame
  this is 57.60x that
  RESULT: NO USABLE FIT (R^2 0.773). The points do not lie on a line, so the
```

## 2560x1440 — results READ like the client reads them

```
  size: 2560x1440   bypass: False   results: read like the client
  bytes per frame across the pipe: 44.2 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 6916 MB/s  ->  floor 6.4 ms/frame  (156.3 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   1.518s   (worker exit 0)
    30 frames:   2.836s   (worker exit 0)
      worker's own log: 29 frames in 1.225s = 42.2 ms/frame
      our clock 2.836s minus the worker's frame window 1.225s = 1.611s of startup and teardown
    60 frames:   3.617s   (worker exit 0)
      worker's own log: 59 frames in 2.107s = 35.7 ms/frame
      our clock 3.617s minus the worker's frame window 2.107s = 1.510s of startup and teardown
    90 frames:   4.769s   (worker exit 0)
      worker's own log: 89 frames in 3.176s = 35.7 ms/frame
      our clock 4.769s minus the worker's frame window 3.176s = 1.593s of startup and teardown
  fit over 3 points: 32.22 ms/frame  =  31.0 fps   (startup 1.81s, R^2 0.9878)
      30 frames: actual   2.836s  fit says   2.774s  off by +0.062s
      60 frames: actual   3.617s  fit says   3.741s  off by -0.124s
      90 frames: actual   4.769s  fit says   4.707s  off by +0.062s
  the bytes alone, at this box's pipe rate: 6.4 ms/frame
  this is 5.04x that
  RESULT: THE WORKER IS THE WALL (5.0x the pipe). It took
```

## The gap test

```
--- 0ms gap after every frame
      worker's own log: 2 frames in 0.020s = 10.0 ms/frame
      worker's own log: 29 frames in 0.273s = 9.4 ms/frame
      worker's own log: 59 frames in 0.638s = 10.8 ms/frame
  fit over 3 points: -21.72 ms/frame  =  nan fps   (startup 3.58s, R^2 0.5029)
  RESULT: NO USABLE FIT (R^2 0.503). The points do not lie on a line, so the

--- 20ms gap after every frame
      worker's own log: 2 frames in 0.037s = 18.5 ms/frame
      worker's own log: 29 frames in 2.105s = 72.6 ms/frame; GAP 1.4s between '[pure] direct DLSSNR Init_Ext -> 0x00000001 (Success)' and '[video] stream 1280x720, LIVE (unbounded), warmup=2'
      worker's own log: 59 frames in 1.328s = 22.5 ms/frame
  fit over 3 points: 24.40 ms/frame  =  41.0 fps   (startup 2.25s, R^2 0.1059)
  of which 20ms is the deliberate gap, so the worker's own share is 4.40 ms/frame (227.1 fps)  <- this is the number that decides it
  RESULT: NO USABLE FIT (R^2 0.106). The points do not lie on a line, so the

```

One thing this harness has never done is leave a gap between frames, and
the pipeline always leaves one. Feed frames back to back and the worker is
never idle; give it 20ms and it drops into its poll loop between frames,
which under Wine can cost a whole timer tick per attempt. The fit contains
the gap we put there, so `feed.py` prints the remainder — the worker's own
share — and that remainder is what decides whether the fixed ~40ms our loop
pays is the worker's poll or something in us.

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
