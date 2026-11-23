# run r2026-11-11-14-1-pub-shm-off

runner `6a0703c28681` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 0.75 --headless --frames 300 --worker-env DLSS5VK_SERVE_SPLIT=1 --worker-log --save-after small-pub-shm14-off-after.png`

exit **0** after 33.7s

gpu before: WARN [util 22% of the 25% bar] (resident but not contending: chromium (pid 77416, 212.0 MiB); resident but not contending: signal-desktop (pid 78898, 41.0 MiB); resident but not contending: shelly-ui (pid 1280821, 38.0 MiB); resident but not contending: fossilize_replay (pid 414831, 42.0 MiB); resident but not contending: fossilize_replay (pid 414830, 40.0 MiB); resident but not contending: fossilize_replay (pid 414833, 40.0 MiB); resident but not contending: fossilize_replay (pid 414834, 40.0 MiB); resident but not contending: fossilize_replay (pid 414832, 40.0 MiB)) after waiting 75s; after: BUSY [util 29% of the 25% bar] (utilization 29%; chromium (pid 77416, 212.0 MiB); signal-desktop (pid 78898, 41.0 MiB); shelly-ui (pid 1280821, 38.0 MiB); fossilize_replay (pid 414831, 42.0 MiB); fossilize_replay (pid 414830, 40.0 MiB); fossilize_replay (pid 414833, 40.0 MiB); fossilize_replay (pid 414834, 40.0 MiB); fossilize_replay (pid 414832, 42.0 MiB))

```
source video  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo 051c131 (+3594 uncommitted) · worker built from patch 58e98d824bce at port 9d08f41 · in sync
[main] shared memory agreed: 23.0 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 29.864s (10.05 fps headline, 13.31 fps steady), worker exit 0
timing: capture 15.5ms  send 6.9ms  recv 65.4ms  display 10.2ms   (mean 98.1ms/frame, 10.2 fps; median 75.1ms/frame, 13.3 fps steady)
recv split (means): copy 6.2ms (min 2.5, max 15.7) + waiting 59.3ms   <- the copy is ours; the wait is the worker and the handoff
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 3.3  median 6.9  max 11.2 ms at frame 238 of 300   (a one-off at frame 238 — not the warm-up, so worth looking at)
recv spread: min 26.3  median 42.9  max 6822.3 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 8.1  median 14.3  max 75.3 ms at frame 175 of 300   (a one-off at frame 175 — not the warm-up, so worth looking at)
  after  -> small-pub-shm14-off-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: work scale: the client's frame is 2560x1440 and the network runs at 1920x1080, so the colour is resized down on the way in and the published image back up (one bilinear dispatch each way)
[worker] serve: built from port 9d08f41 (19 modified) patch 58e98d824bce70856b56ae4c7f1456d53e1889e6
[worker] serve: frame channel open (23.0 MB, NeuralScreen_416844_0e32b3ff)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_416844_7ca5c2)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_416844_7ca5c2m)
[main] shared memory: frames in and pixels out through /dev/shm (frame 23.0MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 5781 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -14.1719..0.6011 mean -1.53168; residual mean -0.0047 -0.0306 -0.0016 (rgb, head/4), logit mean -5.9793; non-finite 0 of 8294400; first 8 0.0710 0.0906 -0.2217 -3.4668 0.0382 0.0344 -0.1949 -3.6562
[worker] serve frame 0: 177.8 ms (proxy 12.2 [copy 8.2, submit 3.9], network 10.1, composite 0.3, readback 82.8, reply 9.5)
[worker] serve frame 1: 43.2 ms (proxy 12.0 [copy 8.0, submit 4.0], network 12.4, composite 0.5, readback 11.3, reply 4.6)
[worker] serve frame 2: 39.3 ms (proxy 10.1 [copy 6.1, submit 4.0], network 10.8, composite 0.5, readback 10.0, reply 5.5)
[worker] serve frame 29: 40.9 ms (proxy 12.6 [copy 7.5, submit 5.1], network 7.7, composite 1.3, readback 11.2, reply 5.5)
[worker] serve frame 59: 38.8 ms (proxy 10.3 [copy 6.8, submit 3.5], network 8.7, composite 0.3, readback 8.9, reply 9.0)
[worker] serve frame 89: 36.1 ms (proxy 7.9 [copy 5.3, submit 2.5], network 10.9, composite 0.9, readback 8.8, reply 5.5)
[worker] serve frame 119: 36.8 ms (proxy 8.2 [copy 5.5, submit 2.7], network 9.3, composite 0.3, readback 11.4, reply 6.2)
[worker] serve frame 149: 33.6 ms (proxy 7.9 [copy 5.8, submit 2.2], network 9.1, composite 0.5, readback 9.6, reply 4.7)
[worker] serve frame 179: 38.3 ms (proxy 9.6 [copy 6.2, submit 3.4], network 6.9, composite 0.2, readback 13.5, reply 5.6)
[worker] serve frame 209: 25.4 ms (proxy 5.9 [copy 3.8, submit 2.1], network 6.2, composite 0.2, readback 7.8, reply 3.9)
[worker] serve frame 239: 28.9 ms (proxy 7.1 [copy 5.0, submit 2.1], network 7.7, composite 0.2, readback 8.5, reply 4.0)
[worker] serve frame 269: 32.5 ms (proxy 7.6 [copy 5.7, submit 1.9], network 9.2, composite 0.5, readback 8.8, reply 5.4)
[worker] serve frame 299: 39.2 ms (proxy 8.1 [copy 5.0, submit 3.0], network 12.0, composite 0.5, readback 10.6, reply 6.0)
[worker] serve: input stream closed after 300 frame(s), 36.59 ms mean\n

```
