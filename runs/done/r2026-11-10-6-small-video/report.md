# run r2026-11-10-6-small-video

runner `f98364851fa4` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `28b387ec388f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 0.75 --headless --frames 300 --shm --worker-log --save-after small-ws-after.png`

exit **0** after 13.3s

gpu before: WARN (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 282.0 MiB); resident but not contending: chromium (pid 3132450, 104.0 MiB)); after: WARN (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 282.0 MiB); resident but not contending: chromium (pid 3132450, 104.0 MiB))

```
source video  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo 8f96f4c (+60 uncommitted) · worker built from patch f1908586c80c at port 9d08f41 · in sync
[main] shared memory agreed: 23.0 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 11.399s (26.32 fps headline, 41.58 fps steady), worker exit 0
timing: capture 4.9ms  send 2.4ms  recv 27.7ms  display 2.4ms   (mean 37.3ms/frame, 26.8 fps; median 24.1ms/frame, 41.6 fps steady)
recv split (means): copy 1.4ms (min 1.1, max 4.9) + waiting 26.3ms   <- the copy is ours; the wait is the worker and the handoff
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 1.5  median 2.4  max 6.4 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 12.7  median 14.7  max 3614.4 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 2.8  median 4.0  max 48.2 ms at frame 43 of 300   (a one-off at frame 43 — not the warm-up, so worth looking at)
  after  -> small-ws-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: work scale: the client's frame is 2560x1440 and the network runs at 1920x1080, so the colour is resized down on the way in and the published image back up (one bilinear dispatch each way)
[worker] serve: built from port 9d08f41 (19 modified) patch f1908586c80c992da865c66cb5bc196dc6121c7c
[worker] serve: frame channel open (23.0 MB, NeuralScreen_3790277_07ae9c8d)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3790277_0475c7)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_3790277_0475c7m)
[main] shared memory: frames in and pixels out through /dev/shm (frame 23.0MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2889 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -14.1719..0.6011 mean -1.53168; residual mean -0.0047 -0.0306 -0.0016 (rgb, head/4), logit mean -5.9793; non-finite 0 of 8294400; first 8 0.0710 0.0906 -0.2217 -3.4668 0.0382 0.0344 -0.1949 -3.6562
[worker] serve frame 0: 119.6 ms (proxy 4.8 [copy 2.3, submit 2.5], network+composite 59.2, readback 48.9, reply 6.7)
[worker] serve frame 1: 46.2 ms (proxy 4.5 [copy 2.1, submit 2.4], network+composite 33.6, readback 6.6, reply 1.5)
[worker] serve frame 2: 43.4 ms (proxy 4.7 [copy 2.1, submit 2.6], network+composite 33.6, readback 4.0, reply 1.1)
[worker] serve frame 29: 15.0 ms (proxy 2.9 [copy 1.9, submit 1.0], network+composite 8.1, readback 2.7, reply 1.3)
[worker] serve frame 59: 15.2 ms (proxy 2.7 [copy 1.7, submit 0.9], network+composite 8.6, readback 2.7, reply 1.2)
[worker] serve frame 89: 16.0 ms (proxy 3.2 [copy 2.1, submit 1.1], network+composite 8.7, readback 2.9, reply 1.3)
[worker] serve frame 119: 14.2 ms (proxy 3.6 [copy 2.5, submit 1.1], network+composite 5.3, readback 3.6, reply 1.7)
[worker] serve frame 149: 12.7 ms (proxy 2.9 [copy 1.9, submit 1.0], network+composite 5.2, readback 3.1, reply 1.4)
[worker] serve frame 179: 11.7 ms (proxy 2.5 [copy 1.6, submit 1.0], network+composite 5.2, readback 2.7, reply 1.2)
[worker] serve frame 209: 11.7 ms (proxy 2.5 [copy 1.6, submit 0.9], network+composite 5.1, readback 2.9, reply 1.2)
[worker] serve frame 239: 11.8 ms (proxy 2.6 [copy 1.7, submit 0.9], network+composite 5.1, readback 2.8, reply 1.3)
[worker] serve frame 269: 12.1 ms (proxy 2.6 [copy 1.6, submit 0.9], network+composite 5.2, readback 2.8, reply 1.6)
[worker] serve frame 299: 14.6 ms (proxy 3.9 [copy 2.4, submit 1.4], network+composite 5.7, readback 3.5, reply 1.6)
[worker] serve: input stream closed after 300 frame(s), 14.48 ms mean\n

```
