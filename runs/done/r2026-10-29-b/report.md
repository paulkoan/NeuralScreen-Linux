# run r2026-10-29-b

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --shm --send-ahead 2 --worker-log`

exit **0** after 11.0s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo bf479bd (+2148 uncommitted) · worker built from patch 819bea6f149e at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 8.621s (13.92 fps headline, 34.7 fps steady), worker exit 0
timing: capture 5.1ms  send 6.4ms  recv 58.4ms  display 0.0ms   (mean 69.9ms/frame, 14.3 fps; median 28.8ms/frame, 34.7 fps steady)
send spread: min 3.7  median 6.2  max 13.2 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 15.0  median 17.6  max 4761.6 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
capture spread: min 4.0  median 4.7  max 22.1 ms at frame 1 of 120   (a one-off at frame 1 — not the warm-up, so worth looking at)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (12 modified) patch 819bea6f149ee975b922cfea802402d1bd9b7111
[worker] serve: frame channel open (29.5 MB, NeuralScreen_2595864_d3ec3194)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_2595864_daf970)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3415 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 174.3 ms (proxy 10.0, network+composite 88.0, readback 76.3, reply 0.0)
[worker] serve frame 1: 77.9 ms (proxy 10.8, network+composite 67.1, readback 0.0, reply 0.0)
[worker] serve frame 2: 57.8 ms (proxy 11.7, network+composite 46.1, readback 0.0, reply 0.0)
[worker] serve frame 29: 21.2 ms (proxy 9.3, network+composite 11.9, readback 0.0, reply 0.0)
[worker] serve frame 59: 20.6 ms (proxy 9.0, network+composite 11.6, readback 0.0, reply 0.0)
[worker] serve frame 89: 20.9 ms (proxy 8.7, network+composite 12.2, readback 0.0, reply 0.0)
[worker] serve frame 119: 19.4 ms (proxy 7.5, network+composite 11.8, readback 0.0, reply 0.0)

```
