# run r2026-11-11-10-1-pub-on

runner `415e2181914a` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 0.75 --headless --frames 300 --worker-env DLSS5VK_SERVE_SPLIT=1 --publish-work --worker-log --save-after small-pub-on-after.png`

exit **0** after 13.9s

gpu before: WARN [util 0% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 150.0 MiB); resident but not contending: msedge (pid 1300500, 822.0 MiB); resident but not contending: chromium (pid 3132450, 99.0 MiB)); after: WARN [util 0% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 150.0 MiB); resident but not contending: msedge (pid 1300500, 823.0 MiB); resident but not contending: chromium (pid 3132450, 99.0 MiB))

```
source video  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo ab35d7e (+70 uncommitted) · worker built from patch 58e98d824bce at port 9d08f41 · in sync
[main] shared memory agreed: 23.0 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 12.376s (24.24 fps headline, 36.55 fps steady), worker exit 0
timing: capture 5.8ms  send 2.4ms  recv 29.9ms  display 2.5ms   (mean 40.6ms/frame, 24.6 fps; median 27.4ms/frame, 36.5 fps steady)
recv split (means): copy 1.6ms (min 1.2, max 4.5) + waiting 28.4ms   <- the copy is ours; the wait is the worker and the handoff
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 1.6  median 2.4  max 6.6 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 13.2  median 17.6  max 3625.8 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.5  median 4.7  max 36.9 ms at frame 175 of 300   (a one-off at frame 175 — not the warm-up, so worth looking at)
  after  -> small-pub-on-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: work scale: the client's frame is 2560x1440 and the network runs at 1920x1080, so the colour is resized down on the way in and the published image back up (one bilinear dispatch each way)
[worker] serve: publish work (DLSS5VK_PUBLISH_WORK): the image is published at 1920x1080 and the client's present does the upscale to 2560x1440
[worker] serve: built from port 9d08f41 (19 modified) patch 58e98d824bce70856b56ae4c7f1456d53e1889e6
[worker] serve: frame channel open (23.0 MB, NeuralScreen_1057267_6de40398)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_1057267_6d1455)
[main] shared memory: frames in and pixels out through /dev/shm (frame 23.0MB, pixels 14.7MB)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_1057267_6d1455m)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2922 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -14.1719..0.6011 mean -1.53168; residual mean -0.0047 -0.0306 -0.0016 (rgb, head/4), logit mean -5.9793; non-finite 0 of 8294400; first 8 0.0710 0.0906 -0.2217 -3.4668 0.0382 0.0344 -0.1949 -3.6562
[worker] serve frame 0: 81.1 ms (proxy 3.4 [copy 2.5, submit 0.9], network 4.4, composite 0.1, readback 40.7, reply 2.6)
[worker] serve frame 1: 15.5 ms (proxy 3.6 [copy 2.5, submit 1.1], network 4.4, composite 0.2, readback 5.0, reply 1.6)
[worker] serve frame 2: 14.4 ms (proxy 3.4 [copy 2.3, submit 1.2], network 4.4, composite 0.2, readback 4.4, reply 1.2)
[worker] serve frame 29: 13.9 ms (proxy 3.2 [copy 2.2, submit 1.0], network 6.4, composite 0.2, readback 2.6, reply 0.8)
[worker] serve frame 59: 15.0 ms (proxy 3.3 [copy 2.3, submit 1.0], network 7.1, composite 0.4, readback 2.7, reply 0.8)
[worker] serve frame 89: 17.3 ms (proxy 3.7 [copy 2.4, submit 1.3], network 7.5, composite 0.4, readback 3.6, reply 1.3)
[worker] serve frame 119: 15.5 ms (proxy 3.2 [copy 2.1, submit 1.1], network 7.7, composite 0.4, readback 2.6, reply 0.8)
[worker] serve frame 149: 15.7 ms (proxy 3.3 [copy 2.2, submit 1.1], network 7.9, composite 0.4, readback 2.6, reply 0.8)
[worker] serve frame 179: 15.5 ms (proxy 2.8 [copy 1.9, submit 0.9], network 8.3, composite 0.4, readback 2.5, reply 0.8)
[worker] serve frame 209: 16.5 ms (proxy 3.2 [copy 2.2, submit 1.0], network 8.7, composite 0.4, readback 2.8, reply 0.8)
[worker] serve frame 239: 17.0 ms (proxy 3.7 [copy 2.5, submit 1.1], network 8.8, composite 0.4, readback 2.6, reply 0.8)
[worker] serve frame 269: 19.7 ms (proxy 4.4 [copy 3.0, submit 1.4], network 8.7, composite 0.4, readback 4.0, reply 1.3)
[worker] serve frame 299: 15.7 ms (proxy 2.9 [copy 2.0, submit 1.0], network 8.3, composite 0.4, readback 2.7, reply 0.7)
[worker] serve: input stream closed after 300 frame(s), 16.33 ms mean\n

```
