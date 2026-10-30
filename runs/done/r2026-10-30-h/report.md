# run r2026-10-30-h

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --shm --worker-log`

exit **0** after 8.8s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 0cbe007 (+2246 uncommitted) · worker built from patch 9e90de0d48d0 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 7.691s (15.6 fps headline, 40.7 fps steady), worker exit 0
timing: capture 3.2ms  send 2.7ms  recv 56.4ms  display 0.0ms   (mean 62.2ms/frame, 16.1 fps; median 24.6ms/frame, 40.7 fps steady)
send spread: min 1.8  median 2.5  max 10.8 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 17.7  median 19.0  max 4396.7 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 9e90de0d48d076c36b22959fc21d40d82ad62e32
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3606654_194e01b9)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3606654_6df9c3)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3355 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 146.7 ms (proxy 5.9 [copy 4.3, submit 1.6], network+composite 68.4, readback 72.3, reply 0.0)
[worker] serve frame 1: 42.6 ms (proxy 5.2 [copy 3.2, submit 1.9], network+composite 37.4, readback 0.0, reply 0.0)
[worker] serve frame 2: 39.4 ms (proxy 4.9 [copy 3.2, submit 1.7], network+composite 34.5, readback 0.0, reply 0.0)
[worker] serve frame 29: 18.7 ms (proxy 5.4 [copy 3.5, submit 1.8], network+composite 13.3, readback 0.0, reply 0.0)
[worker] serve frame 59: 19.3 ms (proxy 6.3 [copy 3.9, submit 2.4], network+composite 13.0, readback 0.0, reply 0.0)
[worker] serve frame 89: 19.7 ms (proxy 6.6 [copy 4.2, submit 2.4], network+composite 13.1, readback 0.0, reply 0.0)
[worker] serve frame 119: 20.2 ms (proxy 6.8 [copy 4.2, submit 2.6], network+composite 13.4, readback 0.0, reply 0.0)

```
