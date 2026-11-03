# run r2026-11-03-live-pipe1m

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --source window --size 2560x1440 --shm --save-before pipe1m-before.png --save-after pipe1m-after.png --worker-log`

exit **0** after 62.6s

gpu before: WARN (resident but not contending: chromium (pid 43069, 220.0 MiB); resident but not contending: signal-desktop (pid 43509, 61.0 MiB); resident but not contending: msedge (pid 73501, 176.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)); after: WARN (resident but not contending: chromium (pid 43069, 220.0 MiB); resident but not contending: signal-desktop (pid 43509, 61.0 MiB); resident but not contending: msedge (pid 73501, 222.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB))

```
  CreateSession
  session /org/freedesktop/portal/desktop/session/1_10542936/nsl_port
  SelectSources
  Start  (the compositor will ask you to choose a screen)
  stream node=118 serial=25982 0x0
  OpenPipeWireRemote
  window stream reports no size; using the requested 2560x1440
  pipe buffer 64 -> 1024 KiB
  pipeline pid 2119141: gst-launch-1.0 -q pipewiresrc fd=5 target-object=25982 ! videoconvert ! videoscale ! video/x-raw,format=RGBA,width=2560,height=1440,pixel-aspect-ratio=1/1 ! queue max-size-buffers=1 leaky=downstream ! fdsink fd=1
source window  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 67c5145 (+31 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 8.494s (14.13 fps headline, 29.59 fps steady), worker exit 0
timing: capture 6.5ms  send 1.5ms  recv 57.2ms  display 3.2ms   (mean 68.4ms/frame, 14.6 fps; median 33.8ms/frame, 29.6 fps steady)
send spread: min 1.1  median 1.3  max 8.8 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 19.5  median 23.0  max 4046.4 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture split: wait 0.5ms  read 6.0ms   (read near 9ms at 2560x1440 with a 1024 KiB pipe means we are draining a stocked pipe; far above that means the compositor was dribbling)
capture cpu: the pipeline used 2.05s over 8.49s = 24% of one core
  before -> pipe1m-before.png
  after  -> pipe1m-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: frame channel open (29.5 MB, NeuralScreen_2114605_0b2bb484)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_2114605_7d95b3)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3173 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -8.6875..0.8145 mean -1.25907; residual mean 0.0033 -0.0007 0.0029 (rgb, head/4), logit mean -5.0581; non-finite 0 of 14745600; first 8 0.0447 0.0701 0.0806 -4.4102 0.0487 0.0745 0.0797 -4.4062
[worker] serve frame 0: 139.3 ms (proxy 3.2 [copy 2.2, submit 1.0], network+composite 46.1, readback 83.1, reply 6.9)
[worker] serve frame 1: 36.6 ms (proxy 3.2 [copy 1.8, submit 1.4], network+composite 25.6, readback 5.6, reply 2.2)
[worker] serve frame 2: 33.9 ms (proxy 3.9 [copy 2.1, submit 1.8], network+composite 24.8, readback 3.2, reply 2.0)
[worker] serve frame 29: 21.8 ms (proxy 3.7 [copy 2.0, submit 1.7], network+composite 13.4, readback 3.4, reply 1.3)
[worker] serve frame 59: 20.5 ms (proxy 2.3 [copy 1.4, submit 0.9], network+composite 12.4, readback 3.9, reply 1.8)
[worker] serve frame 89: 22.3 ms (proxy 3.4 [copy 1.2, submit 2.2], network+composite 12.6, readback 4.5, reply 1.9)
[worker] serve frame 119: 20.7 ms (proxy 2.0 [copy 1.3, submit 0.8], network+composite 12.4, readback 4.5, reply 1.7)

```
