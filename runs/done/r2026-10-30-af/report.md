# run r2026-10-30-af

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --no-motion --worker-log`

exit **0** after 7.3s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo aacd6f4 (+19 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 6.735s (17.82 fps headline, 45.93 fps steady), worker exit 0
timing: capture 2.7ms  send 5.1ms  recv 46.5ms  display 0.0ms   (mean 54.3ms/frame, 18.4 fps; median 21.8ms/frame, 45.9 fps steady)
send spread: min 4.1  median 5.0  max 8.6 ms at frame 29 of 120   (a one-off at frame 29 — not the warm-up, so worth looking at)
recv spread: min 13.7  median 14.0  max 3763.2 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

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
[worker] serve: warm-up 2955 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 98.9 ms (proxy 2.4 [copy 1.5, submit 0.9], network+composite 32.2, readback 64.3, reply 0.0)
[worker] serve frame 1: 14.8 ms (proxy 2.5 [copy 1.5, submit 1.0], network+composite 12.4, readback 0.0, reply 0.0)
[worker] serve frame 2: 32.6 ms (proxy 2.0 [copy 1.2, submit 0.8], network+composite 30.6, readback 0.0, reply 0.0)
[worker] serve frame 29: 14.1 ms (proxy 2.4 [copy 1.5, submit 0.9], network+composite 11.7, readback 0.0, reply 0.0)
[worker] serve frame 59: 13.8 ms (proxy 2.0 [copy 1.2, submit 0.8], network+composite 11.8, readback 0.0, reply 0.0)
[worker] serve frame 89: 14.4 ms (proxy 2.2 [copy 1.3, submit 0.9], network+composite 12.2, readback 0.0, reply 0.0)

```
