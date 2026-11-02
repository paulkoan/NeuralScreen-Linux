# run r2026-11-02-be

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --shm --save-after be-1440p.png --worker-log`

exit **0** after 9.2s

gpu before: WARN (resident but not contending: chromium (pid 43069, 213.0 MiB); resident but not contending: signal-desktop (pid 43509, 60.0 MiB); resident but not contending: msedge (pid 73501, 220.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)); after: WARN (resident but not contending: chromium (pid 43069, 213.0 MiB); resident but not contending: signal-desktop (pid 43509, 60.0 MiB); resident but not contending: msedge (pid 73501, 220.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB))

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo be76ae2 (+24 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 7.49s (16.02 fps headline, 37.92 fps steady), worker exit 0
timing: capture 2.8ms  send 1.4ms  recv 54.8ms  display 2.0ms   (mean 61.0ms/frame, 16.4 fps; median 26.4ms/frame, 37.9 fps steady)
send spread: min 1.1  median 1.2  max 5.4 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 19.1  median 20.4  max 3952.5 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
  after  -> be-1440p.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3034304_e744f3a9)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3034304_c82189)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3034 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 147.2 ms (proxy 3.1 [copy 2.0, submit 1.0], network+composite 64.6, readback 74.5, reply 5.0)
[worker] serve frame 1: 49.2 ms (proxy 2.6 [copy 1.5, submit 1.1], network+composite 41.3, readback 4.0, reply 1.2)
[worker] serve frame 2: 44.1 ms (proxy 2.5 [copy 1.4, submit 1.1], network+composite 37.7, readback 2.6, reply 1.2)
[worker] serve frame 29: 20.2 ms (proxy 3.1 [copy 1.9, submit 1.2], network+composite 12.2, readback 3.2, reply 1.7)
[worker] serve frame 59: 18.1 ms (proxy 2.4 [copy 1.5, submit 0.9], network+composite 12.0, readback 2.6, reply 1.2)
[worker] serve frame 89: 18.1 ms (proxy 2.3 [copy 1.4, submit 0.9], network+composite 11.9, readback 2.7, reply 1.2)
[worker] serve frame 119: 19.4 ms (proxy 2.3 [copy 1.4, submit 0.9], network+composite 12.1, readback 3.3, reply 1.6)

```
