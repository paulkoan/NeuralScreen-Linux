# run r2026-10-30-f

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --shm --worker-log`

exit **0** after 9.6s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 5a142d8 (+12 uncommitted) · worker built from patch 7b827810f679 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 8.977s (13.37 fps headline, 30.63 fps steady), worker exit 0
timing: capture 3.4ms  send 4.2ms  recv 65.4ms  display 0.0ms   (mean 72.9ms/frame, 13.7 fps; median 32.6ms/frame, 30.6 fps steady)
send spread: min 2.7  median 3.9  max 14.0 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 22.1  median 25.4  max 4593.4 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 7b827810f679da1d16390c62e6f4677bd5688d09
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3483414_918ca787)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3483414_bf8b7c)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3573 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 139.0 ms (proxy 8.2, network+composite 59.1, readback 71.7, reply 0.0)
[worker] serve frame 1: 44.2 ms (proxy 8.7, network+composite 35.5, readback 0.0, reply 0.0)
[worker] serve frame 2: 40.7 ms (proxy 6.9, network+composite 33.7, readback 0.0, reply 0.0)
[worker] serve frame 29: 19.6 ms (proxy 6.3, network+composite 13.4, readback 0.0, reply 0.0)
[worker] serve frame 59: 19.2 ms (proxy 5.7, network+composite 13.4, readback 0.0, reply 0.0)
[worker] serve frame 89: 35.9 ms (proxy 21.3, network+composite 14.6, readback 0.0, reply 0.0)

```
