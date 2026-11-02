# run r2026-11-02-bc

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --send-ahead 2 --save-after bc-1440p.png --worker-log`

exit **0** after 12.0s

gpu before: WARN (resident but not contending: chromium (pid 43069, 214.0 MiB); resident but not contending: signal-desktop (pid 43509, 59.0 MiB); resident but not contending: msedge (pid 73501, 219.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)); after: WARN (resident but not contending: chromium (pid 43069, 214.0 MiB); resident but not contending: signal-desktop (pid 43509, 59.0 MiB); resident but not contending: msedge (pid 73501, 219.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB))

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 63fe255 (+22 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 10.164s (11.81 fps headline, 22.36 fps steady), worker exit 0
timing: capture 4.2ms  send 72.5ms  recv 0.3ms  display 5.3ms   (mean 82.3ms/frame, 12.1 fps; median 44.7ms/frame, 22.4 fps steady)
send spread: min 10.4  median 35.1  max 4411.9 ms at frame 1 of 120   (a one-off at frame 1 — not the warm-up, so worth looking at)
recv spread: min 0.0  median 0.0  max 27.5 ms at frame 119 of 120   (a one-off at frame 119 — not the warm-up, so worth looking at)
  after  -> bc-1440p.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3294 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 185.7 ms (proxy 4.8 [copy 2.4, submit 2.4], network+composite 92.4, readback 80.8, reply 7.7)
[worker] serve frame 1: 92.4 ms (proxy 5.7 [copy 3.0, submit 2.6], network+composite 74.0, readback 6.4, reply 6.4)
[worker] serve frame 2: 89.9 ms (proxy 5.8 [copy 3.0, submit 2.8], network+composite 71.8, readback 5.5, reply 6.8)
[worker] serve frame 29: 33.9 ms (proxy 6.9 [copy 4.2, submit 2.7], network+composite 13.0, readback 5.2, reply 8.8)
[worker] serve frame 59: 36.2 ms (proxy 6.4 [copy 3.6, submit 2.8], network+composite 14.8, readback 5.5, reply 9.5)
[worker] serve frame 89: 31.9 ms (proxy 5.3 [copy 3.1, submit 2.2], network+composite 14.9, readback 4.9, reply 6.8)
[worker] serve frame 119: 28.8 ms (proxy 4.9 [copy 2.9, submit 2.0], network+composite 13.5, readback 3.7, reply 6.7)

```
