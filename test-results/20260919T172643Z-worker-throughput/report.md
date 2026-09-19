# Worker throughput, no client in the way — 20260919T172643Z

**RESULT: NO USABLE FIT (R^2 0.768). The points do not lie on a line, so the**

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
  pipe rate on this box: 5476 MB/s  ->  floor 2.0 ms/frame  (495.2 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   2.386s   (worker exit 0)
    30 frames:   1.970s   (worker exit 0)
      worker's own log: 29 frames in 0.232s = 8.0 ms/frame
      our clock 1.970s minus the worker's frame window 0.232s = 1.738s of startup and teardown
    60 frames:   2.131s   (worker exit 0)
      worker's own log: 59 frames in 0.578s = 9.8 ms/frame
      our clock 2.131s minus the worker's frame window 0.578s = 1.553s of startup and teardown
    90 frames:   8.599s   (worker exit 0)
      worker's own log: 89 frames in 2.024s = 22.7 ms/frame; GAP 4.5s between '[pure] direct DLSSNR Init_Ext -> 0x00000001 (Success)' and '[video] stream 1280x720, LIVE (unbounded), warmup=2'
      our clock 8.599s minus the worker's frame window 2.024s = 6.575s of startup and teardown
  fit over 3 points: 110.49 ms/frame  =  9.1 fps   (startup -2.40s, R^2 0.7682)
      30 frames: actual   1.970s  fit says   0.919s  off by +1.051s
      60 frames: actual   2.131s  fit says   4.233s  off by -2.102s
      90 frames: actual   8.599s  fit says   7.548s  off by +1.051s
  the bytes alone, at this box's pipe rate: 2.0 ms/frame
  this is 54.71x that
  RESULT: NO USABLE FIT (R^2 0.768). The points do not lie on a line, so the
```

## 1280x720 — results READ like the client reads them

```
  size: 1280x720   bypass: False   results: read like the client
  bytes per frame across the pipe: 11.1 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 3652 MB/s  ->  floor 3.0 ms/frame  (330.2 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:  10.977s   (worker exit 0)
    30 frames:   1.969s   (worker exit 0)
      worker's own log: 29 frames in 0.346s = 11.9 ms/frame
      our clock 1.969s minus the worker's frame window 0.346s = 1.623s of startup and teardown
    60 frames:  13.396s   (worker exit 0)
      worker's own log: 59 frames in 0.808s = 13.7 ms/frame; GAP 11.1s between '[pure] standalone D3D12 device ready; no swapchain or carrier modules' and '[host] NVSDK_NGX_D3D12_Init -> 0x00000001 (Success)'
      our clock 13.396s minus the worker's frame window 0.808s = 12.588s of startup and teardown
    90 frames:   2.687s   (worker exit 0)
      worker's own log: 89 frames in 1.095s = 12.3 ms/frame
      our clock 2.687s minus the worker's frame window 1.095s = 1.592s of startup and teardown
  fit over 3 points: 11.97 ms/frame  =  83.5 fps   (startup 5.30s, R^2 0.0031)
      30 frames: actual   1.969s  fit says   5.658s  off by -3.689s
      60 frames: actual  13.396s  fit says   6.017s  off by +7.379s
      90 frames: actual   2.687s  fit says   6.377s  off by -3.689s
  the bytes alone, at this box's pipe rate: 3.0 ms/frame
  this is 3.95x that
  RESULT: NO USABLE FIT (R^2 0.003). The points do not lie on a line, so the
```

## 2560x1440 — results DISCARDED (/dev/null)

```
  size: 2560x1440   bypass: False   results: discarded
  bytes per frame across the pipe: 44.2 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 4322 MB/s  ->  floor 10.2 ms/frame  (97.7 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   1.755s   (worker exit 0)
    30 frames:   2.850s   (worker exit 0)
      worker's own log: 29 frames in 1.067s = 36.8 ms/frame
      our clock 2.850s minus the worker's frame window 1.067s = 1.783s of startup and teardown
    60 frames:   3.527s   (worker exit 0)
      worker's own log: 59 frames in 1.864s = 31.6 ms/frame
      our clock 3.527s minus the worker's frame window 1.864s = 1.663s of startup and teardown
    90 frames:   4.580s   (worker exit 0)
      worker's own log: 89 frames in 2.849s = 32.0 ms/frame; GAP 1.0s between '[video] delivered frame 60 (live)' and '[video] delivered frame 90 (live)'
      our clock 4.580s minus the worker's frame window 2.849s = 1.731s of startup and teardown
  fit over 3 points: 28.83 ms/frame  =  34.7 fps   (startup 1.92s, R^2 0.9845)
      30 frames: actual   2.850s  fit says   2.787s  off by +0.063s
      60 frames: actual   3.527s  fit says   3.652s  off by -0.125s
      90 frames: actual   4.580s  fit says   4.517s  off by +0.063s
  the bytes alone, at this box's pipe rate: 10.2 ms/frame
  this is 2.82x that
  RESULT: THE WORKER IS THE WALL (2.8x the pipe). It took
```

## 2560x1440 — results READ like the client reads them

```
  size: 2560x1440   bypass: False   results: read like the client
  bytes per frame across the pipe: 44.2 MB (8/pixel in, 4/pixel back)
  pipe rate on this box: 4021 MB/s  ->  floor 11.0 ms/frame  (90.9 fps)
  warm-up pass (its time is the cold start and is not measured):
    5 frames:   1.904s   (worker exit 0)
    30 frames:   2.971s   (worker exit 0)
      worker's own log: 29 frames in 1.276s = 44.0 ms/frame; GAP 1.1s between '[video] delivered frame 3 (live)' and '[video] delivered frame 30 (live)'
      our clock 2.971s minus the worker's frame window 1.276s = 1.695s of startup and teardown
    60 frames:   4.548s   (worker exit 0)
      worker's own log: 59 frames in 2.595s = 44.0 ms/frame; GAP 1.3s between '[video] delivered frame 30 (live)' and '[video] delivered frame 60 (live)'
      our clock 4.548s minus the worker's frame window 2.595s = 1.953s of startup and teardown
    90 frames:  17.942s   (worker exit 0)
      worker's own log: 89 frames in 4.648s = 52.2 ms/frame; GAP 6.4s between 'dlss5-feed-host64 (built Sep 11 2026 17:26:14)' and '[host] adapter 0: NVIDIA GeForce RTX 4080 SUPER vendor=0x10DE'
      our clock 17.942s minus the worker's frame window 4.648s = 13.294s of startup and teardown
  fit over 3 points: 249.51 ms/frame  =  4.0 fps   (startup -6.48s, R^2 0.8280)
      30 frames: actual   2.971s  fit says   1.002s  off by +1.970s
      60 frames: actual   4.548s  fit says   8.487s  off by -3.939s
      90 frames: actual  17.942s  fit says  15.972s  off by +1.970s
  the bytes alone, at this box's pipe rate: 11.0 ms/frame
  this is 22.68x that
  RESULT: NO USABLE FIT (R^2 0.828). The points do not lie on a line, so the
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
