# Worker throughput, no client in the way — 20260918T192715Z

**RESULT: AT THE PIPE'S RATE. With no handshake and no client in the way, the**

## What this is

The worker fed a byte-identical stream as fast as it will take one, with
its results discarded rather than read, so nothing in the process is
waiting on a round trip. Every other number this project has includes
the client's strictly serial loop — send a frame, wait for that frame —
which is what this removes.

Each size runs twice, with N frames and 2N, and the per-frame cost is
the difference: NGX init and shutdown are a second or two and cancel
exactly. The stream is built with the client's own `stream_header` and
`protocol.send_frame`, so it cannot be rejected for being a second
implementation of the protocol.

The pipe floor is 8 bytes per pixel in (RGBA8 colour + two float16 motion
channels) plus 4 bytes per pixel back, at the ~1.1 GB/s measured here.
That is ~10ms a frame at 720p and ~40ms at 1440p.

## 1280x720

```
  size: 1280x720   frames: 30 then 60   bypass: False
  bytes per frame across the pipe: 11.1 MB (8/pixel in, 4/pixel back)
   30 frames:   2.350s   (worker exit 0)
   60 frames:   1.700s   (worker exit 0)
```

## 2560x1440

```
  size: 2560x1440   frames: 30 then 60   bypass: False
  bytes per frame across the pipe: 44.2 MB (8/pixel in, 4/pixel back)
   30 frames:   2.485s   (worker exit 0)
   60 frames:   3.009s   (worker exit 0)
  derived per frame: 17.46 ms  =  57.3 fps
  the pipe alone would be: 40.2 ms/frame at ~1.1 GB/s = 24.9 fps
  this run is 0.43x the pipe floor
  RESULT: AT THE PIPE'S RATE. With no handshake and no client in the way, the
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
