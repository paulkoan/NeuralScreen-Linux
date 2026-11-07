# run r2026-11-07-motionfull

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source synthetic --size 2560x1440 --headless --frames 120 --shm --motion-guides --worker-log --save-after motionfull-after.png`

exit **0** after 15.5s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 116.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 336.0 MiB)) after waiting 270s; after: WARN (resident but not contending: signal-desktop (pid 18889, 116.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 336.0 MiB))

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 786ad75 (+35 uncommitted) · worker built from patch 088280e62d50 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 13.292s (9.03 fps headline, 20.07 fps steady), worker exit 0
timing: capture 4.8ms  send 5.2ms  recv 71.2ms  display 3.9ms   (mean 85.1ms/frame, 11.8 fps; median 49.8ms/frame, 20.1 fps steady)
send spread: min 3.6  median 4.8  max 17.2 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 28.1  median 36.3  max 4156.7 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
  after  -> motionfull-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 088280e62d5047a684d65df2a3fb2dcf84d5f9d1
[worker] serve: frame channel open (29.5 MB, NeuralScreen_2604808_f0887456)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_2604808_6cc150)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3207 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 155.7 ms (proxy 10.3 [copy 8.6, submit 1.7], network+composite 56.3, readback 82.7, reply 6.5)
[worker] serve frame 1: 46.1 ms (proxy 6.9 [copy 4.5, submit 2.3], network+composite 32.0, readback 5.0, reply 2.3)
[worker] serve frame 2: 44.2 ms (proxy 5.9 [copy 4.1, submit 1.8], network+composite 30.5, readback 5.4, reply 2.4)
[worker] serve frame 29: 33.8 ms (proxy 6.7 [copy 4.6, submit 2.1], network+composite 21.2, readback 3.9, reply 1.9)
[worker] serve frame 59: 34.7 ms (proxy 7.2 [copy 4.4, submit 2.8], network+composite 19.1, readback 4.1, reply 4.3)
[worker] serve frame 89: 29.9 ms (proxy 6.1 [copy 4.3, submit 1.8], network+composite 16.6, readback 4.8, reply 2.4)
[worker] serve frame 119: 29.9 ms (proxy 4.9 [copy 3.3, submit 1.7], network+composite 19.8, readback 3.4, reply 1.9)

```
