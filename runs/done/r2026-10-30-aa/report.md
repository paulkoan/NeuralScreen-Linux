# run r2026-10-30-aa

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 1280x720 --worker-log`

exit **0** after 5.5s

```
source synthetic  capture 1280x720  ->  work 1280x720 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 2bd942f (+19 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 5.079s (23.63 fps headline, 98.58 fps steady), worker exit 0
timing: capture 0.9ms  send 2.7ms  recv 37.3ms  display 0.0ms   (mean 40.9ms/frame, 24.4 fps; median 10.1ms/frame, 98.6 fps steady)
send spread: min 2.1  median 2.7  max 3.9 ms at frame 0 of 120   (steady — a fixed interval, not contention)
recv spread: min 5.7  median 6.5  max 3683.9 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1280x720, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2924 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -5.8320..0.6001 mean -0.72287; residual mean 0.0254 0.0122 0.0096 (rgb, head/4), logit mean -3.0800; non-finite 0 of 3686400; first 8 -0.0093 -0.0529 -0.0734 -4.5742 0.0055 -0.0467 -0.0605 -3.5469
[worker] serve frame 0: 43.0 ms (proxy 1.8 [copy 1.2, submit 0.6], network+composite 24.8, readback 16.4, reply 0.0)
[worker] serve frame 1: 7.0 ms (proxy 1.6 [copy 0.8, submit 0.8], network+composite 5.4, readback 0.0, reply 0.0)
[worker] serve frame 2: 6.2 ms (proxy 1.5 [copy 0.7, submit 0.8], network+composite 4.7, readback 0.0, reply 0.0)
[worker] serve frame 29: 7.8 ms (proxy 2.0 [copy 1.0, submit 1.0], network+composite 5.8, readback 0.0, reply 0.0)
[worker] serve frame 59: 6.7 ms (proxy 1.7 [copy 0.9, submit 0.8], network+composite 5.0, readback 0.0, reply 0.0)
[worker] serve frame 89: 5.7 ms (proxy 1.4 [copy 0.7, submit 0.7], network+composite 4.4, readback 0.0, reply 0.0)

```
