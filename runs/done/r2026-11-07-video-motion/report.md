# run r2026-11-07-video-motion

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --headless --frames 600 --shm --motion-guides --worker-log --save-after video-motion.png`

exit **0** after 55.7s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 116.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 335.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 116.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 335.0 MiB))

```
source video  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo ea6e492 (+40 uncommitted) · worker built from patch 088280e62d50 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 600 done, 0 skipped, 53.059s (11.31 fps headline, 18.8 fps steady), worker exit 0
timing: capture 9.0ms  send 3.5ms  recv 44.7ms  display 3.2ms   (mean 60.5ms/frame, 16.5 fps; median 53.2ms/frame, 18.8 fps steady)
source: replayed fixtures/stream-1440p-2s.mp4 — 601 frames decoded, 13 loops
send spread: min 2.8  median 3.4  max 17.8 ms at frame 0 of 600   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 26.3  median 38.4  max 3769.2 ms at frame 0 of 600   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.9  median 8.1  max 112.8 ms at frame 131 of 600   (a one-off at frame 131 — not the warm-up, so worth looking at)
  after  -> video-motion.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 088280e62d5047a684d65df2a3fb2dcf84d5f9d1
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3447324_dcda4fac)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3447324_9b4e7d)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2908 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -10.5703..2.1426 mean -0.54321; residual mean 0.1111 0.0057 0.1539 (rgb, head/4), logit mean -3.2555; non-finite 0 of 14745600; first 8 0.4094 0.6533 -0.3296 -0.3892 0.4255 0.6670 -0.3159 -0.2235
[worker] serve frame 0: 107.5 ms (proxy 5.3 [copy 3.8, submit 1.4], network+composite 31.9, readback 65.4, reply 4.9)
[worker] serve frame 1: 22.9 ms (proxy 4.7 [copy 3.0, submit 1.6], network+composite 12.5, readback 4.0, reply 1.7)
[worker] serve frame 2: 50.0 ms (proxy 4.6 [copy 2.9, submit 1.7], network+composite 35.9, readback 6.8, reply 2.7)
[worker] serve frame 29: 32.1 ms (proxy 5.3 [copy 3.5, submit 1.8], network+composite 21.4, readback 3.5, reply 1.9)
[worker] serve frame 59: 35.5 ms (proxy 5.7 [copy 3.5, submit 2.2], network+composite 24.7, readback 3.4, reply 1.8)
[worker] serve frame 89: 38.7 ms (proxy 5.7 [copy 3.5, submit 2.2], network+composite 27.2, readback 3.6, reply 2.3)
[worker] serve frame 119: 36.8 ms (proxy 4.6 [copy 2.8, submit 1.8], network+composite 24.4, readback 5.2, reply 2.7)
[worker] serve frame 149: 40.6 ms (proxy 5.5 [copy 3.5, submit 1.9], network+composite 29.5, readback 3.7, reply 2.0)
[worker] serve frame 179: 39.9 ms (proxy 4.9 [copy 3.2, submit 1.6], network+composite 30.1, readback 3.2, reply 1.7)
[worker] serve frame 209: 35.4 ms (proxy 5.3 [copy 3.7, submit 1.6], network+composite 25.0, readback 3.3, reply 1.8)
[worker] serve frame 239: 40.2 ms (proxy 4.3 [copy 2.8, submit 1.5], network+composite 27.7, readback 5.4, reply 2.8)
[worker] serve frame 269: 36.2 ms (proxy 5.4 [copy 3.5, submit 1.9], network+composite 25.3, readback 3.7, reply 1.8)
[worker] serve frame 299: 39.6 ms (proxy 5.2 [copy 3.4, submit 1.9], network+composite 28.9, readback 3.5, reply 1.9)
[worker] serve frame 329: 35.7 ms (proxy 5.1 [copy 3.4, submit 1.7], network+composite 25.2, readback 3.5, reply 2.0)
[worker] serve frame 359: 40.4 ms (proxy 4.5 [copy 2.8, submit 1.7], network+composite 28.7, readback 4.7, reply 2.5)
[worker] serve frame 389: 36.8 ms (proxy 5.5 [copy 3.7, submit 1.7], network+composite 26.0, readback 3.5, reply 1.7)
[worker] serve frame 419: 40.2 ms (proxy 4.8 [copy 3.2, submit 1.6], network+composite 28.9, readback 4.5, reply 2.0)
[worker] serve frame 449: 35.5 ms (proxy 5.2 [copy 3.5, submit 1.7], network+composite 25.0, readback 3.3, reply 1.9)
[worker] serve frame 479: 36.5 ms (proxy 4.6 [copy 2.9, submit 1.6], network+composite 25.6, readback 4.3, reply 2.0)
[worker] serve frame 509: 35.1 ms (proxy 5.7 [copy 3.7, submit 2.0], network+composite 24.2, readback 3.4, reply 1.8)
[worker] serve frame 539: 34.3 ms (proxy 5.0 [copy 3.2, submit 1.8], network+composite 24.3, readback 3.1, reply 2.0)
[worker] serve frame 569: 35.7 ms (proxy 5.7 [copy 3.8, submit 1.9], network+composite 25.0, readback 3.3, reply 1.7)
[worker] serve frame 599: 35.9 ms (proxy 4.3 [copy 2.8, submit 1.6], network+composite 25.1, readback 4.4, reply 2.0)

```
