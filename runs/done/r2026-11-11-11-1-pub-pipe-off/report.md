# run r2026-11-11-11-1-pub-pipe-off

runner `415e2181914a` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 0.75 --headless --frames 300 --worker-env DLSS5VK_SERVE_SPLIT=1 --no-shm --worker-log --save-after small-pub-pipe-off-after.png`

exit **0** after 19.0s

gpu before: WARN [util 0% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 150.0 MiB); resident but not contending: msedge (pid 1300500, 823.0 MiB); resident but not contending: chromium (pid 3132450, 99.0 MiB)); after: WARN [util 0% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 150.0 MiB); resident but not contending: msedge (pid 1300500, 822.0 MiB); resident but not contending: chromium (pid 3132450, 99.0 MiB))

```
source video  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo beb5c44 (+3522 uncommitted) · worker built from patch 58e98d824bce at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 16.6s (18.07 fps headline, 24.37 fps steady), worker exit 0
timing: capture 5.4ms  send 6.7ms  recv 40.2ms  display 2.3ms   (mean 54.7ms/frame, 18.3 fps; median 41.0ms/frame, 24.4 fps steady)
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 4.5  median 6.0  max 33.4 ms at frame 132 of 300   (a one-off at frame 132 — not the warm-up, so worth looking at)
recv spread: min 18.6  median 28.2  max 3584.2 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.3  median 4.3  max 38.1 ms at frame 131 of 300   (a one-off at frame 131 — not the warm-up, so worth looking at)
  after  -> small-pub-pipe-off-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: work scale: the client's frame is 2560x1440 and the network runs at 1920x1080, so the colour is resized down on the way in and the published image back up (one bilinear dispatch each way)
[worker] serve: built from port 9d08f41 (19 modified) patch 58e98d824bce70856b56ae4c7f1456d53e1889e6
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2932 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -14.1719..0.6011 mean -1.53168; residual mean -0.0047 -0.0306 -0.0016 (rgb, head/4), logit mean -5.9793; non-finite 0 of 8294400; first 8 0.0710 0.0906 -0.2217 -3.4668 0.0382 0.0344 -0.1949 -3.6562
[worker] serve frame 0: 82.6 ms (proxy 2.6 [copy 1.6, submit 1.0], network 4.4, composite 0.1, readback 41.4, reply 6.6)
[worker] serve frame 1: 17.2 ms (proxy 2.3 [copy 1.4, submit 0.9], network 4.5, composite 0.2, readback 4.9, reply 4.5)
[worker] serve frame 2: 18.5 ms (proxy 2.3 [copy 1.4, submit 0.9], network 4.5, composite 0.2, readback 3.2, reply 7.4)
[worker] serve frame 29: 15.6 ms (proxy 2.7 [copy 1.6, submit 1.1], network 4.5, composite 0.2, readback 3.2, reply 4.4)
[worker] serve frame 59: 20.0 ms (proxy 2.3 [copy 1.3, submit 0.9], network 7.6, composite 0.5, readback 3.0, reply 6.0)
[worker] serve frame 89: 24.9 ms (proxy 3.2 [copy 1.9, submit 1.3], network 8.5, composite 0.5, readback 3.8, reply 8.2)
[worker] serve frame 119: 25.4 ms (proxy 3.3 [copy 2.0, submit 1.3], network 9.7, composite 0.5, readback 4.1, reply 7.1)
[worker] serve frame 149: 23.2 ms (proxy 2.6 [copy 1.5, submit 1.1], network 11.2, composite 0.5, readback 3.0, reply 5.2)
[worker] serve frame 179: 38.4 ms (proxy 2.3 [copy 1.4, submit 0.9], network 12.6, composite 0.5, readback 4.2, reply 17.9)
[worker] serve frame 209: 29.5 ms (proxy 3.0 [copy 1.7, submit 1.4], network 13.4, composite 0.5, readback 4.5, reply 7.1)
[worker] serve frame 239: 26.5 ms (proxy 2.5 [copy 1.5, submit 1.0], network 13.4, composite 0.5, readback 3.3, reply 6.1)
[worker] serve frame 269: 36.5 ms (proxy 2.4 [copy 1.4, submit 1.0], network 13.9, composite 0.5, readback 5.3, reply 13.3)
[worker] serve frame 299: 31.3 ms (proxy 2.8 [copy 1.7, submit 1.1], network 14.0, composite 0.5, readback 4.4, reply 9.0)
[worker] serve: input stream closed after 300 frame(s), 25.23 ms mean\n

```
