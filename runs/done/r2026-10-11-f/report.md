# run r2026-10-11-f

`uv run python -m minimal --source image --input-image fixtures/youtube-720p.png --headless --frames 60 --worker-log --shm --no-motion --send-ahead 2`

exit **0** after 5.1s

```
source image (fixtures/youtube-720p.png)  capture 1280x720  ->  work 1280x720 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /home/paul/dev/OpenDLSS-NR/build/dlss5vk serve --model /home/paul/dev/odl-model
version: repo 5b056de (+4 uncommitted) · worker built from patch ea90414e2b00 at port 9d08f41 · in sync
[main] shared memory agreed: 7.4 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 60 done, 0 skipped, 4.518s (13.28 fps), worker exit 0
timing: capture 0.8ms  send 0.6ms  recv 70.1ms  display 1.0ms   (total 72.5ms/frame, 13.8 fps)
send spread: min 0.3  median 0.5  max 1.2 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 4.6  median 6.2  max 3752.5 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1280x720, model /home/paul/dev/odl-model, shaders /home/paul/dev/OpenDLSS-NR/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (11 modified) patch ea90414e2b0055cd1e7477c260e98faf3bb84571
[worker] serve: frame channel open (7.4 MB, NeuralScreen_3295284_15fdf8a5)
[worker] serve: pixel channel open (1280x720, 3.7 MB, NeuralScreenOut_3295284_f71039)
[main] shared memory: frames in and pixels out through /dev/shm (frame 7.4MB, pixels 3.7MB)
[worker] serve: the caller declared no motion field (nothing here reads one)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2980 ms
[worker] serve: frame 0 carries reset (no history is kept, so it is a no-op)
[worker] serve: head -8.4609..0.7085 mean -1.08560, non-finite 0 of 4128768; first 8 0.0107 0.0185 0.0306 -2.5371 0.0085 0.0222 0.0327 -2.3027
[worker] serve frame 0: 28.0 ms (proxy 0.9, network+composite 12.1, readback 13.8, reply 1.2)
[worker] serve frame 1: 7.2 ms (proxy 0.9, network+composite 4.9, readback 1.0, reply 0.3)
[worker] serve frame 2: 7.3 ms (proxy 1.1, network+composite 4.9, readback 1.0, reply 0.3)
[worker] serve frame 29: 8.5 ms (proxy 1.6, network+composite 5.5, readback 1.0, reply 0.3)
[worker] serve frame 59: 7.4 ms (proxy 1.3, network+composite 4.5, readback 1.1, reply 0.5)

```
