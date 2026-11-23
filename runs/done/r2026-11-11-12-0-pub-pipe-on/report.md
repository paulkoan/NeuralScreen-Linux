# run r2026-11-11-12-0-pub-pipe-on

runner `6a0703c28681` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 0.75 --headless --frames 300 --worker-env DLSS5VK_SERVE_SPLIT=1 --no-shm --publish-work --worker-log --save-after small-pub-pipe-on-b-after.png`

exit **0** after 46.7s

gpu before: BUSY [util 75% of the 25% bar] (utilization 75%; chromium (pid 77416, 268.0 MiB); signal-desktop (pid 78898, 41.0 MiB); DyingLightGame_TheBeast_x64_rwdi.exe (pid 112259, 6540.0 MiB); shelly-ui (pid 1280821, 38.0 MiB)) after waiting 297s; after: BUSY [util 74% of the 25% bar] (utilization 74%; chromium (pid 77416, 269.0 MiB); signal-desktop (pid 78898, 41.0 MiB); DyingLightGame_TheBeast_x64_rwdi.exe (pid 112259, 6540.0 MiB); shelly-ui (pid 1280821, 38.0 MiB))

```
source video  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo 77a1bd1 (+74 uncommitted) · worker built from patch 58e98d824bce at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 35.538s (8.44 fps headline, 13.62 fps steady), worker exit 0
timing: capture 11.9ms  send 15.0ms  recv 87.2ms  display 3.3ms   (mean 117.5ms/frame, 8.5 fps; median 73.4ms/frame, 13.6 fps steady)
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 10.3  median 15.0  max 21.5 ms at frame 54 of 300   (a one-off at frame 54 — not the warm-up, so worth looking at)
recv spread: min 35.0  median 44.2  max 13007.3 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 5.7  median 10.7  max 69.3 ms at frame 43 of 300   (a one-off at frame 43 — not the warm-up, so worth looking at)
  after  -> small-pub-pipe-on-b-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: work scale: the client's frame is 2560x1440 and the network runs at 1920x1080, so the colour is resized down on the way in and the published image back up (one bilinear dispatch each way)
[worker] serve: publish work (DLSS5VK_PUBLISH_WORK): the image is published at 1920x1080 and the client's present does the upscale to 2560x1440
[worker] serve: built from port 9d08f41 (19 modified) patch 58e98d824bce70856b56ae4c7f1456d53e1889e6
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 8487 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -14.1719..0.6011 mean -1.53168; residual mean -0.0047 -0.0306 -0.0016 (rgb, head/4), logit mean -5.9793; non-finite 0 of 8294400; first 8 0.0710 0.0906 -0.2217 -3.4668 0.0382 0.0344 -0.1949 -3.6562
[worker] serve frame 0: 149.0 ms (proxy 8.9 [copy 5.7, submit 3.2], network 7.4, composite 0.1, readback 73.5, reply 9.9)
[worker] serve frame 1: 36.6 ms (proxy 7.3 [copy 3.9, submit 3.4], network 7.1, composite 0.2, readback 9.7, reply 9.0)
[worker] serve frame 2: 39.5 ms (proxy 10.6 [copy 6.6, submit 4.0], network 8.2, composite 0.2, readback 9.3, reply 8.6)
[worker] serve frame 29: 37.7 ms (proxy 11.5 [copy 7.6, submit 3.9], network 10.2, composite 0.2, readback 5.0, reply 8.6)
[worker] serve frame 59: 31.4 ms (proxy 6.7 [copy 3.8, submit 2.9], network 5.9, composite 0.2, readback 8.7, reply 8.4)
[worker] serve frame 89: 32.2 ms (proxy 8.0 [copy 4.5, submit 3.6], network 4.8, composite 0.2, readback 7.1, reply 10.2)
[worker] serve frame 119: 35.5 ms (proxy 9.2 [copy 5.5, submit 3.7], network 7.9, composite 0.2, readback 8.8, reply 6.7)
[worker] serve frame 149: 42.9 ms (proxy 14.9 [copy 8.9, submit 6.0], network 8.2, composite 1.8, readback 8.6, reply 7.1)
[worker] serve frame 179: 38.6 ms (proxy 10.1 [copy 4.5, submit 5.6], network 8.1, composite 1.5, readback 9.3, reply 8.1)
[worker] serve frame 209: 29.2 ms (proxy 6.5 [copy 3.8, submit 2.7], network 4.4, composite 0.2, readback 7.0, reply 9.5)
[worker] serve frame 239: 37.7 ms (proxy 10.0 [copy 6.0, submit 3.9], network 8.2, composite 1.4, readback 8.9, reply 8.0)
[worker] serve frame 269: 37.0 ms (proxy 7.9 [copy 5.2, submit 2.7], network 7.9, composite 1.5, readback 8.3, reply 9.7)
[worker] serve frame 299: 43.6 ms (proxy 13.0 [copy 8.7, submit 4.3], network 9.7, composite 0.2, readback 7.7, reply 10.1)
[worker] serve: input stream closed after 300 frame(s), 37.43 ms mean\n

```
