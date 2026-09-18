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

## Why it runs each size twice

NGX init and shutdown cost a second or two, and that is not what is being
measured. Each size is run with N frames and with 2N, and the per-frame cost is
the difference over N — the startup and the exit cancel exactly. The tool derives
that itself rather than leaving the arithmetic to whoever reads the report.

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

## What it does not measure

The feeder's own writes go through the same pipe the real client uses, so a
pathologically slow feeder would show up as a pipe result rather than as its own
fault. The tool refuses to report at all if the longer run is not slower, which is
the shape that failure takes.
