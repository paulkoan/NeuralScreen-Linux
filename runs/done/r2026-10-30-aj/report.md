# run r2026-10-30-aj

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 1920x1080 --no-motion --worker-log`

exit **0** after 6.1s

```
source synthetic  capture 1920x1080  ->  work 1920x1080 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo eff8d69 (+20 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 5.645s (21.26 fps headline, 69.02 fps steady), worker exit 0
timing: capture 1.9ms  send 2.9ms  recv 40.9ms  display 0.0ms   (mean 45.6ms/frame, 21.9 fps; median 14.5ms/frame, 69.0 fps steady)
send spread: min 2.3  median 2.8  max 4.2 ms at frame 62 of 120   (steady — a fixed interval, not contention)
recv spread: min 9.5  median 9.8  max 3722.6 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

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
[worker] serve: warm-up 2946 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.1016..0.6226 mean -0.76198; residual mean 0.0186 0.0169 0.0229 (rgb, head/4), logit mean -3.2814; non-finite 0 of 8294400; first 8 0.0011 -0.0350 -0.0381 -4.3438 0.0004 -0.0418 -0.0382 -3.8105
[worker] serve frame 0: 69.6 ms (proxy 2.1 [copy 1.3, submit 0.8], network+composite 30.6, readback 36.9, reply 0.0)
[worker] serve frame 1: 10.2 ms (proxy 2.0 [copy 1.0, submit 1.0], network+composite 8.3, readback 0.0, reply 0.0)
[worker] serve frame 2: 9.9 ms (proxy 1.7 [copy 0.9, submit 0.8], network+composite 8.2, readback 0.0, reply 0.0)
[worker] serve frame 29: 9.9 ms (proxy 2.0 [copy 1.0, submit 1.0], network+composite 7.9, readback 0.0, reply 0.0)
[worker] serve frame 59: 9.5 ms (proxy 1.7 [copy 0.9, submit 0.8], network+composite 7.8, readback 0.0, reply 0.0)
[worker] serve frame 89: 9.6 ms (proxy 1.8 [copy 0.9, submit 0.9], network+composite 7.8, readback 0.0, reply 0.0)
[worker] serve frame 119: 11.0 ms (proxy 2.7 [copy 1.1, submit 1.5], network+composite 8.3, readback 0.0, reply 0.0)

```
