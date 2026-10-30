# run r2026-10-30-b

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --shm --worker-log`

exit **0** after 9.2s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 47d64fb (+2202 uncommitted) · worker built from patch 4b934233b924 at port 9d08f41 · OUT OF SYNC — the worker was built from patch 4b934233b924, this checkout has 7b827810f679: re-apply the patch and rebuild, the run below is not the code in this checkout
version: OUT OF SYNC — the worker was built from patch 4b934233b924, this checkout has 7b827810f679: re-apply the patch and rebuild, the run below is not the code in this checkout
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 8.185s (14.66 fps headline, 35.17 fps steady), worker exit 0
timing: capture 3.1ms  send 2.8ms  recv 60.9ms  display 0.0ms   (mean 66.8ms/frame, 15.0 fps; median 28.4ms/frame, 35.2 fps steady)
send spread: min 1.9  median 2.6  max 10.1 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 20.0  median 22.8  max 4503.0 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (12 modified) patch 4b934233b9241aa3ea39cab42de9f9ee68ff0f29
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3419522_f3ab8bb1)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3419522_9f756e)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3545 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 146.2 ms (proxy 6.8, network+composite 66.5, readback 72.9, reply 0.0)
[worker] serve frame 1: 45.4 ms (proxy 5.8, network+composite 39.6, readback 0.0, reply 0.0)
[worker] serve frame 2: 41.5 ms (proxy 5.8, network+composite 35.6, readback 0.0, reply 0.0)
[worker] serve frame 29: 20.9 ms (proxy 7.3, network+composite 13.6, readback 0.0, reply 0.0)
[worker] serve frame 59: 18.6 ms (proxy 5.8, network+composite 12.7, readback 0.0, reply 0.0)
[worker] serve frame 89: 20.8 ms (proxy 7.8, network+composite 13.0, readback 0.0, reply 0.0)
[worker] serve frame 119: 18.7 ms (proxy 5.6, network+composite 13.1, readback 0.0, reply 0.0)

```
