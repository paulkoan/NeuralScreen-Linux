# run r2026-11-08-1080p-video

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 1920x1080 --headless --frames 300 --shm --worker-log --save-after 1080p-video.png`

exit **0** after 14.0s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 152.0 MiB); resident but not contending: chromium (pid 18945, 97.0 MiB); resident but not contending: msedge (pid 54723, 335.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 152.0 MiB); resident but not contending: chromium (pid 18945, 97.0 MiB); resident but not contending: msedge (pid 54723, 336.0 MiB))

```
source video  capture 1920x1080  ->  work 1920x1080 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 57a1d43 (+48 uncommitted) · worker built from patch f2cd1f272c4c at port 9d08f41 · in sync
[main] shared memory agreed: 16.6 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 12.522s (23.96 fps headline, 36.54 fps steady), worker exit 0
timing: capture 8.7ms  send 1.6ms  recv 29.4ms  display 1.2ms   (mean 40.9ms/frame, 24.4 fps; median 27.4ms/frame, 36.5 fps steady)
recv split (means): copy 1.1ms (min 0.8, max 3.2) + waiting 28.3ms   <- the copy is ours; the wait is the worker and the handoff
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 1.2  median 1.5  max 4.3 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 15.0  median 16.7  max 3743.7 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 6.2  median 7.5  max 32.9 ms at frame 175 of 300   (a one-off at frame 175 — not the warm-up, so worth looking at)
  after  -> 1080p-video.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (18 modified) patch f2cd1f272c4c4aaa27628dc19e95ef0b3a7c0e28
[worker] serve: frame channel open (16.6 MB, NeuralScreen_269548_7c9e8a85)
[worker] serve: pixel channel open (1920x1080, 8.3 MB, NeuralScreenOut_269548_f7d6b9)
[worker] serve: mid-frame channel open (8.3 MB, NeuralScreenOut_269548_f7d6b9m)
[main] shared memory: frames in and pixels out through /dev/shm (frame 16.6MB, pixels 8.3MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2936 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -8.6875..2.1582 mean -0.80407; residual mean 0.1728 -0.0214 0.1447 (rgb, head/4), logit mean -4.4009; non-finite 0 of 8294400; first 8 0.2830 0.5894 -0.5981 -2.8066 0.2808 0.5352 -0.6294 -2.9883
[worker] serve frame 0: 74.8 ms (proxy 1.9 [copy 1.4, submit 0.5], network+composite 28.4, readback 41.3, reply 3.2)
[worker] serve frame 1: 51.2 ms (proxy 3.1 [copy 1.6, submit 1.6], network+composite 43.9, readback 3.4, reply 0.9)
[worker] serve frame 2: 17.2 ms (proxy 1.5 [copy 0.8, submit 0.7], network+composite 12.9, readback 2.0, reply 0.8)
[worker] serve frame 29: 17.3 ms (proxy 1.7 [copy 1.0, submit 0.7], network+composite 11.4, readback 2.9, reply 1.4)
[worker] serve frame 59: 16.3 ms (proxy 2.2 [copy 1.4, submit 0.8], network+composite 11.1, readback 2.2, reply 0.7)
[worker] serve frame 89: 16.1 ms (proxy 3.2 [copy 1.2, submit 2.0], network+composite 10.1, readback 1.9, reply 0.8)
[worker] serve frame 119: 15.9 ms (proxy 2.1 [copy 1.3, submit 0.8], network+composite 10.3, readback 2.6, reply 0.9)
[worker] serve frame 149: 15.4 ms (proxy 2.1 [copy 1.2, submit 0.9], network+composite 10.4, readback 2.2, reply 0.8)
[worker] serve frame 179: 15.2 ms (proxy 1.9 [copy 1.2, submit 0.8], network+composite 9.9, readback 2.3, reply 1.1)
[worker] serve frame 209: 15.5 ms (proxy 2.2 [copy 1.4, submit 0.8], network+composite 9.9, readback 2.4, reply 1.0)
[worker] serve frame 239: 14.8 ms (proxy 1.7 [copy 1.0, submit 0.7], network+composite 10.3, readback 2.1, reply 0.7)
[worker] serve frame 269: 15.8 ms (proxy 2.3 [copy 1.5, submit 0.8], network+composite 10.3, readback 2.5, reply 0.8)
[worker] serve frame 299: 14.0 ms (proxy 1.7 [copy 1.0, submit 0.7], network+composite 9.9, readback 1.7, reply 0.7)
[worker] serve: input stream closed after 300 frame(s), 15.90 ms mean\n

```
