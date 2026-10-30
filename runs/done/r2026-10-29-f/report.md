# run r2026-10-29-f

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --shm --worker-log`

exit **0** after 8.2s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 4fcea77 (+2181 uncommitted) · worker built from patch 4b934233b924 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 7.233s (16.59 fps headline, 40.48 fps steady), worker exit 0
timing: capture 2.8ms  send 2.1ms  recv 53.9ms  display 0.0ms   (mean 58.9ms/frame, 17.0 fps; median 24.7ms/frame, 40.5 fps steady)
send spread: min 1.7  median 2.0  max 10.8 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 18.8  median 19.9  max 3937.5 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (12 modified) patch 4b934233b9241aa3ea39cab42de9f9ee68ff0f29
[worker] serve: frame channel open (29.5 MB, NeuralScreen_2707567_baf7371d)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_2707567_f47a0d)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3041 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 125.0 ms (proxy 4.5, network+composite 56.4, readback 64.1, reply 0.0)
[worker] serve frame 1: 41.0 ms (proxy 5.8, network+composite 35.1, readback 0.0, reply 0.0)
[worker] serve frame 2: 40.5 ms (proxy 4.0, network+composite 36.5, readback 0.0, reply 0.0)
[worker] serve frame 29: 18.5 ms (proxy 5.8, network+composite 12.7, readback 0.0, reply 0.0)
[worker] serve frame 59: 16.4 ms (proxy 3.7, network+composite 12.7, readback 0.0, reply 0.0)
[worker] serve frame 89: 17.9 ms (proxy 5.1, network+composite 12.8, readback 0.0, reply 0.0)
[worker] serve frame 119: 16.8 ms (proxy 3.9, network+composite 12.9, readback 0.0, reply 0.0)

```
