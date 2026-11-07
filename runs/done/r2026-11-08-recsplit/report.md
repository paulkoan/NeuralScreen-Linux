# run r2026-11-08-recsplit

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --headless --frames 600 --shm --worker-log --save-after recsplit.png`

exit **0** after 26.9s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 148.0 MiB); resident but not contending: chromium (pid 18945, 103.0 MiB); resident but not contending: msedge (pid 54723, 336.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 148.0 MiB); resident but not contending: chromium (pid 18945, 103.0 MiB); resident but not contending: msedge (pid 54723, 335.0 MiB))

```
source video  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo bb304f3 (+42 uncommitted) · worker built from patch 088280e62d50 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 600 done, 0 skipped, 24.54s (24.45 fps headline, 30.71 fps steady), worker exit 0
timing: capture 5.8ms  send 2.4ms  recv 29.6ms  display 2.7ms   (mean 40.5ms/frame, 24.7 fps; median 32.6ms/frame, 30.7 fps steady)
recv split: copy 1.7ms (min 1.4, max 18.3) + waiting 27.9ms   <- the copy is ours; the wait is the worker and the handoff
source: replayed fixtures/stream-1440p-2s.mp4 — 601 frames decoded, 13 loops
send spread: min 1.5  median 2.2  max 51.2 ms at frame 131 of 600   (a one-off at frame 131 — not the warm-up, so worth looking at)
recv spread: min 20.4  median 22.7  max 3828.6 ms at frame 0 of 600   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.0  median 4.7  max 66.2 ms at frame 395 of 600   (a one-off at frame 395 — not the warm-up, so worth looking at)
  after  -> recsplit.png

```

stderr:

```
rker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 088280e62d5047a684d65df2a3fb2dcf84d5f9d1
[worker] serve: frame channel open (29.5 MB, NeuralScreen_4012047_3980eb84)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_4012047_e4b4bb)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2963 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -10.5703..2.1426 mean -0.54321; residual mean 0.1111 0.0057 0.1539 (rgb, head/4), logit mean -3.2555; non-finite 0 of 14745600; first 8 0.4094 0.6533 -0.3296 -0.3892 0.4255 0.6670 -0.3159 -0.2235
[worker] serve frame 0: 116.7 ms (proxy 3.2 [copy 2.2, submit 1.0], network+composite 32.7, readback 75.7, reply 5.0)
[worker] serve frame 1: 22.5 ms (proxy 3.0 [copy 1.8, submit 1.2], network+composite 12.6, readback 5.1, reply 1.7)
[worker] serve frame 2: 20.3 ms (proxy 2.7 [copy 1.7, submit 1.1], network+composite 12.6, readback 3.3, reply 1.7)
[worker] serve frame 29: 23.8 ms (proxy 3.7 [copy 2.2, submit 1.5], network+composite 12.4, readback 5.4, reply 2.4)
[worker] serve frame 59: 23.6 ms (proxy 3.0 [copy 1.9, submit 1.1], network+composite 13.3, readback 5.0, reply 2.3)
[worker] serve frame 89: 21.6 ms (proxy 3.8 [copy 2.3, submit 1.5], network+composite 12.1, readback 3.6, reply 2.2)
[worker] serve frame 119: 25.0 ms (proxy 3.8 [copy 2.5, submit 1.3], network+composite 14.1, readback 4.7, reply 2.4)
[worker] serve frame 149: 20.4 ms (proxy 3.5 [copy 2.1, submit 1.4], network+composite 12.0, readback 3.3, reply 1.6)
[worker] serve frame 179: 21.0 ms (proxy 3.2 [copy 2.0, submit 1.2], network+composite 11.8, readback 3.8, reply 2.1)
[worker] serve frame 209: 20.8 ms (proxy 2.7 [copy 1.7, submit 1.0], network+composite 11.6, readback 4.5, reply 2.0)
[worker] serve frame 239: 20.4 ms (proxy 3.4 [copy 2.3, submit 1.0], network+composite 11.6, readback 3.8, reply 1.6)
[worker] serve frame 269: 21.0 ms (proxy 3.9 [copy 2.6, submit 1.3], network+composite 11.7, readback 3.6, reply 1.7)
[worker] serve frame 299: 19.5 ms (proxy 2.8 [copy 1.7, submit 1.1], network+composite 11.6, readback 3.5, reply 1.6)
[worker] serve frame 329: 22.0 ms (proxy 4.0 [copy 2.5, submit 1.5], network+composite 11.9, readback 4.2, reply 2.0)
[worker] serve frame 359: 24.5 ms (proxy 3.5 [copy 2.4, submit 1.2], network+composite 13.5, readback 5.0, reply 2.5)
[worker] serve frame 389: 20.4 ms (proxy 2.7 [copy 1.7, submit 1.0], network+composite 11.6, readback 4.0, reply 2.1)
[worker] serve frame 419: 21.4 ms (proxy 3.0 [copy 2.0, submit 1.0], network+composite 13.0, readback 3.8, reply 1.5)
[worker] serve frame 449: 22.9 ms (proxy 3.3 [copy 2.0, submit 1.3], network+composite 13.4, readback 4.3, reply 1.9)
[worker] serve frame 479: 20.7 ms (proxy 2.6 [copy 1.6, submit 1.0], network+composite 12.1, readback 3.9, reply 2.1)
[worker] serve frame 509: 19.5 ms (proxy 2.8 [copy 1.7, submit 1.0], network+composite 11.8, readback 3.3, reply 1.6)
[worker] serve frame 539: 19.4 ms (proxy 2.8 [copy 1.7, submit 1.0], network+composite 11.7, readback 3.3, reply 1.6)
[worker] serve frame 569: 19.2 ms (proxy 2.5 [copy 1.5, submit 0.9], network+composite 11.6, readback 3.6, reply 1.6)
[worker] serve frame 599: 20.5 ms (proxy 3.0 [copy 1.9, submit 1.1], network+composite 12.4, readback 3.4, reply 1.6)

```
