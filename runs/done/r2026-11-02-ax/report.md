# run r2026-11-02-ax

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --worker-log`

exit **0** after 8.7s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 184c38d (+20 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 7.844s (15.3 fps headline, 38.81 fps steady), worker exit 0
timing: capture 3.1ms  send 6.5ms  recv 54.0ms  display 0.0ms   (mean 63.5ms/frame, 15.7 fps; median 25.8ms/frame, 38.8 fps steady)
send spread: min 5.3  median 6.4  max 9.5 ms at frame 41 of 120   (steady — a fixed interval, not contention)
recv spread: min 15.4  median 16.4  max 4496.8 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

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
[worker] serve: warm-up 3219 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 107.9 ms (proxy 2.7 [copy 1.6, submit 1.0], network+composite 33.6, readback 71.6, reply 0.0)
[worker] serve frame 1: 17.5 ms (proxy 3.3 [copy 1.7, submit 1.6], network+composite 14.3, readback 0.0, reply 0.0)
[worker] serve frame 2: 18.2 ms (proxy 4.0 [copy 2.2, submit 1.8], network+composite 14.2, readback 0.0, reply 0.0)
[worker] serve frame 29: 15.9 ms (proxy 2.8 [copy 1.8, submit 1.0], network+composite 13.1, readback 0.0, reply 0.0)
[worker] serve frame 59: 16.0 ms (proxy 2.7 [copy 1.5, submit 1.2], network+composite 13.3, readback 0.0, reply 0.0)
[worker] serve frame 89: 16.4 ms (proxy 2.8 [copy 1.6, submit 1.2], network+composite 13.7, readback 0.0, reply 0.0)
[worker] serve frame 119: 19.0 ms (proxy 5.5 [copy 3.7, submit 1.8], network+composite 13.5, readback 0.0, reply 0.0)

```
