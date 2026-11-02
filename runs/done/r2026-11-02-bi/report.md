# run r2026-11-02-bi

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --shm --motion-guides --save-after bi-1440p.png --worker-log`

exit **0** after 13.0s

gpu before: WARN (resident but not contending: chromium (pid 43069, 213.0 MiB); resident but not contending: signal-desktop (pid 43509, 59.0 MiB); resident but not contending: msedge (pid 73501, 219.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)) after waiting 60s; after: BUSY (utilization 35%; chromium (pid 43069, 213.0 MiB); signal-desktop (pid 43509, 59.0 MiB); msedge (pid 73501, 219.0 MiB); Telegram (pid 988444, 36.0 MiB); shelly-ui (pid 1045732, 46.0 MiB); signon-ui (pid 3062205, 17.0 MiB))

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo d19e1a5 (+27 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 10.874s (11.04 fps headline, 26.84 fps steady), worker exit 0
timing: capture 3.0ms  send 3.1ms  recv 64.2ms  display 2.3ms   (mean 72.6ms/frame, 13.8 fps; median 37.3ms/frame, 26.8 fps steady)
send spread: min 2.4  median 2.9  max 10.7 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 26.7  median 29.0  max 4079.0 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
  after  -> bi-1440p.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3415229_fde761e7)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3415229_b9332d)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3122 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 139.5 ms (proxy 7.1 [copy 5.1, submit 1.9], network+composite 53.9, readback 72.8, reply 5.7)
[worker] serve frame 1: 43.0 ms (proxy 4.9 [copy 2.9, submit 2.0], network+composite 32.1, readback 4.5, reply 1.6)
[worker] serve frame 2: 43.0 ms (proxy 5.1 [copy 3.1, submit 2.0], network+composite 32.3, readback 3.3, reply 2.4)
[worker] serve frame 29: 28.3 ms (proxy 5.5 [copy 3.6, submit 1.9], network+composite 16.1, readback 4.0, reply 2.6)
[worker] serve frame 59: 29.7 ms (proxy 6.7 [copy 4.2, submit 2.5], network+composite 15.6, readback 5.5, reply 1.9)
[worker] serve frame 89: 26.8 ms (proxy 5.9 [copy 3.5, submit 2.4], network+composite 15.8, readback 3.4, reply 1.8)
[worker] serve frame 119: 25.8 ms (proxy 6.0 [copy 3.7, submit 2.2], network+composite 15.1, readback 3.2, reply 1.6)

```
