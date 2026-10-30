# run r2026-10-30-a

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 30 --headless --source synthetic --size 2560x1440 --shm --worker-log --save-before before.png --save-after after.png`

exit **0** after 7.4s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 47d64fb (+12 uncommitted) · worker built from patch 4b934233b924 at port 9d08f41 · OUT OF SYNC — the worker was built from patch 4b934233b924, this checkout has 7b827810f679: re-apply the patch and rebuild, the run below is not the code in this checkout
version: OUT OF SYNC — the worker was built from patch 4b934233b924, this checkout has 7b827810f679: re-apply the patch and rebuild, the run below is not the code in this checkout
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 30 done, 0 skipped, 5.57s (5.39 fps headline, 26.59 fps steady), worker exit 0
timing: capture 3.1ms  send 2.7ms  recv 170.1ms  display 2.6ms   (mean 178.4ms/frame, 5.6 fps; median 37.6ms/frame, 26.6 fps steady)
send spread: min 1.8  median 2.5  max 10.2 ms at frame 0 of 30   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 27.0  median 29.5  max 4245.7 ms at frame 0 of 30   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  before -> before.png
  after  -> after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (12 modified) patch 4b934233b9241aa3ea39cab42de9f9ee68ff0f29
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3418539_08201071)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3418539_18e006)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3251 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 116.0 ms (proxy 6.1, network+composite 34.2, readback 70.2, reply 5.5)
[worker] serve frame 1: 27.1 ms (proxy 7.0, network+composite 14.4, readback 4.4, reply 1.4)
[worker] serve frame 2: 24.9 ms (proxy 6.0, network+composite 13.7, readback 3.8, reply 1.4)
[worker] serve frame 29: 23.4 ms (proxy 5.7, network+composite 13.2, readback 2.9, reply 1.6)

```
