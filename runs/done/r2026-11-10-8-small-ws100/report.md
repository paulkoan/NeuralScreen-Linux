# run r2026-11-10-8-small-ws100

runner `f98364851fa4` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `28b387ec388f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 1.0 --headless --frames 300 --shm --worker-log --save-after small-ws100-after.png`

exit **0** after 22.3s

gpu before: BUSY (utilization 86%; Telegram (pid 16290, 30.0 MiB); signal-desktop (pid 18889, 155.0 MiB); msedge (pid 1300500, 282.0 MiB); chromium (pid 3132450, 104.0 MiB); DyingLightGame_TheBeast_x64_rwdi.exe (pid 3842045, 5518.0 MiB)) after waiting 298s; after: BUSY (utilization 98%; Telegram (pid 16290, 30.0 MiB); signal-desktop (pid 18889, 155.0 MiB); msedge (pid 1300500, 282.0 MiB); chromium (pid 3132450, 104.0 MiB); DyingLightGame_TheBeast_x64_rwdi.exe (pid 3842045, 5518.0 MiB))

```
source video  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo 4ba2204 (+62 uncommitted) · worker built from patch f1908586c80c at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 19.689s (15.24 fps headline, 20.8 fps steady), worker exit 0
timing: capture 8.9ms  send 3.4ms  recv 48.0ms  display 4.5ms   (mean 64.8ms/frame, 15.4 fps; median 48.1ms/frame, 20.8 fps steady)
recv split (means): copy 2.7ms (min 1.2, max 5.9) + waiting 45.4ms   <- the copy is ours; the wait is the worker and the handoff
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 1.6  median 3.3  max 8.4 ms at frame 270 of 300   (a one-off at frame 270 — not the warm-up, so worth looking at)
recv spread: min 25.6  median 31.8  max 4797.7 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 4.9  median 8.0  max 37.7 ms at frame 43 of 300   (a one-off at frame 43 — not the warm-up, so worth looking at)
  after  -> small-ws100-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (19 modified) patch f1908586c80c992da865c66cb5bc196dc6121c7c
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3887439_8dd9cd54)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3887439_52c96a)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_3887439_52c96am)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3820 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -14.0391..0.5762 mean -1.49363; residual mean -0.0040 -0.0286 -0.0002 (rgb, head/4), logit mean -5.8431; non-finite 0 of 14745600; first 8 0.0217 -0.0110 -0.2451 -6.3281 0.0367 0.0088 -0.2224 -6.4531
[worker] serve frame 0: 152.4 ms (proxy 3.0 [copy 1.7, submit 1.4], network+composite 51.6, readback 91.2, reply 6.6)
[worker] serve frame 1: 29.3 ms (proxy 5.1 [copy 1.4, submit 3.7], network+composite 18.2, readback 4.4, reply 1.8)
[worker] serve frame 2: 30.9 ms (proxy 5.2 [copy 2.7, submit 2.5], network+composite 16.8, readback 7.0, reply 1.9)
[worker] serve frame 29: 25.8 ms (proxy 3.3 [copy 1.7, submit 1.7], network+composite 16.0, readback 5.0, reply 1.5)
[worker] serve frame 59: 28.0 ms (proxy 6.2 [copy 3.4, submit 2.7], network+composite 15.4, readback 4.0, reply 2.4)
[worker] serve frame 89: 25.0 ms (proxy 2.7 [copy 1.6, submit 1.1], network+composite 15.4, readback 5.2, reply 1.8)
[worker] serve frame 119: 30.1 ms (proxy 6.6 [copy 3.1, submit 3.5], network+composite 15.8, readback 4.0, reply 3.7)
[worker] serve frame 149: 30.2 ms (proxy 6.1 [copy 2.9, submit 3.1], network+composite 15.3, readback 5.3, reply 3.5)
[worker] serve frame 179: 28.7 ms (proxy 5.1 [copy 1.5, submit 3.6], network+composite 18.7, readback 3.5, reply 1.4)
[worker] serve frame 209: 26.5 ms (proxy 5.6 [copy 2.3, submit 3.3], network+composite 15.8, readback 3.3, reply 1.9)
[worker] serve frame 239: 29.9 ms (proxy 5.7 [copy 2.9, submit 2.8], network+composite 16.4, readback 4.0, reply 3.8)
[worker] serve frame 269: 31.1 ms (proxy 7.2 [copy 3.8, submit 3.3], network+composite 17.0, readback 5.4, reply 1.5)
[worker] serve frame 299: 32.8 ms (proxy 7.1 [copy 3.5, submit 3.6], network+composite 17.4, readback 6.3, reply 2.0)
[worker] serve: input stream closed after 300 frame(s), 29.62 ms mean\n

```
