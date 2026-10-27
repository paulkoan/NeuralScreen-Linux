# run r2026-10-27-i

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 30 --headless --source synthetic --size 2560x1440 --save-before before.png --save-after after.png --worker-log`

exit **0** after 9.1s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo f202851 (+2132 uncommitted) · worker built from patch 410f0fe5de52 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 30 done, 0 skipped, 6.702s (4.48 fps), worker exit 0
timing: capture 6.5ms  send 17.3ms  recv 189.0ms  display 3.4ms   (total 216.2ms/frame, 4.6 fps)
send spread: min 10.0  median 16.2  max 33.8 ms at frame 21 of 30   (a one-off at frame 21 — not the warm-up, so worth looking at)
recv spread: min 50.4  median 61.2  max 3896.4 ms at frame 0 of 30   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  before -> before.png
  after  -> after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (12 modified) patch 410f0fe5de527ca2240a95915e7cefab474f595e
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2977 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 180.7 ms (proxy 10.0, network+composite 70.3, readback 92.6, reply 7.8)
[worker] serve frame 1: 77.2 ms (proxy 6.5, network+composite 42.0, readback 10.8, reply 18.1)
[worker] serve frame 2: 69.8 ms (proxy 6.4, network+composite 42.6, readback 5.4, reply 15.4)
[worker] serve frame 29: 54.2 ms (proxy 6.2, network+composite 26.3, readback 5.3, reply 16.4)

```
