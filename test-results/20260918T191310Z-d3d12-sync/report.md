# D3D12 substrate, and the worker's own loop — 20260918T191310Z

**Probe: RESULT: SYNCHRONISATION IS CHEAP — 0.0ms for a full round trip, and 1.4ms for a frame-sized copy with the sync. Neither accounts for the pipeline's ~55ms, so the fixed cost is in the host's own design and a host we write could plausibly get past it. 0158:fixme:winediag:loader_init wine-staging 11.17 is a testing version containing experimental patches. 0158:fixme:winediag:loader_init Please mention your exact version when filing bug reports on winehq.org. **

**Worker --test: the worker's --test did not report a completed count**

## 1. The D3D12 substrate

```
  A. submit + fence wait, one frame at a time (the host's shape)
    ExecuteCommandLists + Signal          0.001 ms each   (20 of them, 0.0 ms total)
    the wait for it to finish             0.048 ms each   (20 of them, 1.0 ms total)
    the whole round trip                  0.050 ms each   (20 of them, 1.0 ms total)
  B. fence wait on an already-complete value (no GPU work)
    SetEventOnCompletion + Wait           0.001 ms each   (20 of them, 0.0 ms total)
  C. submit, then poll GetCompletedValue instead of waiting
    submit + spin to completion           0.039 ms each   (20 of them, 0.8 ms total)
  D. 20 submits back to back, one wait at the end
    submit, no per-frame wait             0.057 ms each   (20 of them, 1.1 ms total)
  E. a 14.7MB upload copy + 14.7MB readback, with the sync
    recording the two copies              0.007 ms each   (10 of them, 0.1 ms total)
    submit + wait                         1.379 ms each   (10 of them, 13.8 ms total)
    the whole frame-shaped pass           1.386 ms each   (10 of them, 13.9 ms total)
  one submit+wait round trip:     0.05ms  (the wait alone: 0.05ms)
  that wait with no GPU work:     0.00ms  <- Wine's own cost, nothing
  submit then poll instead:       0.04ms
  submit, never wait per frame:   0.06ms
  14.7MB copy + 14.7MB readback:   1.39ms  (with the sync)
```

## 2. The worker's own loop, with nothing feeding it

```
20:13:17.913  [host] adapter 0: NVIDIA GeForce RTX 4080 SUPER vendor=0x10DE
20:13:17.913  [host] adapter 1: Intel(R) UHD Graphics 770 (ADL-S GT1) vendor=0x8086
20:13:18.511  [host] NVSDK_NGX_D3D12_Init -> 0x00000001 (Success)
20:13:18.557  [pure] direct DLSSNR Init_Ext -> 0x00000001 (Success)
20:13:19.884  [pure] direct feature 18 ready: 640x360 preset=0 result=0x00000001
20:13:19.891  [host] --test finished: 0/300 evaluates succeeded
20:13:19.891  [host] check the host's ReShade.log for 'feature 18 created' / 'evaluation succeeded'
elapsed: 8s
```

## How to read the two together

- Both ran under the worker's own Wine environment (printed in the log).
- **1** says what the GPU layer can do: a 14.7MB upload copy, a 14.7MB
  readback and the sync cost ~1.5ms. That is the floor for a frame's GPU
  work, and it is not why a frame costs 55-175ms.
- **2** says what the worker does per frame with no pipe and no client. Its
  loop calls `PumpPresent()` before every evaluate — a swapchain present
  per frame — and the pipe path additionally polls with `Sleep(8)`.
- Compare **2** against the pipeline's number for the same size:
  `bypass360` (640x360, through the pipe, NGX off) measured 69.2ms a
  frame. If **2** is a fraction of that, the pipe and the client protocol
  are the cost and the worker is not.

Full output: `raw/probe.log` and `raw/host_test.log`.
