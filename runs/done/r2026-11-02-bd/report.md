# run r2026-11-02-bd

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --send-ahead 2 --shm --save-after bd-1440p.png --worker-log`

exit **0** after 9.4s

gpu before: WARN (resident but not contending: chromium (pid 43069, 213.0 MiB); resident but not contending: signal-desktop (pid 43509, 60.0 MiB); resident but not contending: msedge (pid 73501, 220.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)); after: WARN (resident but not contending: chromium (pid 43069, 213.0 MiB); resident but not contending: signal-desktop (pid 43509, 60.0 MiB); resident but not contending: msedge (pid 73501, 220.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB))

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 4c0637c (+23 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 7.589s (15.81 fps headline, 37.74 fps steady), worker exit 0
timing: capture 3.4ms  send 2.3ms  recv 52.3ms  display 3.8ms   (mean 61.8ms/frame, 16.2 fps; median 26.5ms/frame, 37.7 fps steady)
send spread: min 1.6  median 2.3  max 5.7 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 14.5  median 16.8  max 4091.6 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  after  -> bd-1440p.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: frame channel open (29.5 MB, NeuralScreen_2952822_d828103f)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_2952822_f2cc9e)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3133 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.0781..3.5664 mean -0.79537; residual mean 0.0152 0.0100 0.0120 (rgb, head/4), logit mean -3.3299; non-finite 0 of 14745600; first 8 0.1646 0.0842 -0.1411 -0.0911 0.1649 0.0930 -0.1334 -0.1068
[worker] serve frame 0: 196.0 ms (proxy 5.2 [copy 2.5, submit 2.6], network+composite 106.6, readback 78.6, reply 5.7)
[worker] serve frame 1: 96.9 ms (proxy 5.3 [copy 2.7, submit 2.7], network+composite 83.5, readback 6.2, reply 1.9)
[worker] serve frame 2: 97.0 ms (proxy 6.4 [copy 3.2, submit 3.1], network+composite 83.4, readback 5.4, reply 1.8)
[worker] serve frame 29: 28.4 ms (proxy 7.2 [copy 4.8, submit 2.4], network+composite 13.4, readback 5.4, reply 2.4)
[worker] serve frame 59: 29.3 ms (proxy 7.5 [copy 4.8, submit 2.7], network+composite 13.3, readback 5.7, reply 2.7)
[worker] serve frame 89: 28.4 ms (proxy 7.4 [copy 4.5, submit 2.9], network+composite 14.0, readback 4.6, reply 2.4)
[worker] serve frame 119: 24.2 ms (proxy 5.8 [copy 3.9, submit 1.9], network+composite 12.9, readback 3.7, reply 1.8)

```
