# run r2026-11-11-5-ship-split

runner `415e2181914a` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 0.75 --headless --frames 300 --shm --worker-env DLSS5VK_SERVE_SPLIT=1 --worker-log --save-after small-ship-after-d.png`

exit **0** after 14.8s

gpu before: WARN [util 0% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 156.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 191.0 MiB)); after: WARN [util 0% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 156.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 191.0 MiB))

```
source video  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo eb380c7 (+66 uncommitted) · worker built from patch e2c9ae674997 at port 9d08f41 · in sync
[main] shared memory agreed: 23.0 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 12.796s (23.44 fps headline, 34.45 fps steady), worker exit 0
timing: capture 5.1ms  send 2.1ms  recv 32.5ms  display 2.3ms   (mean 42.0ms/frame, 23.8 fps; median 29.0ms/frame, 34.5 fps steady)
recv split (means): copy 1.6ms (min 1.3, max 5.5) + waiting 30.9ms   <- the copy is ours; the wait is the worker and the handoff
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 1.4  median 2.1  max 5.4 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 17.5  median 20.0  max 3645.6 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 2.9  median 4.2  max 30.4 ms at frame 87 of 300   (a one-off at frame 87 — not the warm-up, so worth looking at)
  after  -> small-ship-after-d.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: work scale: the client's frame is 2560x1440 and the network runs at 1920x1080, so the colour is resized down on the way in and the published image back up (one bilinear dispatch each way)
[worker] serve: built from port 9d08f41 (19 modified) patch e2c9ae6749979e22819e9c479536b0e2defd7011
[worker] serve: frame channel open (23.0 MB, NeuralScreen_689483_6ec18d70)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_689483_6e1370)
[main] shared memory: frames in and pixels out through /dev/shm (frame 23.0MB, pixels 14.7MB)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_689483_6e1370m)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2910 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -14.1719..0.6011 mean -1.53168; residual mean -0.0047 -0.0306 -0.0016 (rgb, head/4), logit mean -5.9793; non-finite 0 of 8294400; first 8 0.0710 0.0906 -0.2217 -3.4668 0.0382 0.0344 -0.1949 -3.6562
[worker] serve frame 0: 117.1 ms (proxy 4.7 [copy 2.3, submit 2.3], network 28.6, composite 2.0, readback 49.9, reply 5.3)
[worker] serve frame 1: 48.3 ms (proxy 4.1 [copy 1.7, submit 2.4], network 30.3, composite 3.4, readback 7.6, reply 2.1)
[worker] serve frame 2: 49.3 ms (proxy 4.3 [copy 1.8, submit 2.4], network 30.4, composite 3.4, readback 6.6, reply 2.6)
[worker] serve frame 29: 18.7 ms (proxy 2.6 [copy 1.7, submit 0.9], network 9.1, composite 0.5, readback 4.2, reply 1.7)
[worker] serve frame 59: 18.7 ms (proxy 3.3 [copy 2.3, submit 1.1], network 9.2, composite 0.6, readback 3.4, reply 1.4)
[worker] serve frame 89: 17.8 ms (proxy 3.4 [copy 2.3, submit 1.1], network 8.4, composite 0.5, readback 3.4, reply 1.5)
[worker] serve frame 119: 17.9 ms (proxy 3.3 [copy 2.0, submit 1.3], network 8.2, composite 0.5, readback 3.4, reply 1.8)
[worker] serve frame 149: 20.5 ms (proxy 6.0 [copy 4.9, submit 1.1], network 8.2, composite 0.5, readback 3.4, reply 1.5)
[worker] serve frame 179: 17.4 ms (proxy 3.0 [copy 2.0, submit 1.0], network 8.4, composite 0.5, readback 3.3, reply 1.5)
[worker] serve frame 209: 19.0 ms (proxy 3.2 [copy 2.1, submit 1.1], network 8.5, composite 0.5, readback 4.0, reply 1.5)
[worker] serve frame 239: 18.7 ms (proxy 3.6 [copy 2.4, submit 1.3], network 8.5, composite 0.5, readback 3.6, reply 1.8)
[worker] serve frame 269: 17.2 ms (proxy 2.8 [copy 1.8, submit 1.0], network 8.5, composite 0.5, readback 3.3, reply 1.5)
[worker] serve frame 299: 18.9 ms (proxy 3.7 [copy 2.3, submit 1.5], network 8.6, composite 0.5, readback 3.6, reply 1.7)
[worker] serve: input stream closed after 300 frame(s), 18.98 ms mean\n

```
