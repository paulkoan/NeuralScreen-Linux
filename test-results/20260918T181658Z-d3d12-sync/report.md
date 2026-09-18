# D3D12 sync probe — 20260918T181658Z

**RESULT: SYNCHRONISATION IS CHEAP — 0.1ms for a full round trip, and 1.5ms for a frame-sized copy with the sync. Neither accounts for the pipeline's ~55ms, so the fixed cost is in the host's own design and a host we write could plausibly get past it. 015c:fixme:winediag:loader_init wine-staging 11.17 is a testing version containing experimental patches. 015c:fixme:winediag:loader_init Please mention your exact version when filing bug reports on winehq.org. **

## What it measured

```
  A. submit + fence wait, one frame at a time (the host's shape)
    ExecuteCommandLists + Signal          0.001 ms each   (20 of them, 0.0 ms total)
    the wait for it to finish             0.058 ms each   (20 of them, 1.2 ms total)
    the whole round trip                  0.059 ms each   (20 of them, 1.2 ms total)
  B. fence wait on an already-complete value (no GPU work)
    SetEventOnCompletion + Wait           0.001 ms each   (20 of them, 0.0 ms total)
  C. submit, then poll GetCompletedValue instead of waiting
    submit + spin to completion           0.044 ms each   (20 of them, 0.9 ms total)
  D. 20 submits back to back, one wait at the end
    submit, no per-frame wait             0.055 ms each   (20 of them, 1.1 ms total)
  E. a 14.7MB upload copy + 14.7MB readback, with the sync
    recording the two copies              0.008 ms each   (10 of them, 0.1 ms total)
    submit + wait                         1.537 ms each   (10 of them, 15.4 ms total)
    the whole frame-shaped pass           1.545 ms each   (10 of them, 15.4 ms total)
  one submit+wait round trip:     0.06ms  (the wait alone: 0.06ms)
  that wait with no GPU work:     0.00ms  <- Wine's own cost, nothing
  submit then poll instead:       0.04ms
  submit, never wait per frame:   0.05ms
  14.7MB copy + 14.7MB readback:   1.54ms  (with the sync)
```

## How to read it

- Ran `experiments/d3d12_sync/run.sh` on the box with the GPU, under the
  same Wine environment the worker gets (printed in the log).
- Headless on purpose: no window, no swapchain, no NGX, no pipe. A window
  would measure DXVK's present path instead of the synchronisation.
- The discriminator is **B**, the wait on an already-complete fence with no
  GPU work outstanding. Whatever that costs is paid by every wait, whoever
  wrote the host, so it is the part that is not ours to fix.
- Context: the pipeline spends ~55ms per frame with NGX off at *any* size
  (a 64KB frame cost 64.5ms, a 3.7MB frame 54.9ms), so the cost is not the
  bytes and not the network.

Full output: `raw/probe.log`.
