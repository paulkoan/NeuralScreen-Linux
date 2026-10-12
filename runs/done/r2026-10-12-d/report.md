# run r2026-10-12-d

`uv run python -m minimal --source image --input-image fixtures/youtube-1440p.png --headless --frames 60 --worker-log --shm --no-motion --send-ahead 2 --save-before before.png --save-after after.png`

exit **0** after 8.0s

```
source image (fixtures/youtube-1440p.png)  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 17ea04e (+4 uncommitted) · worker built from patch 08e297c8a802 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 60 done, 0 skipped, 5.835s (10.28 fps), worker exit 0
timing: capture 2.1ms  send 1.9ms  recv 86.1ms  display 4.3ms   (total 94.5ms/frame, 10.6 fps)
send spread: min 1.5  median 1.8  max 5.3 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 15.3  median 17.0  max 4013.7 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  before -> before.png
  after  -> after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (12 modified) patch 08e297c8a802f2642dadf402dcfd25ae7ae58d70
[worker] serve: frame channel open (29.5 MB, NeuralScreen_993512_96428c13)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_993512_86a506)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the history is sampled at the pixel
[worker] serve: itself, which is what zero motion means
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3069 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -8.7188..0.7407 mean -1.05684, non-finite 0 of 15073280; first 8 0.0334 0.0340 0.0328 -4.8047 0.0280 0.0312 0.0285 -4.6172
[worker] serve frame 0: 145.4 ms (proxy 4.0, network+composite 77.3, readback 58.4, reply 5.7)
[worker] serve frame 1: 78.4 ms (proxy 4.7, network+composite 65.9, readback 6.0, reply 1.8)
[worker] serve frame 2: 77.6 ms (proxy 5.0, network+composite 66.1, readback 4.7, reply 1.8)
[worker] serve frame 29: 23.3 ms (proxy 4.8, network+composite 12.7, readback 3.8, reply 2.0)
[worker] serve frame 59: 21.3 ms (proxy 3.9, network+composite 12.2, readback 3.3, reply 1.9)

```
