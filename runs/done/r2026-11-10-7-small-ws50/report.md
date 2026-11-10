# run r2026-11-10-7-small-ws50

runner `f98364851fa4` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `28b387ec388f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 0.5 --headless --frames 300 --shm --worker-log --save-after small-ws50-after.png`

exit **0** after 15.4s

gpu before: WARN (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 283.0 MiB); resident but not contending: chromium (pid 3132450, 104.0 MiB)); after: WARN (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 282.0 MiB); resident but not contending: chromium (pid 3132450, 104.0 MiB))

```
source video  capture 2560x1440  ->  work 1280x720 (work scale 0.50, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo 5fc29e8 (+61 uncommitted) · worker built from patch f1908586c80c at port 9d08f41 · in sync
[main] shared memory agreed: 18.4 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 13.697s (21.9 fps headline, 31.9 fps steady), worker exit 0
timing: capture 6.3ms  send 2.8ms  recv 32.8ms  display 3.1ms   (mean 44.9ms/frame, 22.3 fps; median 31.3ms/frame, 31.9 fps steady)
recv split (means): copy 2.2ms (min 1.5, max 5.6) + waiting 30.6ms   <- the copy is ours; the wait is the worker and the handoff
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 1.6  median 2.7  max 32.0 ms at frame 43 of 300   (a one-off at frame 43 — not the warm-up, so worth looking at)
recv spread: min 14.2  median 19.6  max 3816.9 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.6  median 5.3  max 42.8 ms at frame 219 of 300   (a one-off at frame 219 — not the warm-up, so worth looking at)
  after  -> small-ws50-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1280x720, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: work scale: the client's frame is 2560x1440 and the network runs at 1280x720, so the colour is resized down on the way in and the published image back up (one bilinear dispatch each way)
[worker] serve: built from port 9d08f41 (19 modified) patch f1908586c80c992da865c66cb5bc196dc6121c7c
[worker] serve: frame channel open (18.4 MB, NeuralScreen_3823042_6a4d9b37)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3823042_b956ca)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_3823042_b956cam)
[main] shared memory: frames in and pixels out through /dev/shm (frame 18.4MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3073 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -14.5781..0.5703 mean -1.55466; residual mean -0.0072 -0.0313 -0.0063 (rgb, head/4), logit mean -6.0395; non-finite 0 of 3686400; first 8 0.0152 -0.0058 -0.1831 -4.2344 0.0078 -0.0031 -0.1340 -4.3281
[worker] serve frame 0: 82.9 ms (proxy 5.2 [copy 2.6, submit 2.6], network+composite 45.9, readback 26.2, reply 5.6)
[worker] serve frame 1: 29.6 ms (proxy 4.2 [copy 1.8, submit 2.4], network+composite 18.7, readback 4.9, reply 1.7)
[worker] serve frame 2: 29.7 ms (proxy 4.5 [copy 2.1, submit 2.4], network+composite 18.6, readback 4.8, reply 1.7)
[worker] serve frame 29: 14.7 ms (proxy 3.6 [copy 2.3, submit 1.3], network+composite 5.9, readback 3.5, reply 1.7)
[worker] serve frame 59: 16.3 ms (proxy 3.4 [copy 2.3, submit 1.1], network+composite 7.4, readback 3.5, reply 1.9)
[worker] serve frame 89: 15.5 ms (proxy 2.9 [copy 1.9, submit 1.0], network+composite 6.7, readback 3.9, reply 2.0)
[worker] serve frame 119: 16.5 ms (proxy 3.4 [copy 2.2, submit 1.2], network+composite 7.2, readback 3.7, reply 2.2)
[worker] serve frame 149: 19.7 ms (proxy 4.3 [copy 2.7, submit 1.5], network+composite 8.0, readback 4.7, reply 2.6)
[worker] serve frame 179: 17.1 ms (proxy 3.9 [copy 2.7, submit 1.2], network+composite 6.5, readback 4.3, reply 2.4)
[worker] serve frame 209: 17.6 ms (proxy 3.3 [copy 2.1, submit 1.2], network+composite 7.7, readback 4.5, reply 2.1)
[worker] serve frame 239: 17.0 ms (proxy 3.6 [copy 2.4, submit 1.2], network+composite 7.3, readback 3.7, reply 2.3)
[worker] serve frame 269: 18.3 ms (proxy 4.5 [copy 3.0, submit 1.5], network+composite 7.8, readback 3.8, reply 2.2)
[worker] serve frame 299: 18.9 ms (proxy 3.5 [copy 2.2, submit 1.3], network+composite 8.1, readback 4.4, reply 2.9)
[worker] serve: input stream closed after 300 frame(s), 17.98 ms mean\n

```
