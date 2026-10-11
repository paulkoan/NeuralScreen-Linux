# run r2026-10-11-e

`uv run python -m minimal --source image --input-image fixtures/youtube-1440p.png --headless --size 1280x720 --frames 60 --worker-log --shm --no-motion --send-ahead 2`

exit **0** after 6.8s

```
source image (fixtures/youtube-1440p.png)  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /home/paul/dev/OpenDLSS-NR/build/dlss5vk serve --model /home/paul/dev/odl-model
version: repo 46c44cf (+4 uncommitted) · worker built from patch ea90414e2b00 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 60 done, 0 skipped, 6.116s (9.81 fps), worker exit 0
timing: capture 2.1ms  send 1.9ms  recv 90.0ms  display 5.0ms   (total 99.1ms/frame, 10.1 fps)
send spread: min 1.1  median 1.8  max 5.3 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 15.9  median 19.4  max 4199.5 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /home/paul/dev/odl-model, shaders /home/paul/dev/OpenDLSS-NR/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (11 modified) patch ea90414e2b0055cd1e7477c260e98faf3bb84571
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3261238_f5893ec6)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3261238_4300ef)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field (nothing here reads one)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3218 ms
[worker] serve: frame 0 carries reset (no history is kept, so it is a no-op)
[worker] serve: head -8.7188..0.7407 mean -1.05684, non-finite 0 of 15073280; first 8 0.0334 0.0340 0.0328 -4.8047 0.0280 0.0312 0.0285 -4.6172
[worker] serve frame 0: 109.0 ms (proxy 7.3, network+composite 37.2, readback 57.8, reply 6.7)
[worker] serve frame 1: 41.6 ms (proxy 4.7, network+composite 31.3, readback 4.2, reply 1.4)
[worker] serve frame 2: 33.4 ms (proxy 4.6, network+composite 24.0, readback 3.6, reply 1.2)
[worker] serve frame 29: 26.2 ms (proxy 5.5, network+composite 14.9, readback 4.0, reply 1.8)
[worker] serve frame 59: 23.7 ms (proxy 4.6, network+composite 12.8, readback 4.6, reply 1.7)

```
