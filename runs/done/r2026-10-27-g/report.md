# run r2026-10-27-g

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 30 --headless --source synthetic --size 2560x1440 --save-before before.png --save-after after.png --worker-log`

exit **0** after 10.1s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 3d2fb08 (+2116 uncommitted) · worker built from patch d6d4664f7d19 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 30 done, 0 skipped, 6.669s (4.5 fps), worker exit 0
timing: capture 5.0ms  send 15.3ms  recv 191.0ms  display 3.8ms   (total 215.1ms/frame, 4.6 fps)
send spread: min 11.7  median 14.8  max 26.2 ms at frame 19 of 30   (a one-off at frame 19 — not the warm-up, so worth looking at)
recv spread: min 35.1  median 40.0  max 4561.6 ms at frame 0 of 30   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  before -> before.png
  after  -> after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (12 modified) patch d6d4664f7d1998aa4f5fd61043b4f438104767a4
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3249 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90270; residual mean 0.0147 0.0100 0.0109 (rgb, head/4), logit mean -3.7533; non-finite 0 of 15073280; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 192.6 ms (proxy 12.9, network+composite 99.4, readback 70.5, reply 9.8)
[worker] serve frame 1: 37.9 ms (proxy 8.7, network+composite 13.5, readback 7.3, reply 8.3)
[worker] serve frame 2: 37.0 ms (proxy 10.4, network+composite 13.8, readback 5.0, reply 7.9)
[worker] serve frame 29: 37.6 ms (proxy 8.6, network+composite 16.2, readback 4.5, reply 8.3)

```
