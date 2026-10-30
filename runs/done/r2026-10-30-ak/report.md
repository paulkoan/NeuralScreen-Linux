# run r2026-10-30-ak

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 1280x720 --no-motion --worker-log`

exit **0** after 6.1s

```
source synthetic  capture 1280x720  ->  work 1280x720 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo eff8d69 (+2463 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 5.065s (23.69 fps headline, 137.79 fps steady), worker exit 0
timing: capture 0.8ms  send 1.3ms  recv 38.3ms  display 0.0ms   (mean 40.4ms/frame, 24.8 fps; median 7.3ms/frame, 137.8 fps steady)
send spread: min 0.9  median 1.2  max 2.2 ms at frame 8 of 120   (a one-off at frame 8 — not the warm-up, so worth looking at)
recv spread: min 4.9  median 5.2  max 3721.0 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1280x720, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2968 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -5.8320..0.6001 mean -0.72287; residual mean 0.0254 0.0122 0.0096 (rgb, head/4), logit mean -3.0800; non-finite 0 of 3686400; first 8 -0.0093 -0.0529 -0.0734 -4.5742 0.0055 -0.0467 -0.0605 -3.5469
[worker] serve frame 0: 61.9 ms (proxy 1.3 [copy 0.5, submit 0.8], network+composite 42.4, readback 18.2, reply 0.0)
[worker] serve frame 1: 25.4 ms (proxy 1.2 [copy 0.4, submit 0.8], network+composite 24.2, readback 0.0, reply 0.0)
[worker] serve frame 2: 25.9 ms (proxy 1.3 [copy 0.5, submit 0.9], network+composite 24.5, readback 0.0, reply 0.0)
[worker] serve frame 29: 5.2 ms (proxy 0.7 [copy 0.3, submit 0.4], network+composite 4.5, readback 0.0, reply 0.0)
[worker] serve frame 59: 5.0 ms (proxy 0.7 [copy 0.3, submit 0.4], network+composite 4.3, readback 0.0, reply 0.0)
[worker] serve frame 89: 5.1 ms (proxy 0.8 [copy 0.4, submit 0.4], network+composite 4.3, readback 0.0, reply 0.0)

```
