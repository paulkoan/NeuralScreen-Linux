# run r2026-11-07-video-workerlog

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --headless --frames 600 --shm --worker-log --save-after video-workerlog.png`

exit **0** after 26.4s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 116.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 335.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 116.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 336.0 MiB))

```
source video  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo ea6e492 (+2792 uncommitted) · worker built from patch 088280e62d50 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 600 done, 0 skipped, 23.697s (25.32 fps headline, 32.0 fps steady), worker exit 0
timing: capture 5.8ms  send 1.8ms  recv 28.6ms  display 2.7ms   (mean 39.0ms/frame, 25.6 fps; median 31.2ms/frame, 32.0 fps steady)
source: replayed fixtures/stream-1440p-2s.mp4 — 601 frames decoded, 13 loops
send spread: min 1.2  median 1.7  max 4.8 ms at frame 0 of 600   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 19.1  median 21.6  max 3862.2 ms at frame 0 of 600   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 2.9  median 4.7  max 68.0 ms at frame 395 of 600   (a one-off at frame 395 — not the warm-up, so worth looking at)
  after  -> video-workerlog.png

```

stderr:

```
rker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 088280e62d5047a684d65df2a3fb2dcf84d5f9d1
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3460895_93331d62)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3460895_0d782a)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2947 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -10.5703..2.1426 mean -0.54321; residual mean 0.1111 0.0057 0.1539 (rgb, head/4), logit mean -3.2555; non-finite 0 of 14745600; first 8 0.4094 0.6533 -0.3296 -0.3892 0.4255 0.6670 -0.3159 -0.2235
[worker] serve frame 0: 187.5 ms (proxy 8.9 [copy 6.3, submit 2.6], network+composite 92.5, readback 81.2, reply 4.9)
[worker] serve frame 1: 28.9 ms (proxy 2.5 [copy 1.4, submit 1.0], network+composite 21.1, readback 4.0, reply 1.3)
[worker] serve frame 2: 31.2 ms (proxy 2.2 [copy 1.2, submit 1.0], network+composite 21.3, readback 5.1, reply 2.6)
[worker] serve frame 29: 22.2 ms (proxy 2.4 [copy 1.5, submit 1.0], network+composite 12.8, readback 5.1, reply 1.9)
[worker] serve frame 59: 19.0 ms (proxy 2.6 [copy 1.5, submit 1.1], network+composite 11.6, readback 3.4, reply 1.3)
[worker] serve frame 89: 18.4 ms (proxy 2.4 [copy 1.4, submit 1.0], network+composite 11.7, readback 3.0, reply 1.3)
[worker] serve frame 119: 18.4 ms (proxy 2.4 [copy 1.4, submit 1.0], network+composite 11.7, readback 3.0, reply 1.3)
[worker] serve frame 149: 18.9 ms (proxy 2.6 [copy 1.6, submit 1.0], network+composite 11.7, readback 3.2, reply 1.4)
[worker] serve frame 179: 19.1 ms (proxy 2.7 [copy 1.6, submit 1.1], network+composite 11.8, readback 3.4, reply 1.3)
[worker] serve frame 209: 19.2 ms (proxy 2.3 [copy 1.3, submit 0.9], network+composite 11.8, readback 3.3, reply 1.8)
[worker] serve frame 239: 23.0 ms (proxy 2.6 [copy 1.5, submit 1.0], network+composite 13.0, readback 5.0, reply 2.5)
[worker] serve frame 269: 21.4 ms (proxy 2.4 [copy 1.5, submit 0.9], network+composite 12.3, readback 4.7, reply 2.1)
[worker] serve frame 299: 19.3 ms (proxy 2.2 [copy 1.3, submit 0.9], network+composite 11.5, readback 3.6, reply 2.0)
[worker] serve frame 329: 20.7 ms (proxy 3.7 [copy 2.0, submit 1.6], network+composite 11.7, readback 3.8, reply 1.4)
[worker] serve frame 359: 19.7 ms (proxy 3.0 [copy 1.8, submit 1.1], network+composite 12.1, readback 3.3, reply 1.3)
[worker] serve frame 389: 19.0 ms (proxy 2.4 [copy 1.6, submit 0.9], network+composite 11.5, readback 3.5, reply 1.6)
[worker] serve frame 419: 18.9 ms (proxy 2.3 [copy 1.3, submit 1.0], network+composite 12.0, readback 3.3, reply 1.3)
[worker] serve frame 449: 23.5 ms (proxy 2.6 [copy 1.7, submit 0.9], network+composite 13.3, readback 5.1, reply 2.4)
[worker] serve frame 479: 19.6 ms (proxy 2.6 [copy 1.5, submit 1.1], network+composite 11.6, readback 3.8, reply 1.5)
[worker] serve frame 509: 22.9 ms (proxy 2.6 [copy 1.5, submit 1.0], network+composite 12.4, readback 5.2, reply 2.7)
[worker] serve frame 539: 21.7 ms (proxy 2.5 [copy 1.5, submit 0.9], network+composite 11.9, readback 4.7, reply 2.6)
[worker] serve frame 569: 19.5 ms (proxy 2.5 [copy 1.5, submit 0.9], network+composite 11.9, readback 3.5, reply 1.7)
[worker] serve frame 599: 21.8 ms (proxy 2.2 [copy 1.2, submit 0.9], network+composite 12.1, readback 4.9, reply 2.6)

```
