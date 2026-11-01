# run r2026-10-31-as

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --save-after after.png --worker-log`

exit **0** after 10.6s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo b44da39 (+20 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 8.572s (14.0 fps headline, 28.03 fps steady), worker exit 0
timing: capture 2.9ms  send 4.8ms  recv 60.3ms  display 2.1ms   (mean 70.0ms/frame, 14.3 fps; median 35.7ms/frame, 28.0 fps steady)
send spread: min 4.0  median 4.5  max 8.6 ms at frame 23 of 120   (a one-off at frame 23 — not the warm-up, so worth looking at)
recv spread: min 22.8  median 26.2  max 3948.0 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
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
[worker] serve: warm-up 3031 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 129.7 ms (proxy 2.2 [copy 1.4, submit 0.8], network+composite 55.4, readback 65.4, reply 6.8)
[worker] serve frame 1: 46.0 ms (proxy 2.0 [copy 1.1, submit 0.9], network+composite 33.9, readback 4.7, reply 5.4)
[worker] serve frame 2: 46.4 ms (proxy 2.1 [copy 1.1, submit 1.0], network+composite 36.5, readback 3.0, reply 4.7)
[worker] serve frame 29: 24.3 ms (proxy 1.9 [copy 1.1, submit 0.8], network+composite 14.8, readback 3.0, reply 4.6)
[worker] serve frame 59: 21.9 ms (proxy 1.9 [copy 1.1, submit 0.8], network+composite 12.7, readback 2.8, reply 4.5)
[worker] serve frame 89: 22.1 ms (proxy 3.1 [copy 1.1, submit 1.9], network+composite 11.8, readback 2.9, reply 4.3)
[worker] serve frame 119: 20.8 ms (proxy 1.9 [copy 1.1, submit 0.7], network+composite 12.4, readback 2.8, reply 3.8)

```
