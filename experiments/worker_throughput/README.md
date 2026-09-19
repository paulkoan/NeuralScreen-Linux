# Worker throughput, with no client in the way

One question: **is the worker the wall, or is our client?**

Every number this project has for the pipeline includes the client — a strictly
serial loop that sends a frame and then waits for *that frame's* result. That is a
round-trip measurement, and the round trip is one of the things under
investigation. This measures the other thing: the worker fed a byte-identical
stream as fast as it will accept one, with **its results discarded rather than
read**, so nothing in the process is waiting on a reply.

No handshake, no capture, no display, no per-frame timing — just the worker.

## Running it

```bash
cd experiments/worker_throughput
./run.sh --push
```

About a minute. It runs both sizes because one cannot answer it alone.

## Why two sizes

A frame is **8 bytes per pixel in** (RGBA8 colour plus two float16 motion
channels) and **4 bytes per pixel back**, so the pipe's own floor — at the
~1.1 GB/s measured on this hardware — is:

| size | per frame across the pipe | pipe floor |
|---|---|---|
| 1280×720 | 11.1 MB | ~10 ms → ~100 fps |
| 2560×1440 | 44.2 MB | ~40 ms → ~25 fps |

720p is where a slow worker shows up on its own; 1440p is where the pipe starts to
hide it.

## Why three runs per size, after a warm-up

NGX init and shutdown cost a second or two and are not what is being measured, and
**the first `wine` invocation also pays the cold prefix and wineserver start.** The
first version of this ran each size twice and took the difference of N and 2N,
assuming the startup cancelled. It did not: 60 frames came in 0.65s *faster* than
30, which is impossible, so the derived figure was smaller than the noise behind
it. The tool refused to report — which is what that guard is for — but it meant no
usable number.

So now: a discarded warm-up pass first, then **N, 2N and 3N frames**, and the
per-frame cost is the slope of a least-squares fit through the three. The intercept
is the startup, the residuals and R² are printed, and **R² ≤ 0.98 is refused
rather than quoted**. Three points because a line through two points fits anything
— the lesson the size sweep already taught.

## Why the floor is measured here too

The verdict turns on how the worker compares to the pipe it is fed through, so
that rate is measured on the same machine in the same run, by writing 200 MB to a
`cat > /dev/null` that does nothing else. The 1.1 GB/s this project has been
quoting came from a Python-side copy on a different box and does not belong in a
verdict about this one.

## Why the stream is built with the client's own code

`minimal.worker.stream_header` and `protocol.send_frame` build it, so it is
byte-identical to what a real run sends rather than a second implementation of the
protocol that might be rejected on frame 0. (The first byte of a frame message is
`F` — the worker's message tag — which is why a stream that starts with the wrong
message type dies immediately.)

## Reading the result

The tool prints its own verdict, and the ratio to the pipe floor decides it:

- **At the pipe's rate** → the worker keeps up with its own pipe once nothing
  waits on it. The pipeline's 12–18 fps is then **the client loop**, not the
  worker — and the shared-file transport proven in `experiments/mmap_bridge/`
  (~7 GB/s one way, ~4x a pipe) lifts that ceiling directly. No new host needed.
- **Well above the pipe's rate** → the worker is the wall. It took longer than the
  pipe needs for the same bytes with nothing else in the process, so no client
  change and no faster transport moves it. Only a host we write would.

## The client's own write path, measured without a GPU

`experiments/worker_throughput/client_write.py` runs anywhere — no Wine, no GPU,
no worker — and answers "is our frame write slow, or is the reader?" by writing
frames through the real `send_frame` into the fastest reader there is:

```
reader              frame       ms/frame      MB/s
cat>/dev/null       1280x720        5.65      1305
cat>/dev/null       2560x1440      14.14      2086
```

At 1440p a frame is 29.5MB (8 bytes/pixel: RGBA8 plus two float16 motion
channels, half of it the all-zero motion field this MVP sends because it has no
real vectors). **14ms is the client's floor for handing a frame over**, so the
88–112ms the gate reports for `send` is not our write — it is the worker or the
back-pressure waiting for it.

## What it does not measure

The feeder's own writes go through the same pipe the real client uses, so a
pathologically slow feeder would show up as a pipe result rather than as its own
fault. The tool refuses to report at all if the longer run is not slower, which is
the shape that failure takes.
