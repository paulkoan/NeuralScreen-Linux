# run r2026-11-02-ba

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 1920x1080 --worker-log`

exit **0** after 6.4s

gpu before: WARN (resident but not contending: chromium (pid 43069, 213.0 MiB); resident but not contending: signal-desktop (pid 43509, 59.0 MiB); resident but not contending: msedge (pid 73501, 219.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)); after: BUSY (utilization 52%; chromium (pid 43069, 213.0 MiB); signal-desktop (pid 43509, 59.0 MiB); msedge (pid 73501, 219.0 MiB); Telegram (pid 988444, 36.0 MiB); shelly-ui (pid 1045732, 46.0 MiB); signon-ui (pid 3062205, 17.0 MiB))

```
source synthetic  capture 1920x1080  ->  work 1920x1080 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 5de071c (+21 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 5.949s (20.17 fps headline, 67.28 fps steady), worker exit 0
timing: capture 2.0ms  send 3.1ms  recv 43.1ms  display 0.0ms   (mean 48.2ms/frame, 20.8 fps; median 14.9ms/frame, 67.3 fps steady)
send spread: min 2.5  median 3.0  max 4.8 ms at frame 37 of 120   (steady — a fixed interval, not contention)
recv spread: min 9.5  median 9.9  max 3821.8 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2981 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.1016..0.6226 mean -0.76198; residual mean 0.0186 0.0169 0.0229 (rgb, head/4), logit mean -3.2814; non-finite 0 of 8294400; first 8 0.0011 -0.0350 -0.0381 -4.3438 0.0004 -0.0418 -0.0382 -3.8105
[worker] serve frame 0: 104.5 ms (proxy 2.8 [copy 1.3, submit 1.5], network+composite 61.0, readback 40.7, reply 0.0)
[worker] serve frame 1: 47.2 ms (proxy 3.0 [copy 1.5, submit 1.5], network+composite 44.2, readback 0.0, reply 0.0)
[worker] serve frame 2: 41.8 ms (proxy 2.3 [copy 0.9, submit 1.4], network+composite 39.5, readback 0.0, reply 0.0)
[worker] serve frame 29: 9.7 ms (proxy 1.9 [copy 1.1, submit 0.8], network+composite 7.8, readback 0.0, reply 0.0)
[worker] serve frame 59: 9.8 ms (proxy 1.9 [copy 1.1, submit 0.8], network+composite 7.9, readback 0.0, reply 0.0)
[worker] serve frame 89: 9.7 ms (proxy 1.7 [copy 0.9, submit 0.8], network+composite 8.0, readback 0.0, reply 0.0)

```
