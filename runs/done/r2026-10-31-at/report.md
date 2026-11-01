# run r2026-10-31-at

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 30 --headless --source synthetic --size 2560x1440 --save-before before.png --save-after after.png --worker-log`

exit **0** after 7.4s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo d666a51 (+20 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 30 done, 0 skipped, 5.568s (5.39 fps headline, 22.81 fps steady), worker exit 0
timing: capture 3.0ms  send 4.8ms  recv 169.8ms  display 2.4ms   (mean 180.1ms/frame, 5.6 fps; median 43.8ms/frame, 22.8 fps steady)
send spread: min 3.8  median 4.7  max 6.3 ms at frame 12 of 30   (steady — a fixed interval, not contention)
recv spread: min 27.9  median 33.8  max 4044.5 ms at frame 0 of 30   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
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
[worker] serve: warm-up 3030 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 156.8 ms (proxy 2.2 [copy 1.4, submit 0.8], network+composite 55.1, readback 88.9, reply 10.6)
[worker] serve frame 1: 48.4 ms (proxy 2.1 [copy 1.2, submit 0.9], network+composite 35.4, readback 5.2, reply 5.7)
[worker] serve frame 2: 46.2 ms (proxy 2.7 [copy 1.7, submit 1.0], network+composite 35.6, readback 2.6, reply 5.3)
[worker] serve frame 29: 24.9 ms (proxy 2.2 [copy 1.3, submit 0.8], network+composite 15.3, readback 2.7, reply 4.7)

```
