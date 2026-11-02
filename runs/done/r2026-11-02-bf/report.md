# run r2026-11-02-bf

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --send-ahead 2 --shm --save-after bf-1440p.png --worker-log`

exit **0** after 8.7s

gpu before: WARN (resident but not contending: chromium (pid 43069, 213.0 MiB); resident but not contending: signal-desktop (pid 43509, 60.0 MiB); resident but not contending: msedge (pid 73501, 220.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)); after: WARN (resident but not contending: chromium (pid 43069, 213.0 MiB); resident but not contending: signal-desktop (pid 43509, 60.0 MiB); resident but not contending: msedge (pid 73501, 220.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB))

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 52ecc85 (+25 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 6.999s (17.14 fps headline, 46.04 fps steady), worker exit 0
timing: capture 2.9ms  send 1.7ms  recv 49.0ms  display 2.9ms   (mean 56.5ms/frame, 17.7 fps; median 21.7ms/frame, 46.0 fps steady)
send spread: min 1.4  median 1.6  max 5.6 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 12.5  median 14.4  max 3953.3 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
  after  -> bf-1440p.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3078359_d4bf6789)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3078359_b2bb37)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3030 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.0781..3.5664 mean -0.79537; residual mean 0.0152 0.0100 0.0120 (rgb, head/4), logit mean -3.3299; non-finite 0 of 14745600; first 8 0.1646 0.0842 -0.1411 -0.0911 0.1649 0.0930 -0.1334 -0.1068
[worker] serve frame 0: 184.6 ms (proxy 4.8 [copy 2.3, submit 2.5], network+composite 96.9, readback 77.8, reply 5.1)
[worker] serve frame 1: 94.1 ms (proxy 5.0 [copy 2.4, submit 2.6], network+composite 82.1, readback 5.9, reply 1.1)
[worker] serve frame 2: 88.9 ms (proxy 4.7 [copy 2.3, submit 2.4], network+composite 78.8, readback 4.2, reply 1.2)
[worker] serve frame 29: 21.4 ms (proxy 5.0 [copy 3.4, submit 1.6], network+composite 12.3, readback 2.9, reply 1.3)
[worker] serve frame 59: 22.4 ms (proxy 5.0 [copy 3.3, submit 1.7], network+composite 13.1, readback 2.9, reply 1.4)
[worker] serve frame 89: 21.7 ms (proxy 4.7 [copy 3.1, submit 1.5], network+composite 12.8, readback 3.0, reply 1.3)
[worker] serve frame 119: 23.4 ms (proxy 5.6 [copy 3.8, submit 1.7], network+composite 12.4, readback 3.8, reply 1.6)

```
