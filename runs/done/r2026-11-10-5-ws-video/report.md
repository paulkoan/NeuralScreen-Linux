# run r2026-11-10-5-ws-video

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 0.75 --headless --frames 300 --shm --worker-log --save-after ws-video-after.png`

exit **0** after 15.8s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 162.0 MiB); resident but not contending: chromium (pid 18945, 107.0 MiB); resident but not contending: msedge (pid 1300500, 436.0 MiB)) after waiting 45s; after: WARN (resident but not contending: signal-desktop (pid 18889, 162.0 MiB); resident but not contending: chromium (pid 18945, 107.0 MiB); resident but not contending: msedge (pid 1300500, 436.0 MiB))

```
source video  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 9593992 (+57 uncommitted) · worker built from patch f1908586c80c at port 9d08f41 · in sync
[main] shared memory agreed: 23.0 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 13.764s (21.8 fps headline, 33.15 fps steady), worker exit 0
timing: capture 5.9ms  send 2.6ms  recv 33.8ms  display 2.5ms   (mean 44.9ms/frame, 22.3 fps; median 30.2ms/frame, 33.2 fps steady)
recv split (means): copy 1.7ms (min 1.3, max 3.9) + waiting 32.1ms   <- the copy is ours; the wait is the worker and the handoff
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 1.5  median 2.5  max 6.3 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 17.8  median 19.8  max 4006.8 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.0  median 4.8  max 38.0 ms at frame 43 of 300   (a one-off at frame 43 — not the warm-up, so worth looking at)
  after  -> ws-video-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: work scale: the client's frame is 2560x1440 and the network runs at 1920x1080, so the colour is resized down on the way in and the published image back up (one bilinear dispatch each way)
[worker] serve: built from port 9d08f41 (19 modified) patch f1908586c80c992da865c66cb5bc196dc6121c7c
[worker] serve: frame channel open (23.0 MB, NeuralScreen_3029812_487ffbe3)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3029812_a15138)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_3029812_a15138m)
[main] shared memory: frames in and pixels out through /dev/shm (frame 23.0MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3147 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -9.6562..2.1641 mean -0.78992; residual mean 0.1679 -0.0240 0.1834 (rgb, head/4), logit mean -4.4690; non-finite 0 of 8294400; first 8 0.6870 0.5190 -0.5425 -2.6152 0.6343 0.4888 -0.5278 -2.7832
[worker] serve frame 0: 90.5 ms (proxy 4.5 [copy 3.0, submit 1.5], network+composite 37.1, readback 43.7, reply 5.3)
[worker] serve frame 1: 18.2 ms (proxy 3.0 [copy 1.9, submit 1.0], network+composite 8.9, readback 4.5, reply 1.8)
[worker] serve frame 2: 16.3 ms (proxy 2.9 [copy 1.8, submit 1.1], network+composite 8.8, readback 3.2, reply 1.5)
[worker] serve frame 29: 20.4 ms (proxy 4.5 [copy 2.8, submit 1.7], network+composite 10.1, readback 4.1, reply 1.6)
[worker] serve frame 59: 17.5 ms (proxy 2.7 [copy 1.6, submit 1.2], network+composite 9.6, readback 3.6, reply 1.5)
[worker] serve frame 89: 18.1 ms (proxy 4.2 [copy 1.8, submit 2.4], network+composite 9.5, readback 2.9, reply 1.5)
[worker] serve frame 119: 19.2 ms (proxy 3.5 [copy 2.3, submit 1.2], network+composite 10.0, readback 4.0, reply 1.7)
[worker] serve frame 149: 20.5 ms (proxy 3.4 [copy 2.2, submit 1.2], network+composite 10.0, readback 4.8, reply 2.2)
[worker] serve frame 179: 17.5 ms (proxy 3.2 [copy 2.0, submit 1.2], network+composite 9.6, readback 3.2, reply 1.4)
[worker] serve frame 209: 18.4 ms (proxy 3.6 [copy 2.1, submit 1.5], network+composite 9.1, readback 3.3, reply 2.3)
[worker] serve frame 239: 21.4 ms (proxy 4.4 [copy 2.9, submit 1.5], network+composite 10.1, readback 4.8, reply 2.2)
[worker] serve frame 269: 25.3 ms (proxy 5.1 [copy 3.1, submit 2.0], network+composite 10.3, readback 6.7, reply 3.3)
[worker] serve frame 299: 18.6 ms (proxy 4.2 [copy 2.6, submit 1.6], network+composite 9.9, readback 2.9, reply 1.6)
[worker] serve: input stream closed after 300 frame(s), 18.81 ms mean\n

```
