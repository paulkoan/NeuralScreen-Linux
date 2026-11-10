# run r2026-11-10-9-small-ws100

runner `f98364851fa4` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `28b387ec388f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 1.0 --headless --frames 300 --shm --worker-log --save-after small-ws100-after.png`

exit **0** after 16.8s

gpu before: WARN (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 264.0 MiB); resident but not contending: chromium (pid 3132450, 104.0 MiB)) after waiting 60s; after: WARN (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 264.0 MiB); resident but not contending: chromium (pid 3132450, 104.0 MiB))

```
source video  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo f660b9a (+63 uncommitted) · worker built from patch f1908586c80c at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 14.514s (20.67 fps headline, 30.43 fps steady), worker exit 0
timing: capture 6.1ms  send 2.6ms  recv 36.2ms  display 2.8ms   (mean 47.7ms/frame, 21.0 fps; median 32.9ms/frame, 30.4 fps steady)
recv split (means): copy 2.0ms (min 1.6, max 4.0) + waiting 34.2ms   <- the copy is ours; the wait is the worker and the handoff
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 1.8  median 2.6  max 5.8 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 19.0  median 21.8  max 4033.3 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.6  median 5.0  max 37.7 ms at frame 87 of 300   (a one-off at frame 87 — not the warm-up, so worth looking at)
  after  -> small-ws100-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (19 modified) patch f1908586c80c992da865c66cb5bc196dc6121c7c
[worker] serve: frame channel open (29.5 MB, NeuralScreen_4075093_1b24042c)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_4075093_2c9193)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_4075093_2c9193m)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3022 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -14.0391..0.5762 mean -1.49363; residual mean -0.0040 -0.0286 -0.0002 (rgb, head/4), logit mean -5.8431; non-finite 0 of 14745600; first 8 0.0217 -0.0110 -0.2451 -6.3281 0.0367 0.0088 -0.2224 -6.4531
[worker] serve frame 0: 124.2 ms (proxy 3.2 [copy 2.4, submit 0.9], network+composite 44.9, readback 70.7, reply 5.3)
[worker] serve frame 1: 34.6 ms (proxy 3.4 [copy 2.1, submit 1.3], network+composite 24.9, readback 4.4, reply 1.9)
[worker] serve frame 2: 32.3 ms (proxy 2.8 [copy 1.7, submit 1.1], network+composite 24.8, readback 3.0, reply 1.7)
[worker] serve frame 29: 23.4 ms (proxy 3.0 [copy 2.0, submit 1.0], network+composite 14.1, readback 4.5, reply 1.8)
[worker] serve frame 59: 22.2 ms (proxy 3.0 [copy 1.9, submit 1.1], network+composite 12.6, readback 4.2, reply 2.4)
[worker] serve frame 89: 19.5 ms (proxy 2.7 [copy 1.7, submit 1.0], network+composite 11.1, readback 3.7, reply 1.9)
[worker] serve frame 119: 19.7 ms (proxy 3.0 [copy 1.9, submit 1.0], network+composite 11.0, readback 3.8, reply 2.0)
[worker] serve frame 149: 18.9 ms (proxy 3.1 [copy 2.0, submit 1.0], network+composite 10.6, readback 3.2, reply 2.0)
[worker] serve frame 179: 19.2 ms (proxy 2.9 [copy 1.7, submit 1.2], network+composite 11.1, readback 3.3, reply 1.9)
[worker] serve frame 209: 19.0 ms (proxy 2.6 [copy 1.7, submit 0.9], network+composite 10.2, readback 3.7, reply 2.5)
[worker] serve frame 239: 20.1 ms (proxy 3.3 [copy 2.2, submit 1.2], network+composite 10.3, readback 4.1, reply 2.4)
[worker] serve frame 269: 22.2 ms (proxy 3.5 [copy 2.0, submit 1.6], network+composite 10.7, readback 5.7, reply 2.3)
[worker] serve frame 299: 17.4 ms (proxy 2.5 [copy 1.5, submit 1.0], network+composite 10.2, readback 3.0, reply 1.6)
[worker] serve: input stream closed after 300 frame(s), 20.93 ms mean\n

```
