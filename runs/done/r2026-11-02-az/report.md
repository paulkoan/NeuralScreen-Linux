# run r2026-11-02-az

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 1920x1080 --save-after az-1080p.png --worker-log`

exit **0** after 9.3s

gpu before: WARN (resident but not contending: chromium (pid 43069, 213.0 MiB); resident but not contending: signal-desktop (pid 43509, 59.0 MiB); resident but not contending: msedge (pid 73501, 220.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)) after waiting 285s; after: WARN (resident but not contending: chromium (pid 43069, 213.0 MiB); resident but not contending: signal-desktop (pid 43509, 59.0 MiB); resident but not contending: msedge (pid 73501, 219.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB))

```
source synthetic  capture 1920x1080  ->  work 1920x1080 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo c3a7326 (+20 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 8.027s (14.95 fps headline, 31.62 fps steady), worker exit 0
timing: capture 2.8ms  send 4.4ms  recv 56.3ms  display 1.5ms   (mean 65.0ms/frame, 15.4 fps; median 31.6ms/frame, 31.6 fps steady)
send spread: min 3.0  median 4.3  max 6.6 ms at frame 10 of 120   (a one-off at frame 10 — not the warm-up, so worth looking at)
recv spread: min 19.2  median 23.3  max 3957.8 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  after  -> az-1080p.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3125 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.1016..0.6226 mean -0.76198; residual mean 0.0186 0.0169 0.0229 (rgb, head/4), logit mean -3.2814; non-finite 0 of 8294400; first 8 0.0011 -0.0350 -0.0381 -4.3438 0.0004 -0.0418 -0.0382 -3.8105
[worker] serve frame 0: 89.5 ms (proxy 2.7 [copy 2.0, submit 0.7], network+composite 39.6, readback 41.9, reply 5.3)
[worker] serve frame 1: 31.1 ms (proxy 3.2 [copy 2.1, submit 1.1], network+composite 19.1, readback 4.8, reply 4.1)
[worker] serve frame 2: 27.8 ms (proxy 2.6 [copy 1.5, submit 1.1], network+composite 18.1, readback 3.3, reply 3.7)
[worker] serve frame 29: 19.3 ms (proxy 2.8 [copy 1.5, submit 1.3], network+composite 9.7, readback 3.0, reply 3.8)
[worker] serve frame 59: 21.0 ms (proxy 3.4 [copy 2.3, submit 1.1], network+composite 9.1, readback 3.5, reply 4.9)
[worker] serve frame 89: 20.7 ms (proxy 3.8 [copy 1.5, submit 2.3], network+composite 9.1, readback 3.3, reply 4.6)
[worker] serve frame 119: 17.1 ms (proxy 2.3 [copy 1.4, submit 0.9], network+composite 8.9, readback 3.1, reply 2.7)

```
