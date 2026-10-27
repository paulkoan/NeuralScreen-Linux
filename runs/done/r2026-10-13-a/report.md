# run r2026-10-13-a

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 30 --headless --source synthetic --size 2560x1440 --save-before before.png --save-after after.png --worker-log`

exit **0** after 8.5s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo a468ddb (+6 uncommitted) · worker built from patch f0c60a1c2224 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 30 done, 0 skipped, 6.412s (4.68 fps), worker exit 0
timing: capture 5.8ms  send 14.9ms  recv 182.2ms  display 3.6ms   (total 206.5ms/frame, 4.8 fps)
send spread: min 11.2  median 13.5  max 27.4 ms at frame 22 of 30   (a one-off at frame 22 — not the warm-up, so worth looking at)
recv spread: min 41.9  median 49.6  max 4026.4 ms at frame 0 of 30   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  before -> before.png
  after  -> after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (12 modified) patch f0c60a1c2224d1bbbe7ee86c692d391fb24359dc
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3082 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90270, non-finite 0 of 15073280; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 110.1 ms (proxy 6.7, network+composite 38.7, readback 56.9, reply 7.8)
[worker] serve frame 1: 51.2 ms (proxy 8.0, network+composite 22.6, readback 8.9, reply 11.6)
[worker] serve frame 2: 43.7 ms (proxy 9.6, network+composite 23.3, readback 4.0, reply 6.8)
[worker] serve frame 29: 49.7 ms (proxy 9.1, network+composite 19.4, readback 5.6, reply 15.6)

```
