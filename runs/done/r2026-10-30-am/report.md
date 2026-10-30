# run r2026-10-30-am

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --send-ahead 2 --worker-log`

exit **0** after 8.5s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 11bae32 (+2477 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 7.553s (15.89 fps headline, 35.34 fps steady), worker exit 0
timing: capture 4.5ms  send 56.7ms  recv 0.2ms  display 0.0ms   (mean 61.4ms/frame, 16.3 fps; median 28.3ms/frame, 35.3 fps steady)
send spread: min 10.2  median 23.7  max 3851.0 ms at frame 1 of 120   (a one-off at frame 1 — not the warm-up, so worth looking at)
recv spread: min 0.0  median 0.0  max 17.3 ms at frame 119 of 120   (a one-off at frame 119 — not the warm-up, so worth looking at)

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
[worker] serve: warm-up 3008 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 167.2 ms (proxy 7.6 [copy 3.1, submit 4.5], network+composite 89.7, readback 69.9, reply 0.0)
[worker] serve frame 1: 75.2 ms (proxy 8.7 [copy 4.1, submit 4.7], network+composite 66.5, readback 0.0, reply 0.0)
[worker] serve frame 2: 75.5 ms (proxy 8.9 [copy 4.1, submit 4.9], network+composite 66.6, readback 0.0, reply 0.0)
[worker] serve frame 29: 18.0 ms (proxy 6.3 [copy 4.5, submit 1.8], network+composite 11.7, readback 0.0, reply 0.0)
[worker] serve frame 59: 19.8 ms (proxy 6.9 [copy 5.2, submit 1.7], network+composite 12.9, readback 0.0, reply 0.0)
[worker] serve frame 89: 17.8 ms (proxy 6.0 [copy 4.3, submit 1.8], network+composite 11.8, readback 0.0, reply 0.0)
[worker] serve frame 119: 17.3 ms (proxy 5.5 [copy 3.5, submit 2.0], network+composite 11.9, readback 0.0, reply 0.0)

```
