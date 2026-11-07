# run r2026-11-07-motionsmall

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source synthetic --size 2560x1440 --headless --frames 120 --shm --motion-guides --motion-small --worker-log --save-after motionsmall-after.png`

exit **0** after 14.0s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 116.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 336.0 MiB)) after waiting 30s; after: WARN (resident but not contending: signal-desktop (pid 18889, 116.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 336.0 MiB))

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 786ad75 (+2747 uncommitted) · worker built from patch 088280e62d50 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 10.604s (11.32 fps headline, 23.44 fps steady), worker exit 0
timing: capture 4.5ms  send 3.3ms  recv 66.5ms  display 4.1ms   (mean 78.4ms/frame, 12.8 fps; median 42.7ms/frame, 23.4 fps steady)
send spread: min 1.9  median 2.9  max 23.4 ms at frame 76 of 120   (a one-off at frame 76 — not the warm-up, so worth looking at)
recv spread: min 27.3  median 30.8  max 4165.6 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
  after  -> motionsmall-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 088280e62d5047a684d65df2a3fb2dcf84d5f9d1
[worker] serve: frame channel open (29.5 MB, NeuralScreen_2608631_57503316)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_2608631_2f535e)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3147 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 238.3 ms (proxy 17.9 [copy 12.0, submit 5.9], network+composite 114.5, readback 99.6, reply 6.3)
[worker] serve frame 1: 35.6 ms (proxy 5.5 [copy 3.3, submit 2.2], network+composite 22.9, readback 5.4, reply 1.9)
[worker] serve frame 2: 34.5 ms (proxy 6.2 [copy 4.6, submit 1.6], network+composite 23.0, readback 3.3, reply 2.0)
[worker] serve frame 29: 28.3 ms (proxy 6.9 [copy 4.3, submit 2.6], network+composite 16.2, readback 3.4, reply 1.8)
[worker] serve frame 59: 31.8 ms (proxy 7.9 [copy 5.3, submit 2.6], network+composite 16.6, readback 4.7, reply 2.7)
[worker] serve frame 89: 27.9 ms (proxy 6.4 [copy 4.7, submit 1.7], network+composite 13.9, readback 3.6, reply 4.0)
[worker] serve frame 119: 25.6 ms (proxy 5.4 [copy 3.3, submit 2.2], network+composite 13.3, readback 4.1, reply 2.7)

```
