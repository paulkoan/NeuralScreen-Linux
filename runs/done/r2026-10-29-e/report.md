# run r2026-10-29-e

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 30 --headless --source synthetic --size 2560x1440 --save-before before.png --save-after after.png --worker-log`

exit **0** after 9.8s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 4fcea77 (+2172 uncommitted) · worker built from patch 4b934233b924 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 30 done, 0 skipped, 6.379s (4.7 fps headline, 19.83 fps steady), worker exit 0
timing: capture 3.2ms  send 10.3ms  recv 191.2ms  display 2.4ms   (mean 207.1ms/frame, 4.8 fps; median 50.4ms/frame, 19.8 fps steady)
send spread: min 8.6  median 10.1  max 14.3 ms at frame 13 of 30   (steady — a fixed interval, not contention)
recv spread: min 30.0  median 34.4  max 4676.7 ms at frame 0 of 30   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  before -> before.png
  after  -> after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (12 modified) patch 4b934233b9241aa3ea39cab42de9f9ee68ff0f29
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3277 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 154.7 ms (proxy 5.2, network+composite 71.3, readback 70.9, reply 7.3)
[worker] serve frame 1: 48.3 ms (proxy 6.3, network+composite 33.6, readback 4.0, reply 4.4)
[worker] serve frame 2: 47.8 ms (proxy 6.4, network+composite 33.3, readback 2.7, reply 5.4)
[worker] serve frame 29: 30.1 ms (proxy 6.4, network+composite 15.3, readback 3.1, reply 5.2)

```
