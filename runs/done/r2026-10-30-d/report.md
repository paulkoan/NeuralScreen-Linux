# run r2026-10-30-d

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 30 --headless --source synthetic --size 2560x1440 --shm --worker-log --save-before before.png --save-after after.png`

exit **0** after 8.4s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo dd10e53 (+12 uncommitted) · worker built from patch 7b827810f679 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 30 done, 0 skipped, 6.287s (4.77 fps headline, 19.11 fps steady), worker exit 0
timing: capture 3.9ms  send 4.7ms  recv 190.2ms  display 3.5ms   (mean 202.3ms/frame, 4.9 fps; median 52.3ms/frame, 19.1 fps steady)
send spread: min 3.1  median 4.4  max 12.2 ms at frame 0 of 30   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 34.5  median 40.2  max 4472.7 ms at frame 0 of 30   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  before -> before.png
  after  -> after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 7b827810f679da1d16390c62e6f4677bd5688d09
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3457511_036c4b16)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3457511_d0ecb0)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3387 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 162.5 ms (proxy 5.8, network+composite 59.6, readback 91.0, reply 6.0)
[worker] serve frame 1: 47.7 ms (proxy 6.3, network+composite 33.7, readback 5.4, reply 2.4)
[worker] serve frame 2: 45.2 ms (proxy 6.5, network+composite 32.0, readback 3.9, reply 2.8)
[worker] serve frame 29: 30.3 ms (proxy 5.6, network+composite 15.6, readback 6.1, reply 3.0)

```
