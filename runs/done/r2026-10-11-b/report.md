# run r2026-10-11-b

`uv run python -m minimal --source image --input-image fixtures/youtube-1440p.png --headless --frames 60 --worker-log --shm --no-motion --send-ahead 2`

exit **0** after 6.7s

```
source image (fixtures/youtube-1440p.png)  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /home/paul/dev/OpenDLSS-NR/build/dlss5vk serve --model /home/paul/dev/odl-model
version: repo a3c205f (+2 uncommitted) · worker built from patch ea90414e2b00 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 60 done, 0 skipped, 5.99s (10.02 fps), worker exit 0
timing: capture 2.1ms  send 2.2ms  recv 87.3ms  display 4.6ms   (total 96.2ms/frame, 10.4 fps)
send spread: min 1.5  median 2.1  max 6.9 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 15.9  median 18.6  max 4066.6 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /home/paul/dev/odl-model, shaders /home/paul/dev/OpenDLSS-NR/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (11 modified) patch ea90414e2b0055cd1e7477c260e98faf3bb84571
[worker] serve: frame channel open (29.5 MB, NeuralScreen_2875314_78493f57)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_2875314_b9cde7)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field (nothing here reads one)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3125 ms
[worker] serve: frame 0 carries reset (no history is kept, so it is a no-op)
[worker] serve: head -8.7188..0.7407 mean -1.05684, non-finite 0 of 15073280; first 8 0.0334 0.0340 0.0328 -4.8047 0.0280 0.0312 0.0285 -4.6172
[worker] serve frame 0: 98.8 ms (proxy 2.8, network+composite 36.6, readback 53.8, reply 5.6)
[worker] serve frame 1: 43.0 ms (proxy 4.1, network+composite 30.0, readback 6.5, reply 2.4)
[worker] serve frame 2: 43.0 ms (proxy 7.0, network+composite 29.1, readback 4.5, reply 2.3)
[worker] serve frame 29: 22.2 ms (proxy 4.0, network+composite 12.8, readback 3.2, reply 2.2)
[worker] serve frame 59: 23.5 ms (proxy 5.4, network+composite 12.5, readback 3.6, reply 2.1)

```
