# run r2026-11-02-bg

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 1920x1080 --shm --save-after bg-1080p.png --worker-log`

exit **0** after 8.1s

gpu before: WARN (resident but not contending: chromium (pid 43069, 213.0 MiB); resident but not contending: signal-desktop (pid 43509, 60.0 MiB); resident but not contending: msedge (pid 73501, 221.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)); after: WARN (resident but not contending: chromium (pid 43069, 213.0 MiB); resident but not contending: signal-desktop (pid 43509, 60.0 MiB); resident but not contending: msedge (pid 73501, 219.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB))

```
source synthetic  capture 1920x1080  ->  work 1920x1080 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 37b46b1 (+26 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
[main] shared memory agreed: 16.6 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 6.862s (17.49 fps headline, 51.22 fps steady), worker exit 0
timing: capture 2.5ms  send 1.5ms  recv 50.3ms  display 1.1ms   (mean 55.3ms/frame, 18.1 fps; median 19.5ms/frame, 51.2 fps steady)
send spread: min 1.0  median 1.3  max 3.1 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 13.5  median 14.7  max 4193.6 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
  after  -> bg-1080p.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: frame channel open (16.6 MB, NeuralScreen_3096911_305c8176)
[main] shared memory: frames in and pixels out through /dev/shm (frame 16.6MB, pixels 8.3MB)
[worker] serve: pixel channel open (1920x1080, 8.3 MB, NeuralScreenOut_3096911_7f5cf4)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3022 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.1016..0.6226 mean -0.76198; residual mean 0.0186 0.0169 0.0229 (rgb, head/4), logit mean -3.2814; non-finite 0 of 8294400; first 8 0.0011 -0.0350 -0.0381 -4.3438 0.0004 -0.0418 -0.0382 -3.8105
[worker] serve frame 0: 76.3 ms (proxy 2.9 [copy 2.1, submit 0.8], network+composite 28.9, readback 41.7, reply 2.8)
[worker] serve frame 1: 15.0 ms (proxy 3.3 [copy 1.9, submit 1.4], network+composite 8.4, readback 2.6, reply 0.7)
[worker] serve frame 2: 13.1 ms (proxy 1.8 [copy 0.9, submit 1.0], network+composite 8.3, readback 2.2, reply 0.7)
[worker] serve frame 29: 12.9 ms (proxy 2.1 [copy 0.9, submit 1.1], network+composite 7.9, readback 2.2, reply 0.7)
[worker] serve frame 59: 13.3 ms (proxy 2.4 [copy 1.3, submit 1.1], network+composite 7.9, readback 2.4, reply 0.6)
[worker] serve frame 89: 14.1 ms (proxy 3.6 [copy 1.2, submit 2.4], network+composite 7.8, readback 2.0, reply 0.8)
[worker] serve frame 119: 13.2 ms (proxy 2.2 [copy 1.2, submit 1.0], network+composite 7.9, readback 2.3, reply 0.8)

```
