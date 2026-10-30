# run r2026-10-30-ad

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 30 --headless --source synthetic --size 2560x1440 --save-after after.png --worker-log`

exit **0** after 7.2s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 0273a63 (+19 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 30 done, 0 skipped, 5.5s (5.45 fps headline, 21.13 fps steady), worker exit 0
timing: capture 3.2ms  send 11.2ms  recv 159.7ms  display 2.0ms   (mean 176.1ms/frame, 5.7 fps; median 47.3ms/frame, 21.1 fps steady)
send spread: min 9.3  median 11.1  max 15.1 ms at frame 16 of 30   (steady — a fixed interval, not contention)
recv spread: min 29.3  median 30.8  max 3803.6 ms at frame 0 of 30   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  after  -> after.png

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
[worker] serve: warm-up 2958 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 116.8 ms (proxy 4.7 [copy 3.1, submit 1.7], network+composite 32.6, readback 70.8, reply 8.7)
[worker] serve frame 1: 28.1 ms (proxy 5.5 [copy 3.6, submit 1.9], network+composite 12.4, readback 4.2, reply 6.1)
[worker] serve frame 2: 85.3 ms (proxy 8.1 [copy 3.4, submit 4.7], network+composite 67.2, readback 4.4, reply 5.6)
[worker] serve frame 29: 27.4 ms (proxy 4.7 [copy 2.9, submit 1.8], network+composite 15.1, readback 2.7, reply 4.9)

```
