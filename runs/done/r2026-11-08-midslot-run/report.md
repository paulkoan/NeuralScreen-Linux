# run r2026-11-08-midslot-run

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --headless --frames 300 --shm --worker-log --motion --interpolate --save-mid midslot-mid.png --save-after midslot-after.png`

exit **0** after 29.1s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 148.0 MiB); resident but not contending: chromium (pid 18945, 103.0 MiB); resident but not contending: msedge (pid 54723, 335.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 148.0 MiB); resident but not contending: chromium (pid 18945, 103.0 MiB); resident but not contending: msedge (pid 54723, 336.0 MiB))

```
source video  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 816219e (+44 uncommitted) · worker built from patch 91c8a0c768c0 at port 9d08f41 · OUT OF SYNC — the worker was built from patch 91c8a0c768c0, this checkout has 043fc129a2a7: re-apply the patch and rebuild, the run below is not the code in this checkout
version: OUT OF SYNC — the worker was built from patch 91c8a0c768c0, this checkout has 043fc129a2a7: re-apply the patch and rebuild, the run below is not the code in this checkout
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 300 done, 0 skipped, 25.171s (11.92 fps headline, 14.43 fps steady), worker exit 0
timing: capture 6.2ms  send 3.4ms  recv 59.7ms  display 2.9ms   (mean 83.1ms/frame, 12.0 fps; median 69.3ms/frame, 14.4 fps steady)
recv split (means): copy 2.3ms (min 1.4, max 7.6) + waiting 57.4ms   <- the copy is ours; the wait is the worker and the handoff
interp: 299 generated frames presented (11.9/s) beside 300 computed — presentation is the computed rate plus these
source: replayed fixtures/stream-1440p-2s.mp4 — 301 frames decoded, 6 loops
send spread: min 2.3  median 3.2  max 10.1 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 30.8  median 46.2  max 3964.8 ms at frame 0 of 300   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.4  median 5.1  max 52.2 ms at frame 263 of 300   (a one-off at frame 263 — not the warm-up, so worth looking at)
  after  -> midslot-after.png
  mid    -> midslot-mid.png (299 generated frames arrived; the last one)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (18 modified) patch 91c8a0c768c0900041c2b03e1317e9e3d0d82fa0
[worker] serve: frame channel open (29.5 MB, NeuralScreen_7029_c9cffc14)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_7029_56f842)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_7029_56f842m)
[worker] serve: frame 0 asked for a mid-frame and cannot have one (no history yet): the caller sees one frame per send, as before
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3056 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -10.5703..2.1426 mean -0.54321; residual mean 0.1111 0.0057 0.1539 (rgb, head/4), logit mean -3.2555; non-finite 0 of 14745600; first 8 0.4094 0.6533 -0.3296 -0.3892 0.4255 0.6670 -0.3159 -0.2235
[worker] serve frame 0: 201.8 ms (proxy 11.8 [copy 7.2, submit 4.6], network+composite 91.7, readback 93.1, reply 5.2)
[worker] serve: frame 1 carries a generated mid-frame first: half the motion, one dispatch and one 14.7MB readback (16.3 ms this frame; the run's mean is reported at the end)
[worker] serve frame 1: 129.8 ms (proxy 7.6 [copy 2.7, submit 4.9], network+composite 97.1, readback 23.7, reply 1.5)
[worker] serve frame 2: 111.0 ms (proxy 7.7 [copy 2.8, submit 4.9], network+composite 72.0, readback 28.7, reply 2.6)
[worker] serve frame 29: 39.9 ms (proxy 4.4 [copy 2.8, submit 1.5], network+composite 20.7, readback 13.3, reply 1.5)
[worker] serve frame 59: 44.0 ms (proxy 4.8 [copy 3.2, submit 1.7], network+composite 23.7, readback 13.7, reply 1.9)
[worker] serve frame 89: 49.5 ms (proxy 4.5 [copy 3.0, submit 1.5], network+composite 24.7, readback 18.3, reply 2.0)
[worker] serve frame 119: 46.8 ms (proxy 4.1 [copy 2.6, submit 1.4], network+composite 23.7, readback 17.5, reply 1.5)
[worker] serve frame 149: 43.4 ms (proxy 4.5 [copy 2.9, submit 1.5], network+composite 24.7, readback 12.7, reply 1.6)
[worker] serve frame 179: 42.7 ms (proxy 4.7 [copy 3.1, submit 1.5], network+composite 24.6, readback 11.9, reply 1.5)
[worker] serve frame 209: 43.1 ms (proxy 4.3 [copy 2.8, submit 1.6], network+composite 24.2, readback 13.0, reply 1.6)
[worker] serve frame 239: 42.4 ms (proxy 4.7 [copy 3.0, submit 1.6], network+composite 24.4, readback 11.7, reply 1.6)
[worker] serve frame 269: 33.1 ms (proxy 5.3 [copy 3.4, submit 1.8], network+composite 12.4, readback 13.7, reply 1.7)
[worker] serve frame 299: 31.6 ms (proxy 4.8 [copy 3.3, submit 1.5], network+composite 12.3, readback 12.6, reply 1.9)

```
