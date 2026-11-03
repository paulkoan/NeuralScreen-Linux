# run r2026-11-03-live-prefetch

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --source window --size 2560x1440 --shm --prefetch --save-before pf-before.png --save-after pf-after.png --worker-log`

exit **0** after 22.6s

gpu before: WARN (resident but not contending: chromium (pid 43069, 220.0 MiB); resident but not contending: signal-desktop (pid 43509, 61.0 MiB); resident but not contending: msedge (pid 73501, 221.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)) after waiting 15s; after: WARN (resident but not contending: chromium (pid 43069, 220.0 MiB); resident but not contending: signal-desktop (pid 43509, 61.0 MiB); resident but not contending: msedge (pid 73501, 221.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB))

```
  CreateSession
  session /org/freedesktop/portal/desktop/session/1_10544682/nsl_port
  SelectSources
  Start  (the compositor will ask you to choose a screen)
  stream node=68 serial=26098 0x0
  OpenPipeWireRemote
  window stream reports no size; using the requested 2560x1440
  pipe buffer 64 -> 1024 KiB
  pipeline pid 2122155: gst-launch-1.0 -q pipewiresrc fd=5 target-object=26098 ! videoconvert ! videoscale ! video/x-raw,format=RGBA,width=2560,height=1440,pixel-aspect-ratio=1/1 ! queue max-size-buffers=1 leaky=downstream ! fdsink fd=1
source window  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 67c5145 (+2688 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 8.877s (13.52 fps headline, 28.44 fps steady), worker exit 0
timing: capture 0.0ms  send 2.9ms  recv 64.7ms  display 4.0ms   (mean 71.6ms/frame, 14.0 fps; median 35.2ms/frame, 28.4 fps steady)
send spread: min 1.7  median 2.7  max 5.7 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 22.9  median 28.4  max 4311.9 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
prefetch: drained 387 frames on its own thread, 386 dropped, frame age mean 15.6ms max 39.0ms
  before -> pf-before.png
  after  -> pf-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: frame channel open (29.5 MB, NeuralScreen_2121187_757db538)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_2121187_0bd60e)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3324 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -7.8555..0.2688 mean -0.95310; residual mean 0.0010 -0.0009 -0.0011 (rgb, head/4), logit mean -3.8082; non-finite 0 of 14745600; first 8 -0.0234 -0.0240 -0.0341 -3.2383 -0.0279 -0.0282 -0.0368 -3.4844
[worker] serve frame 0: 157.1 ms (proxy 3.2 [copy 2.1, submit 1.1], network+composite 45.8, readback 101.3, reply 6.9)
[worker] serve frame 1: 40.8 ms (proxy 3.9 [copy 2.4, submit 1.5], network+composite 25.9, readback 8.6, reply 2.5)
[worker] serve frame 2: 38.7 ms (proxy 4.5 [copy 2.3, submit 2.2], network+composite 26.1, readback 4.9, reply 3.3)
[worker] serve frame 29: 26.0 ms (proxy 3.7 [copy 2.6, submit 1.1], network+composite 12.7, readback 6.1, reply 3.5)
[worker] serve frame 59: 26.7 ms (proxy 4.4 [copy 2.5, submit 1.9], network+composite 12.5, readback 6.9, reply 3.0)
[worker] serve frame 89: 28.9 ms (proxy 6.5 [copy 2.9, submit 3.7], network+composite 13.2, readback 5.8, reply 3.4)
[worker] serve frame 119: 24.9 ms (proxy 4.5 [copy 2.9, submit 1.6], network+composite 12.5, readback 5.8, reply 2.2)

```
