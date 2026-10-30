# run r2026-10-30-ac

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --worker-log`

exit **0** after 8.6s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 2bd942f (+2404 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 7.655s (15.68 fps headline, 34.33 fps steady), worker exit 0
timing: capture 2.8ms  send 9.9ms  recv 49.7ms  display 0.0ms   (mean 62.4ms/frame, 16.0 fps; median 29.1ms/frame, 34.3 fps steady)
send spread: min 7.8  median 9.6  max 14.3 ms at frame 1 of 120   (steady — a fixed interval, not contention)
recv spread: min 16.0  median 16.5  max 3817.8 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2976 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 171.7 ms (proxy 8.2 [copy 3.5, submit 4.6], network+composite 90.1, readback 73.5, reply 0.0)
[worker] serve frame 1: 76.4 ms (proxy 10.0 [copy 5.3, submit 4.7], network+composite 66.4, readback 0.0, reply 0.0)
[worker] serve frame 2: 57.8 ms (proxy 7.7 [copy 3.1, submit 4.5], network+composite 50.1, readback 0.0, reply 0.0)
[worker] serve frame 29: 16.3 ms (proxy 4.5 [copy 2.8, submit 1.7], network+composite 11.8, readback 0.0, reply 0.0)
[worker] serve frame 59: 16.6 ms (proxy 4.5 [copy 2.9, submit 1.6], network+composite 12.1, readback 0.0, reply 0.0)
[worker] serve frame 89: 16.3 ms (proxy 4.4 [copy 2.8, submit 1.6], network+composite 11.9, readback 0.0, reply 0.0)
[worker] serve frame 119: 16.3 ms (proxy 4.5 [copy 2.8, submit 1.7], network+composite 11.8, readback 0.0, reply 0.0)

```
