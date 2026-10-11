# run r2026-10-11-c

`uv run python -m minimal --source image --input-image fixtures/youtube-1440p.png --headless --frames 60 --worker-log --shm --no-motion --send-ahead 2 --save-before before.png --save-after after.png`

exit **0** after 8.2s

```
source image (fixtures/youtube-1440p.png)  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /home/paul/dev/OpenDLSS-NR/build/dlss5vk serve --model /home/paul/dev/odl-model
version: repo af52854 (+2 uncommitted) · worker built from patch ea90414e2b00 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 60 done, 0 skipped, 6.035s (9.94 fps), worker exit 0
timing: capture 2.3ms  send 2.3ms  recv 88.0ms  display 4.2ms   (total 96.9ms/frame, 10.3 fps)
send spread: min 1.7  median 2.2  max 6.7 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 16.5  median 19.8  max 4049.8 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  before -> before.png
  after  -> after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /home/paul/dev/odl-model, shaders /home/paul/dev/OpenDLSS-NR/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (11 modified) patch ea90414e2b0055cd1e7477c260e98faf3bb84571
[worker] serve: frame channel open (29.5 MB, NeuralScreen_2980533_23ce4b0d)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_2980533_449a98)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field (nothing here reads one)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3132 ms
[worker] serve: frame 0 carries reset (no history is kept, so it is a no-op)
[worker] serve: head -8.7188..0.7407 mean -1.05684, non-finite 0 of 15073280; first 8 0.0334 0.0340 0.0328 -4.8047 0.0280 0.0312 0.0285 -4.6172
[worker] serve frame 0: 100.5 ms (proxy 2.8, network+composite 38.7, readback 53.8, reply 5.2)
[worker] serve frame 1: 44.3 ms (proxy 5.1, network+composite 32.6, readback 4.7, reply 1.9)
[worker] serve frame 2: 35.7 ms (proxy 4.8, network+composite 24.8, readback 3.7, reply 2.4)
[worker] serve frame 29: 23.4 ms (proxy 4.6, network+composite 13.1, readback 3.6, reply 2.1)
[worker] serve frame 59: 23.2 ms (proxy 4.6, network+composite 13.1, readback 3.3, reply 2.2)

```
