# Worker throughput, no client in the way — 20260919T103213Z

**RESULT: THE WORKER IS THE WALL (2.9x the pipe). It took**

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
  pipe rate on this box: 6584 MB/s  ->  floor 1.7 ms/frame  (595.3 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   2.201s   (worker exit 0)
    30 frames:   1.677s   (worker exit 0)
      worker's own log: 29 frames in 0.238s = 8.2 ms/frame
      our clock 1.677s minus the worker's frame window 0.238s = 1.439s of startup and teardown
    60 frames:   1.798s   (worker exit 0)
      worker's own log: 59 frames in 0.474s = 8.0 ms/frame
      our clock 1.798s minus the worker's frame window 0.474s = 1.324s of startup and teardown
    90 frames:   1.972s   (worker exit 0)
      worker's own log: 89 frames in 0.650s = 7.3 ms/frame
      our clock 1.972s minus the worker's frame window 0.650s = 1.322s of startup and teardown
  fit over 3 points: 4.91 ms/frame  =  203.5 fps   (startup 1.52s, R^2 0.9897)
      30 frames: actual   1.677s  fit says   1.668s  off by +0.009s
      60 frames: actual   1.798s  fit says   1.815s  off by -0.017s
      90 frames: actual   1.972s  fit says   1.963s  off by +0.009s
  the bytes alone, at this box's pipe rate: 1.7 ms/frame
  this is 2.93x that
  RESULT: THE WORKER IS THE WALL (2.9x the pipe). It took
```

## 1280x720 — results READ like the client reads them

```
  size: 1280x720   bypass: False   results: read like the client
  bytes per frame across the pipe: 11.1 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 6180 MB/s  ->  floor 1.8 ms/frame  (558.8 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   1.508s   (worker exit 0)
    30 frames:   1.704s   (worker exit 0)
      worker's own log: 29 frames in 0.345s = 11.9 ms/frame
      our clock 1.704s minus the worker's frame window 0.345s = 1.359s of startup and teardown
    60 frames:   1.898s   (worker exit 0)
      worker's own log: 59 frames in 0.570s = 9.7 ms/frame
      our clock 1.898s minus the worker's frame window 0.570s = 1.328s of startup and teardown
    90 frames:   2.017s   (worker exit 0)
      worker's own log: 89 frames in 0.755s = 8.5 ms/frame
      our clock 2.017s minus the worker's frame window 0.755s = 1.262s of startup and teardown
  fit over 3 points: 5.22 ms/frame  =  191.4 fps   (startup 1.56s, R^2 0.9813)
      30 frames: actual   1.704s  fit says   1.716s  off by -0.013s
      60 frames: actual   1.898s  fit says   1.873s  off by +0.025s
      90 frames: actual   2.017s  fit says   2.030s  off by -0.013s
  the bytes alone, at this box's pipe rate: 1.8 ms/frame
  this is 2.92x that
  RESULT: THE WORKER IS THE WALL (2.9x the pipe). It took
```

## 2560x1440 — results DISCARDED (/dev/null)

```
  size: 2560x1440   bypass: False   results: discarded
  bytes per frame across the pipe: 44.2 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 5651 MB/s  ->  floor 7.8 ms/frame  (127.7 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   1.426s   (worker exit 0)
    30 frames:   2.053s   (worker exit 0)
      worker's own log: 29 frames in 0.742s = 25.6 ms/frame
      our clock 2.053s minus the worker's frame window 0.742s = 1.311s of startup and teardown
    60 frames:   2.929s   (worker exit 0)
      worker's own log: 59 frames in 1.579s = 26.8 ms/frame
      our clock 2.929s minus the worker's frame window 1.579s = 1.350s of startup and teardown
    90 frames:  17.236s   (worker exit 0)
      worker's own log: 89 frames in 12.543s = 140.9 ms/frame; GAP 10.9s between '[video] delivered frame 60 (live)' and '[video] delivered frame 90 (live)'
      our clock 17.236s minus the worker's frame window 12.543s = 4.693s of startup and teardown
  fit over 3 points: 253.05 ms/frame  =  4.0 fps   (startup -7.78s, R^2 0.7931)
      30 frames: actual   2.053s  fit says  -0.186s  off by +2.239s
      60 frames: actual   2.929s  fit says   7.406s  off by -4.477s
      90 frames: actual  17.236s  fit says  14.998s  off by +2.239s
  the bytes alone, at this box's pipe rate: 7.8 ms/frame
  this is 32.33x that
  RESULT: NO USABLE FIT (R^2 0.793). The points do not lie on a line, so the
```

## 2560x1440 — results READ like the client reads them

```
  size: 2560x1440   bypass: False   results: read like the client
  bytes per frame across the pipe: 44.2 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 4293 MB/s  ->  floor 10.3 ms/frame  (97.0 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   1.787s   (worker exit 0)
    30 frames:   2.415s   (worker exit 0)
      worker's own log: 29 frames in 0.918s = 31.7 ms/frame
      our clock 2.415s minus the worker's frame window 0.918s = 1.497s of startup and teardown
    60 frames:   3.565s   (worker exit 0)
      worker's own log: 59 frames in 2.112s = 35.8 ms/frame; GAP 1.0s between '[video] delivered frame 3 (live)' and '[video] delivered frame 30 (live)'
      our clock 3.565s minus the worker's frame window 2.112s = 1.453s of startup and teardown
    90 frames:   4.541s   (worker exit 0)
      worker's own log: 89 frames in 2.954s = 33.2 ms/frame; GAP 1.0s between '[video] delivered frame 60 (live)' and '[video] delivered frame 90 (live)'
      our clock 4.541s minus the worker's frame window 2.954s = 1.587s of startup and teardown
  fit over 3 points: 35.43 ms/frame  =  28.2 fps   (startup 1.38s, R^2 0.9978)
      30 frames: actual   2.415s  fit says   2.444s  off by -0.029s
      60 frames: actual   3.565s  fit says   3.507s  off by +0.058s
      90 frames: actual   4.541s  fit says   4.570s  off by -0.029s
  the bytes alone, at this box's pipe rate: 10.3 ms/frame
  this is 3.44x that
  RESULT: THE WORKER IS THE WALL (3.4x the pipe). It took
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
