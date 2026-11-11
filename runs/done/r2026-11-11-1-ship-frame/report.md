# run r2026-11-11-1-ship-frame

runner `415e2181914a` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 0.75 --headless --frames 300 --shm --worker-log --save-after small-ship-after.png`

exit **0** after 17.0s

gpu before: WARN [util 1% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 167.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 220.0 MiB)); after: WARN [util 13% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 156.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 250.0 MiB))

```
source video  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo 3b360b2 (+63 uncommitted) · worker built from patch e2c9ae674997 at port 9d08f41 · in sync
[main] shared memory agreed: 23.0 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 14.503s (20.69 fps headline, 30.59 fps steady), worker exit 0
timing: capture 5.9ms  send 2.8ms  recv 35.9ms  display 2.9ms   (mean 47.5ms/frame, 21.1 fps; median 32.7ms/frame, 30.6 fps steady)
recv split (means): copy 2.1ms (min 1.4, max 4.9) + waiting 33.9ms   <- the copy is ours; the wait is the worker and the handoff
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 1.6  median 2.7  max 6.6 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 17.8  median 22.1  max 4115.4 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.1  median 4.9  max 39.0 ms at frame 43 of 300   (a one-off at frame 43 — not the warm-up, so worth looking at)
  after  -> small-ship-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: work scale: the client's frame is 2560x1440 and the network runs at 1920x1080, so the colour is resized down on the way in and the published image back up (one bilinear dispatch each way)
[worker] serve: built from port 9d08f41 (19 modified) patch e2c9ae6749979e22819e9c479536b0e2defd7011
[worker] serve: frame channel open (23.0 MB, NeuralScreen_573527_26c8eaaf)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_573527_ec9cf6)
[main] shared memory: frames in and pixels out through /dev/shm (frame 23.0MB, pixels 14.7MB)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_573527_ec9cf6m)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3085 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -14.1719..0.6011 mean -1.53168; residual mean -0.0047 -0.0306 -0.0016 (rgb, head/4), logit mean -5.9793; non-finite 0 of 8294400; first 8 0.0710 0.0906 -0.2217 -3.4668 0.0382 0.0344 -0.1949 -3.6562
[worker] serve frame 0: 89.8 ms (proxy 3.5 [copy 2.5, submit 1.0], network+composite 36.0, readback 44.8, reply 5.4)
[worker] serve frame 1: 20.4 ms (proxy 5.2 [copy 3.4, submit 1.8], network+composite 9.0, readback 4.6, reply 1.6)
[worker] serve frame 2: 16.6 ms (proxy 3.1 [copy 2.1, submit 1.1], network+composite 8.4, readback 3.3, reply 1.8)
[worker] serve frame 29: 17.7 ms (proxy 2.9 [copy 1.8, submit 1.1], network+composite 8.9, readback 4.2, reply 1.7)
[worker] serve frame 59: 20.5 ms (proxy 4.6 [copy 3.3, submit 1.3], network+composite 9.6, readback 4.1, reply 2.2)
[worker] serve frame 89: 21.4 ms (proxy 4.1 [copy 2.5, submit 1.7], network+composite 9.6, readback 4.8, reply 2.8)
[worker] serve frame 119: 19.6 ms (proxy 3.2 [copy 2.1, submit 1.0], network+composite 8.6, readback 5.2, reply 2.6)
[worker] serve frame 149: 19.3 ms (proxy 3.8 [copy 2.4, submit 1.4], network+composite 9.7, readback 3.7, reply 2.1)
[worker] serve frame 179: 23.4 ms (proxy 6.7 [copy 4.4, submit 2.3], network+composite 8.7, readback 5.4, reply 2.6)
[worker] serve frame 209: 16.2 ms (proxy 3.2 [copy 1.9, submit 1.3], network+composite 7.3, readback 3.8, reply 1.9)
[worker] serve frame 239: 21.1 ms (proxy 4.4 [copy 2.9, submit 1.6], network+composite 9.8, readback 4.8, reply 2.0)
[worker] serve frame 269: 21.9 ms (proxy 4.3 [copy 3.0, submit 1.3], network+composite 9.0, readback 5.6, reply 3.0)
[worker] serve frame 299: 20.3 ms (proxy 4.6 [copy 3.4, submit 1.2], network+composite 9.0, readback 5.0, reply 1.7)
[worker] serve: input stream closed after 300 frame(s), 20.23 ms mean\n

```
