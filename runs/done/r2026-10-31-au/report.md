# run r2026-10-31-au

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --save-before before.png --save-after after.png --worker-log`

exit **0** after 11.1s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 4bdf513 (+20 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 9.107s (13.18 fps headline, 27.95 fps steady), worker exit 0
timing: capture 2.8ms  send 4.6ms  recv 64.8ms  display 2.2ms   (mean 74.5ms/frame, 13.4 fps; median 35.8ms/frame, 28.0 fps steady)
send spread: min 3.7  median 4.5  max 6.9 ms at frame 57 of 120   (steady — a fixed interval, not contention)
recv spread: min 24.8  median 26.3  max 4389.4 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  before -> before.png
  after  -> after.png

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
[worker] serve: warm-up 3101 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 201.4 ms (proxy 3.7 [copy 1.3, submit 2.4], network+composite 100.5, readback 88.9, reply 8.3)
[worker] serve frame 1: 91.9 ms (proxy 3.7 [copy 1.3, submit 2.4], network+composite 76.6, readback 5.4, reply 6.1)
[worker] serve frame 2: 87.7 ms (proxy 4.0 [copy 1.5, submit 2.5], network+composite 74.8, readback 3.9, reply 5.0)
[worker] serve frame 29: 22.5 ms (proxy 2.4 [copy 1.5, submit 1.0], network+composite 12.3, readback 2.9, reply 4.9)
[worker] serve frame 59: 22.5 ms (proxy 1.9 [copy 1.2, submit 0.8], network+composite 13.1, readback 2.8, reply 4.7)
[worker] serve frame 89: 24.1 ms (proxy 2.2 [copy 1.3, submit 0.9], network+composite 12.5, readback 3.6, reply 5.7)
[worker] serve frame 119: 21.9 ms (proxy 2.1 [copy 1.2, submit 0.9], network+composite 12.9, readback 2.7, reply 4.2)

```
