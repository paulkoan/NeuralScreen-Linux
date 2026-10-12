# run r2026-10-12-b

`uv run python -m minimal --source image --input-image fixtures/youtube-1440p.png --headless --frames 60 --worker-log --shm --no-motion --send-ahead 2 --save-before before.png --save-after after.png`

exit **0** after 7.7s

```
source image (fixtures/youtube-1440p.png)  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo dc44bf7 (+4 uncommitted) · worker built from patch c2c4279a9623 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 60 done, 0 skipped, 5.498s (10.91 fps), worker exit 0
timing: capture 2.1ms  send 2.0ms  recv 80.6ms  display 4.2ms   (total 88.8ms/frame, 11.3 fps)
send spread: min 1.7  median 1.9  max 5.6 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 12.2  median 16.2  max 3869.1 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  before -> before.png
  after  -> after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (12 modified) patch c2c4279a962366602b95e04afef9ee4ed8662adc
[worker] serve: frame channel open (29.5 MB, NeuralScreen_700350_0a38450e)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_700350_b90849)
[worker] serve: the caller declared no motion field: the history is sampled at the pixel
[worker] serve: itself, which is what zero motion means
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3004 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -8.7188..0.7407 mean -1.05684, non-finite 0 of 15073280; first 8 0.0334 0.0340 0.0328 -4.8047 0.0280 0.0312 0.0285 -4.6172
[worker] serve frame 0: 79.7 ms (proxy 2.6, network+composite 19.5, readback 52.1, reply 5.5)
[worker] serve frame 1: 22.3 ms (proxy 3.7, network+composite 12.8, readback 4.1, reply 1.7)
[worker] serve frame 2: 20.8 ms (proxy 3.7, network+composite 12.5, readback 3.0, reply 1.7)
[worker] serve frame 29: 21.3 ms (proxy 4.4, network+composite 12.2, readback 3.0, reply 1.8)
[worker] serve frame 59: 20.7 ms (proxy 3.9, network+composite 12.0, readback 3.1, reply 1.7)

```
