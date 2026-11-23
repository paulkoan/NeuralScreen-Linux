# run r2026-11-11-14-0-pub-shm-on

runner `6a0703c28681` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 0.75 --headless --frames 300 --worker-env DLSS5VK_SERVE_SPLIT=1 --publish-work --worker-log --save-after small-pub-shm14-on-after.png`

exit **0** after 16.5s

gpu before: WARN [util 24% of the 25% bar] (resident but not contending: chromium (pid 77416, 212.0 MiB); resident but not contending: signal-desktop (pid 78898, 41.0 MiB); resident but not contending: DyingLightGame_TheBeast_x64_rwdi.exe (pid 112259, 316.0 MiB); resident but not contending: shelly-ui (pid 1280821, 38.0 MiB)) after waiting 15s; after: WARN [util 7% of the 25% bar] (resident but not contending: chromium (pid 77416, 212.0 MiB); resident but not contending: signal-desktop (pid 78898, 41.0 MiB); resident but not contending: DyingLightGame_TheBeast_x64_rwdi.exe (pid 112259, 316.0 MiB); resident but not contending: shelly-ui (pid 1280821, 38.0 MiB))

```
source video  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo 051c131 (+78 uncommitted) · worker built from patch 58e98d824bce at port 9d08f41 · in sync
[main] shared memory agreed: 23.0 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 14.902s (20.13 fps headline, 28.76 fps steady), worker exit 0
timing: capture 9.4ms  send 3.6ms  recv 34.0ms  display 1.9ms   (mean 48.9ms/frame, 20.4 fps; median 34.8ms/frame, 28.8 fps steady)
recv split (means): copy 1.5ms (min 0.8, max 4.3) + waiting 32.4ms   <- the copy is ours; the wait is the worker and the handoff
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 1.7  median 3.4  max 7.9 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 16.9  median 20.6  max 3938.9 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 4.9  median 8.3  max 51.4 ms at frame 131 of 300   (a one-off at frame 131 — not the warm-up, so worth looking at)
  after  -> small-pub-shm14-on-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: work scale: the client's frame is 2560x1440 and the network runs at 1920x1080, so the colour is resized down on the way in and the published image back up (one bilinear dispatch each way)
[worker] serve: publish work (DLSS5VK_PUBLISH_WORK): the image is published at 1920x1080 and the client's present does the upscale to 2560x1440
[worker] serve: built from port 9d08f41 (19 modified) patch 58e98d824bce70856b56ae4c7f1456d53e1889e6
[worker] serve: frame channel open (23.0 MB, NeuralScreen_406417_ae2ce10f)
[worker] serve: the pixel channel is 1920x1080 and this run publishes 2560x1440 frames
[worker] serve: pixel channel open (1920x1080, 8.3 MB, NeuralScreenOut_406417_ae678e)
[worker] serve: mid-frame channel open (8.3 MB, NeuralScreenOut_406417_ae678em)
[main] shared memory: frames in and pixels out through /dev/shm (frame 23.0MB, pixels 8.3MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3235 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -14.1719..0.6011 mean -1.53168; residual mean -0.0047 -0.0306 -0.0016 (rgb, head/4), logit mean -5.9793; non-finite 0 of 8294400; first 8 0.0710 0.0906 -0.2217 -3.4668 0.0382 0.0344 -0.1949 -3.6562
[worker] serve frame 0: 134.9 ms (proxy 4.3 [copy 3.1, submit 1.2], network 35.2, composite 2.0, readback 57.3, reply 3.2)
[worker] serve frame 1: 21.0 ms (proxy 6.9 [copy 4.6, submit 2.2], network 8.6, composite 0.4, readback 3.2, reply 1.0)
[worker] serve frame 2: 18.2 ms (proxy 3.7 [copy 2.3, submit 1.4], network 9.5, composite 0.4, readback 3.2, reply 0.8)
[worker] serve frame 29: 20.7 ms (proxy 4.9 [copy 3.2, submit 1.7], network 7.9, composite 0.4, readback 4.5, reply 2.2)
[worker] serve frame 59: 21.2 ms (proxy 6.9 [copy 5.5, submit 1.3], network 9.1, composite 0.4, readback 2.9, reply 0.9)
[worker] serve frame 89: 20.6 ms (proxy 4.2 [copy 2.5, submit 1.7], network 10.2, composite 0.4, readback 3.3, reply 0.8)
[worker] serve frame 119: 18.5 ms (proxy 4.2 [copy 2.5, submit 1.7], network 9.0, composite 0.4, readback 2.5, reply 0.8)
[worker] serve frame 149: 18.8 ms (proxy 4.1 [copy 2.3, submit 1.8], network 9.5, composite 0.4, readback 3.3, reply 0.6)
[worker] serve frame 179: 17.3 ms (proxy 3.3 [copy 2.1, submit 1.2], network 8.6, composite 0.5, readback 3.0, reply 1.1)
[worker] serve frame 209: 19.7 ms (proxy 5.3 [copy 3.6, submit 1.7], network 9.3, composite 0.4, readback 2.9, reply 1.0)
[worker] serve frame 239: 19.4 ms (proxy 2.9 [copy 1.9, submit 1.0], network 9.2, composite 0.4, readback 4.6, reply 1.6)
[worker] serve frame 269: 17.1 ms (proxy 3.3 [copy 2.0, submit 1.3], network 8.7, composite 1.0, readback 2.6, reply 0.7)
[worker] serve frame 299: 21.2 ms (proxy 5.7 [copy 3.5, submit 2.3], network 8.0, composite 0.4, readback 4.1, reply 2.2)
[worker] serve: input stream closed after 300 frame(s), 19.47 ms mean\n

```
