# run r2026-11-11-12-1-pub-pipe-off

runner `6a0703c28681` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 0.75 --headless --frames 300 --worker-env DLSS5VK_SERVE_SPLIT=1 --no-shm --worker-log --save-after small-pub-pipe-off-b-after.png`

exit **0** after 39.7s

gpu before: BUSY [util 99% of the 25% bar] (utilization 99%; chromium (pid 77416, 268.0 MiB); signal-desktop (pid 78898, 41.0 MiB); DyingLightGame_TheBeast_x64_rwdi.exe (pid 112259, 6476.0 MiB); shelly-ui (pid 1280821, 38.0 MiB)) after waiting 298s; after: BUSY [util 82% of the 25% bar] (utilization 82%; chromium (pid 77416, 268.0 MiB); signal-desktop (pid 78898, 41.0 MiB); DyingLightGame_TheBeast_x64_rwdi.exe (pid 112259, 6476.0 MiB); shelly-ui (pid 1280821, 38.0 MiB))

```
source video  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo 77a1bd1 (+3554 uncommitted) · worker built from patch 58e98d824bce at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 33.649s (8.92 fps headline, 11.24 fps steady), worker exit 0
timing: capture 12.7ms  send 14.7ms  recv 77.3ms  display 6.3ms   (mean 111.0ms/frame, 9.0 fps; median 89.0ms/frame, 11.2 fps steady)
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 9.7  median 14.7  max 23.3 ms at frame 217 of 300   (a one-off at frame 217 — not the warm-up, so worth looking at)
recv spread: min 42.8  median 55.8  max 6464.0 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 5.1  median 12.0  max 59.4 ms at frame 87 of 300   (a one-off at frame 87 — not the warm-up, so worth looking at)
  after  -> small-pub-pipe-off-b-after.png

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
[worker] serve: warm-up 5380 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -14.1719..0.6011 mean -1.53168; residual mean -0.0047 -0.0306 -0.0016 (rgb, head/4), logit mean -5.9793; non-finite 0 of 8294400; first 8 0.0710 0.0906 -0.2217 -3.4668 0.0382 0.0344 -0.1949 -3.6562
[worker] serve frame 0: 157.3 ms (proxy 6.4 [copy 3.1, submit 3.4], network 8.0, composite 1.3, readback 74.9, reply 18.0)
[worker] serve frame 1: 48.1 ms (proxy 8.4 [copy 4.3, submit 4.0], network 9.6, composite 0.2, readback 14.2, reply 13.4)
[worker] serve frame 2: 47.2 ms (proxy 11.9 [copy 5.0, submit 6.9], network 9.5, composite 0.2, readback 9.3, reply 14.0)
[worker] serve frame 29: 48.5 ms (proxy 8.0 [copy 3.7, submit 4.3], network 9.3, composite 0.2, readback 14.6, reply 14.1)
[worker] serve frame 59: 47.4 ms (proxy 9.8 [copy 4.0, submit 5.8], network 10.3, composite 0.2, readback 8.0, reply 17.4)
[worker] serve frame 89: 40.6 ms (proxy 7.3 [copy 4.3, submit 2.9], network 4.5, composite 0.2, readback 10.4, reply 14.9)
[worker] serve frame 119: 44.0 ms (proxy 10.3 [copy 4.2, submit 6.0], network 7.7, composite 0.2, readback 9.1, reply 15.5)
[worker] serve frame 149: 54.0 ms (proxy 9.8 [copy 4.1, submit 5.7], network 9.8, composite 0.2, readback 13.1, reply 18.3)
[worker] serve frame 179: 52.3 ms (proxy 10.1 [copy 6.8, submit 3.2], network 9.7, composite 0.2, readback 12.9, reply 16.2)
[worker] serve frame 209: 41.0 ms (proxy 8.2 [copy 4.4, submit 3.7], network 9.3, composite 0.2, readback 7.5, reply 13.3)
[worker] serve frame 239: 51.5 ms (proxy 9.8 [copy 5.0, submit 4.8], network 9.4, composite 0.2, readback 14.6, reply 14.4)
[worker] serve frame 269: 49.6 ms (proxy 13.2 [copy 6.1, submit 7.1], network 8.4, composite 0.2, readback 11.3, reply 14.2)
[worker] serve frame 299: 48.9 ms (proxy 8.1 [copy 3.8, submit 4.3], network 9.5, composite 0.2, readback 14.5, reply 14.4)
[worker] serve: input stream closed after 300 frame(s), 47.23 ms mean\n

```
