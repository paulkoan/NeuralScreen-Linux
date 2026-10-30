# run r2026-10-30-x

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 1280x720 --worker-log`

exit **0** after 5.4s

```
source synthetic  capture 1280x720  ->  work 1280x720 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo d37b3e0 (+19 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 5.0s (24.0 fps headline, 106.58 fps steady), worker exit 0
timing: capture 0.9ms  send 2.6ms  recv 36.8ms  display 0.0ms   (mean 40.3ms/frame, 24.8 fps; median 9.4ms/frame, 106.6 fps steady)
send spread: min 2.0  median 2.5  max 3.7 ms at frame 41 of 120   (steady — a fixed interval, not contention)
recv spread: min 5.7  median 6.0  max 3673.9 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

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
[worker] serve: warm-up 2953 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -5.8320..0.6001 mean -0.72287; residual mean 0.0254 0.0122 0.0096 (rgb, head/4), logit mean -3.0800; non-finite 0 of 3686400; first 8 -0.0093 -0.0529 -0.0734 -4.5742 0.0055 -0.0467 -0.0605 -3.5469
[worker] serve frame 0: 43.8 ms (proxy 1.6 [copy 1.1, submit 0.5], network+composite 24.7, readback 17.5, reply 0.0)
[worker] serve frame 1: 6.3 ms (proxy 1.6 [copy 0.9, submit 0.7], network+composite 4.7, readback 0.0, reply 0.0)
[worker] serve frame 2: 6.2 ms (proxy 1.5 [copy 0.8, submit 0.7], network+composite 4.7, readback 0.0, reply 0.0)
[worker] serve frame 29: 5.9 ms (proxy 1.3 [copy 0.7, submit 0.6], network+composite 4.5, readback 0.0, reply 0.0)
[worker] serve frame 59: 5.8 ms (proxy 1.4 [copy 0.8, submit 0.6], network+composite 4.5, readback 0.0, reply 0.0)
[worker] serve frame 89: 5.8 ms (proxy 1.5 [copy 0.7, submit 0.7], network+composite 4.3, readback 0.0, reply 0.0)
[worker] serve frame 119: 5.8 ms (proxy 1.4 [copy 0.7, submit 0.7], network+composite 4.4, readback 0.0, reply 0.0)

```
