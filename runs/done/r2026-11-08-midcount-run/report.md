# run r2026-11-08-midcount-run

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --headless --frames 300 --shm --worker-log --motion --interpolate --save-mid midcount-mid.png --save-after midcount-after.png`

exit **0** after 29.5s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 173.0 MiB); resident but not contending: chromium (pid 18945, 114.0 MiB); resident but not contending: msedge (pid 54723, 336.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 173.0 MiB); resident but not contending: chromium (pid 18945, 110.0 MiB); resident but not contending: msedge (pid 54723, 335.0 MiB))

```
source video  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo dab7ec8 (+2851 uncommitted) · worker built from patch f2cd1f272c4c at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 24.987s (12.01 fps headline, 14.79 fps steady), worker exit 0
timing: capture 6.6ms  send 3.7ms  recv 57.2ms  display 3.4ms   (mean 82.5ms/frame, 12.1 fps; median 67.6ms/frame, 14.8 fps steady)
recv split (means): copy 2.7ms (min 1.4, max 8.8) + waiting 54.5ms   <- the copy is ours; the wait is the worker and the handoff
interp: 299 generated frames presented (12.0/s) beside 300 computed — presentation is the computed rate plus these
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 2.3  median 3.5  max 11.5 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 32.5  median 43.4  max 4082.8 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.6  median 5.6  max 34.7 ms at frame 131 of 300   (a one-off at frame 131 — not the warm-up, so worth looking at)
  after  -> midcount-after.png
  mid    -> midcount-mid.png (299 generated frames arrived; the last one)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (18 modified) patch f2cd1f272c4c4aaa27628dc19e95ef0b3a7c0e28
[worker] serve: frame channel open (29.5 MB, NeuralScreen_100299_aa670a30)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_100299_f64903)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_100299_f64903m)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: frame 0 asked for a mid-frame and cannot have one (no history yet): the caller sees one frame per send, as before
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3114 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -10.5703..2.1426 mean -0.54321; residual mean 0.1111 0.0057 0.1539 (rgb, head/4), logit mean -3.2555; non-finite 0 of 14745600; first 8 0.4094 0.6533 -0.3296 -0.3892 0.4255 0.6670 -0.3159 -0.2235
[worker] serve frame 0: 212.2 ms (proxy 18.8 [copy 14.1, submit 4.7], network+composite 95.2, readback 93.2, reply 5.1)
[worker] serve: frame 1 carries a generated mid-frame first: half the motion, one dispatch and one 14.7MB readback (21.7 ms this frame; the run's mean is reported at the end)
[worker] serve frame 1: 138.7 ms (proxy 8.1 [copy 3.5, submit 4.6], network+composite 99.1, readback 29.8, reply 1.7)
[worker] serve frame 2: 97.2 ms (proxy 7.4 [copy 2.8, submit 4.6], network+composite 73.1, readback 15.0, reply 1.7)
[worker] serve frame 29: 46.1 ms (proxy 5.1 [copy 3.2, submit 1.9], network+composite 21.8, readback 16.7, reply 2.5)
[worker] serve frame 59: 43.6 ms (proxy 6.2 [copy 4.2, submit 2.1], network+composite 23.8, readback 11.9, reply 1.7)
[worker] serve frame 89: 41.0 ms (proxy 5.0 [copy 3.3, submit 1.7], network+composite 13.1, readback 19.8, reply 3.0)
[worker] serve frame 119: 42.2 ms (proxy 6.0 [copy 4.1, submit 1.9], network+composite 12.0, readback 21.1, reply 3.0)
[worker] serve frame 149: 46.6 ms (proxy 8.9 [copy 6.1, submit 2.8], network+composite 13.7, readback 20.8, reply 3.1)
[worker] serve frame 179: 36.7 ms (proxy 4.8 [copy 3.2, submit 1.6], network+composite 12.9, readback 16.5, reply 2.5)
[worker] serve frame 209: 40.0 ms (proxy 8.7 [copy 5.3, submit 3.3], network+composite 13.0, readback 16.6, reply 1.8)
[worker] serve frame 239: 39.4 ms (proxy 7.5 [copy 4.6, submit 3.0], network+composite 17.5, readback 12.8, reply 1.5)
[worker] serve frame 269: 42.8 ms (proxy 6.8 [copy 4.8, submit 2.0], network+composite 21.0, readback 13.3, reply 1.7)
[worker] serve frame 299: 52.8 ms (proxy 5.7 [copy 3.7, submit 2.0], network+composite 23.2, readback 20.9, reply 3.0)
[worker] serve: 299 generated mid-frame(s) sent, 1 request(s) answered without one, 8.26 ms mean per mid (dispatch + readback + reply)
[worker] serve: input stream closed after 300 frame(s), 42.07 ms mean\n

```
