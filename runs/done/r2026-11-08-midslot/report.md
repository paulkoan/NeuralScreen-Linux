# run r2026-11-08-midslot

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --headless --frames 300 --shm --worker-log --motion --interpolate`

exit **0** after 13.5s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 148.0 MiB); resident but not contending: chromium (pid 18945, 103.0 MiB); resident but not contending: msedge (pid 54723, 336.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 148.0 MiB); resident but not contending: chromium (pid 18945, 103.0 MiB); resident but not contending: msedge (pid 54723, 335.0 MiB))

```
source video  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 8880bfa (+2826 uncommitted) · worker built from patch 91c8a0c768c0 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 300 done, 0 skipped, 12.356s (24.28 fps headline, 37.23 fps steady), worker exit 0
timing: capture 5.9ms  send 3.7ms  recv 30.9ms  display 0.0ms   (mean 40.5ms/frame, 24.7 fps; median 26.9ms/frame, 37.2 fps steady)
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 2.4  median 3.6  max 10.2 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 16.8  median 18.3  max 3751.2 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.3  median 4.7  max 46.4 ms at frame 219 of 300   (a one-off at frame 219 — not the warm-up, so worth looking at)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (18 modified) patch 91c8a0c768c0900041c2b03e1317e9e3d0d82fa0
[worker] serve: frame channel open (29.5 MB, NeuralScreen_4147887_47a5ee89)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_4147887_cf7110)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_4147887_cf7110m)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: frame 0 asked for a mid-frame and cannot have one (no pixels wanted): the caller sees one frame per send, as before
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2929 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -10.5703..2.1426 mean -0.54321; residual mean 0.1111 0.0057 0.1539 (rgb, head/4), logit mean -3.2555; non-finite 0 of 14745600; first 8 0.4094 0.6533 -0.3296 -0.3892 0.4255 0.6670 -0.3159 -0.2235
[worker] serve frame 0: 104.7 ms (proxy 6.0 [copy 4.1, submit 1.9], network+composite 31.7, readback 67.0, reply 0.0)
[worker] serve frame 1: 19.2 ms (proxy 6.7 [copy 4.4, submit 2.3], network+composite 12.5, readback 0.0, reply 0.0)
[worker] serve frame 2: 18.8 ms (proxy 6.4 [copy 4.1, submit 2.3], network+composite 12.4, readback 0.0, reply 0.0)
[worker] serve frame 29: 17.4 ms (proxy 5.7 [copy 3.7, submit 1.9], network+composite 11.8, readback 0.0, reply 0.0)
[worker] serve frame 59: 18.0 ms (proxy 5.5 [copy 3.7, submit 1.9], network+composite 12.4, readback 0.0, reply 0.0)
[worker] serve frame 89: 18.5 ms (proxy 5.9 [copy 4.0, submit 1.9], network+composite 12.6, readback 0.0, reply 0.0)
[worker] serve frame 119: 18.3 ms (proxy 6.4 [copy 4.4, submit 2.0], network+composite 11.9, readback 0.0, reply 0.0)
[worker] serve frame 149: 18.1 ms (proxy 6.1 [copy 3.8, submit 2.3], network+composite 11.9, readback 0.0, reply 0.0)
[worker] serve frame 179: 19.9 ms (proxy 8.0 [copy 5.5, submit 2.4], network+composite 11.9, readback 0.0, reply 0.0)
[worker] serve frame 209: 17.0 ms (proxy 5.1 [copy 3.3, submit 1.8], network+composite 11.9, readback 0.0, reply 0.0)
[worker] serve frame 239: 17.9 ms (proxy 5.7 [copy 3.8, submit 1.9], network+composite 12.2, readback 0.0, reply 0.0)
[worker] serve frame 269: 18.2 ms (proxy 5.5 [copy 3.6, submit 1.9], network+composite 12.7, readback 0.0, reply 0.0)

```
