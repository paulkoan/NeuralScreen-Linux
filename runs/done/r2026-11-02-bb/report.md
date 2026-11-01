# run r2026-11-02-bb

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --save-after bb-1440p.png --worker-log`

exit **0** after 10.5s

gpu before: WARN (resident but not contending: chromium (pid 43069, 214.0 MiB); resident but not contending: signal-desktop (pid 43509, 59.0 MiB); resident but not contending: msedge (pid 73501, 219.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)); after: WARN (resident but not contending: chromium (pid 43069, 214.0 MiB); resident but not contending: signal-desktop (pid 43509, 59.0 MiB); resident but not contending: msedge (pid 73501, 220.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB))

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo c44718c (+21 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 8.822s (13.6 fps headline, 25.2 fps steady), worker exit 0
timing: capture 2.8ms  send 5.4ms  recv 61.6ms  display 2.3ms   (mean 72.1ms/frame, 13.9 fps; median 39.7ms/frame, 25.2 fps steady)
send spread: min 4.1  median 5.2  max 9.6 ms at frame 88 of 120   (a one-off at frame 88 — not the warm-up, so worth looking at)
recv spread: min 27.4  median 29.4  max 3827.1 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  after  -> bb-1440p.png

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
[worker] serve: warm-up 2943 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 164.0 ms (proxy 2.7 [copy 1.8, submit 0.9], network+composite 80.0, readback 75.2, reply 6.1)
[worker] serve frame 1: 31.9 ms (proxy 2.5 [copy 1.6, submit 0.9], network+composite 20.0, readback 4.2, reply 5.1)
[worker] serve frame 2: 30.3 ms (proxy 2.7 [copy 1.6, submit 1.1], network+composite 19.6, readback 3.5, reply 4.5)
[worker] serve frame 29: 25.9 ms (proxy 2.7 [copy 1.7, submit 1.0], network+composite 14.9, readback 3.5, reply 4.9)
[worker] serve frame 59: 25.3 ms (proxy 2.5 [copy 1.6, submit 0.9], network+composite 13.9, readback 3.6, reply 5.3)
[worker] serve frame 89: 29.1 ms (proxy 3.7 [copy 2.6, submit 1.1], network+composite 15.3, readback 4.3, reply 5.8)
[worker] serve frame 119: 24.8 ms (proxy 2.6 [copy 1.6, submit 1.0], network+composite 14.0, readback 3.4, reply 4.7)

```
