# run r2026-11-02-ay

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --worker-log`

exit **0** after 8.0s

gpu before: WARN (resident but not contending: chromium (pid 43069, 213.0 MiB); resident but not contending: signal-desktop (pid 43509, 59.0 MiB); resident but not contending: msedge (pid 73501, 220.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)) after waiting 150s; after: BUSY (utilization 59%; chromium (pid 43069, 213.0 MiB); signal-desktop (pid 43509, 59.0 MiB); msedge (pid 73501, 219.0 MiB); Telegram (pid 988444, 36.0 MiB); shelly-ui (pid 1045732, 46.0 MiB); signon-ui (pid 3062205, 17.0 MiB))

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 73834c1 (+20 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 7.417s (16.18 fps headline, 37.87 fps steady), worker exit 0
timing: capture 3.1ms  send 6.8ms  recv 50.5ms  display 0.0ms   (mean 60.4ms/frame, 16.6 fps; median 26.4ms/frame, 37.9 fps steady)
send spread: min 5.0  median 6.7  max 9.4 ms at frame 43 of 120   (steady — a fixed interval, not contention)
recv spread: min 15.4  median 16.7  max 3970.9 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3053 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 122.0 ms (proxy 2.4 [copy 1.6, submit 0.8], network+composite 52.2, readback 67.4, reply 0.0)
[worker] serve frame 1: 33.3 ms (proxy 3.1 [copy 2.0, submit 1.1], network+composite 30.3, readback 0.0, reply 0.0)
[worker] serve frame 2: 33.7 ms (proxy 3.8 [copy 1.8, submit 2.0], network+composite 29.9, readback 0.0, reply 0.0)
[worker] serve frame 29: 17.0 ms (proxy 3.5 [copy 1.9, submit 1.5], network+composite 13.6, readback 0.0, reply 0.0)
[worker] serve frame 59: 15.9 ms (proxy 2.4 [copy 1.5, submit 0.9], network+composite 13.5, readback 0.0, reply 0.0)
[worker] serve frame 89: 17.2 ms (proxy 3.0 [copy 2.0, submit 1.0], network+composite 14.2, readback 0.0, reply 0.0)
[worker] serve frame 119: 16.9 ms (proxy 3.5 [copy 2.2, submit 1.4], network+composite 13.3, readback 0.0, reply 0.0)

```
