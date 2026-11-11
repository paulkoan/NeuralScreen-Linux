# run r2026-11-11-7-ship-chain-b

runner `415e2181914a` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 0.75 --headless --frames 300 --shm --worker-env DLSS5VK_SERVE_SPLIT=1 --worker-env DLSS5VK_CHAIN_MASK=3 --worker-log --save-after small-ship-after-e.png`

exit **0** after 15.2s

gpu before: WARN [util 0% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 159.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 246.0 MiB)); after: WARN [util 5% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 159.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 291.0 MiB))

```
source video  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo a8a9465 (+68 uncommitted) · worker built from patch e2c9ae674997 at port 9d08f41 · in sync
[main] shared memory agreed: 23.0 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 13.18s (22.76 fps headline, 33.63 fps steady), worker exit 0
timing: capture 6.0ms  send 2.6ms  recv 31.6ms  display 2.7ms   (mean 43.1ms/frame, 23.2 fps; median 29.7ms/frame, 33.6 fps steady)
recv split (means): copy 1.8ms (min 1.2, max 5.5) + waiting 29.8ms   <- the copy is ours; the wait is the worker and the handoff
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 1.5  median 2.6  max 5.5 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 14.0  median 18.8  max 3707.0 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.0  median 5.1  max 34.9 ms at frame 175 of 300   (a one-off at frame 175 — not the warm-up, so worth looking at)
  after  -> small-ship-after-e.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: work scale: the client's frame is 2560x1440 and the network runs at 1920x1080, so the colour is resized down on the way in and the published image back up (one bilinear dispatch each way)
[worker] serve: built from port 9d08f41 (19 modified) patch e2c9ae6749979e22819e9c479536b0e2defd7011
[worker] serve: frame channel open (23.0 MB, NeuralScreen_791277_78a0223b)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_791277_1eab71)
[main] shared memory: frames in and pixels out through /dev/shm (frame 23.0MB, pixels 14.7MB)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_791277_1eab71m)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3007 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -14.1719..0.6011 mean -1.53168; residual mean -0.0047 -0.0306 -0.0016 (rgb, head/4), logit mean -5.9793; non-finite 0 of 8294400; first 8 0.0710 0.0906 -0.2217 -3.4668 0.0382 0.0344 -0.1949 -3.6562
[worker] serve frame 0: 91.7 ms (proxy 3.3 [copy 2.4, submit 0.8], network 4.7, composite 0.1, readback 49.5, reply 5.7)
[worker] serve frame 1: 24.3 ms (proxy 3.5 [copy 2.4, submit 1.1], network 11.8, composite 0.9, readback 5.3, reply 2.2)
[worker] serve frame 2: 23.3 ms (proxy 3.8 [copy 2.5, submit 1.3], network 11.8, composite 1.1, readback 4.2, reply 1.8)
[worker] serve frame 29: 19.5 ms (proxy 4.1 [copy 2.5, submit 1.6], network 8.8, composite 1.0, readback 3.5, reply 1.3)
[worker] serve frame 59: 19.4 ms (proxy 3.8 [copy 2.4, submit 1.3], network 8.5, composite 0.5, readback 4.0, reply 1.8)
[worker] serve frame 89: 14.3 ms (proxy 4.0 [copy 2.6, submit 1.4], network 4.4, composite 0.2, readback 3.6, reply 1.3)
[worker] serve frame 119: 19.2 ms (proxy 5.8 [copy 3.9, submit 1.9], network 5.1, composite 0.2, readback 4.6, reply 2.3)
[worker] serve frame 149: 14.7 ms (proxy 3.5 [copy 2.2, submit 1.4], network 4.4, composite 0.2, readback 3.8, reply 1.9)
[worker] serve frame 179: 15.1 ms (proxy 4.4 [copy 2.8, submit 1.6], network 4.9, composite 0.2, readback 3.6, reply 1.3)
[worker] serve frame 209: 15.5 ms (proxy 3.8 [copy 2.6, submit 1.2], network 5.9, composite 0.3, readback 3.7, reply 1.3)
[worker] serve frame 239: 18.0 ms (proxy 4.2 [copy 2.7, submit 1.4], network 6.2, composite 0.3, readback 4.2, reply 2.4)
[worker] serve frame 269: 22.0 ms (proxy 6.2 [copy 4.3, submit 1.9], network 7.3, composite 1.0, readback 4.7, reply 2.0)
[worker] serve frame 299: 16.6 ms (proxy 4.3 [copy 2.8, submit 1.5], network 4.6, composite 0.3, readback 4.3, reply 2.1)
[worker] serve: input stream closed after 300 frame(s), 17.57 ms mean\n

```
