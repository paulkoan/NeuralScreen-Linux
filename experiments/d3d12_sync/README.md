# The D3D12 sync probe

One question: **what does a submit-and-wait cost under Wine, with nothing else in
the process?**

It matters because the frame pipeline spends **~55ms per frame regardless of the
frame's size**. Measured with NGX switched off, on a synthetic source so the
capture is out of the picture:

| frame | bytes | ms/frame |
|---|---|---|
| 128×128 | 0.07 MB | 64.5 |
| 640×360 | 0.92 MB | 69.2 |
| 1280×720 | 3.7 MB | 54.9 |
| 2560×1440 | 14.7 MB | 174.8 (85.5 in an earlier run) |

A 64KB frame costing more than a 3.7MB one cannot happen under any model where
the bytes set the pace, and the network was never in play here (NGX off). So the
cost is something else per frame, and the host source offers two candidates: a
per-frame fence wait (`SetEventOnCompletion` + `WaitForSingleObject`, lines
546-558 and 1784-1799) and a pipe poll loop with `Sleep(8)` per poll (lines
4741-4748). Under Wine each of those is a wine-server and driver round trip.

If this probe says a round trip is ~15ms, then no host we write can avoid it and
the pipeline's ceiling is real. If it says ~1ms, the current host is spending
~50ms a frame on its own design and a host that pipelines could get past it.

## Running it

```bash
cd experiments/d3d12_sync
./run.sh --push
```

It cross-compiles `probe.cpp` with `x86_64-w64-mingw32-g++` and runs it under the
**worker's own Wine environment** — `wine_env.py` imports `worker_env()` from
`minimal/worker.py` rather than restating the DLL overrides, because a probe
measuring a different D3D12 stack would measure nothing. The environment it used
is printed at the top of the log and in the report.

## What it measures

- **A.** submit + fence wait, one frame at a time — the host's per-frame shape
- **B.** the same wait on an **already-complete** fence, no GPU work at all — this
  is Wine's own cost, and it is the discriminator
- **C.** submit, then poll `GetCompletedValue` instead of waiting on an event
- **D.** 20 submits back to back with no per-frame wait — what pipelining costs
- **E.** a 14.7MB upload copy + a 14.7MB readback with the sync — a frame-shaped
  pass, so its total is directly comparable to the 1440p numbers above

Headless on purpose. The project's own M0 gate established that a standalone
D3D12 device works here without a carrier or a swapchain; adding a window would
measure DXVK's present path instead of the synchronisation.

## Reading the result

The probe prints its own verdict, and **B decides which one it is**:

- **B ≥ 5ms** → waiting itself costs that much in Wine. Three or four of those a
  frame is the pipeline's ~55ms. No host we write avoids it, the frame rate does
  not move when the frame gets smaller, and the honest answer to the original
  question is that this architecture cannot reach a playable rate.
- **B cheap, A's wait expensive** → it is the round trip to the GPU, not Wine's
  event handling, so a host could overlap it instead of waiting (compare D).
- **A cheap, submitting expensive** → the host does several submits per frame and
  fewer would help.
- **A and E both cheap** → synchronisation is not the fixed cost at all; it is the
  host's own design, and a host we write could plausibly get past it.
