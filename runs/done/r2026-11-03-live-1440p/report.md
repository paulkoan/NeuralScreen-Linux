# run r2026-11-03-live-1440p

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --source window --size 2560x1440 --shm --save-before live-before.png --save-after live-after.png --worker-log`

exit **0** after 28.0s

gpu before: WARN (resident but not contending: chromium (pid 43069, 216.0 MiB); resident but not contending: signal-desktop (pid 43509, 59.0 MiB); resident but not contending: msedge (pid 73501, 219.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)); after: WARN (resident but not contending: chromium (pid 43069, 216.0 MiB); resident but not contending: signal-desktop (pid 43509, 59.0 MiB); resident but not contending: msedge (pid 73501, 244.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: shelly-ui (pid 1045732, 46.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB))

```
  CreateSession
  session /org/freedesktop/portal/desktop/session/1_9743056/nsl_port
  SelectSources
  Start  (the compositor will ask you to choose a screen)
  stream node=215 serial=23596 0x0
  OpenPipeWireRemote
  window stream reports no size; using the requested 2560x1440
  pipeline pid 3545380: gst-launch-1.0 -q pipewiresrc fd=5 target-object=23596 ! videoconvert ! videoscale ! video/x-raw,format=RGBA,width=2560,height=1440,pixel-aspect-ratio=1/1 ! queue max-size-buffers=1 leaky=downstream ! fdsink fd=1
source window  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 2232db3 (+29 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 10.821s (11.09 fps headline, 21.48 fps steady), worker exit 0
timing: capture 13.4ms  send 2.6ms  recv 66.9ms  display 4.9ms   (mean 87.8ms/frame, 11.4 fps; median 46.6ms/frame, 21.5 fps steady)
send spread: min 0.8  median 2.3  max 8.3 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 20.8  median 26.7  max 4664.3 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 7.3  median 12.8  max 37.7 ms at frame 29 of 120   (a one-off at frame 29 — not the warm-up, so worth looking at)
display spread: min 2.6  median 4.2  max 33.5 ms at frame 27 of 120   (a one-off at frame 27 — not the warm-up, so worth looking at)
capture split: wait 0.3ms  read 13.1ms   (read ~19ms at 2560x1440 means we are draining a stocked pipe; read far above that means the compositor was dribbling)
capture cpu: the pipeline used 4.19s over 10.82s = 39% of one core
  before -> live-before.png
  after  -> live-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3544098_0c04f266)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3544098_81af74)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3334 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -9.2734..0.9292 mean -1.27059; residual mean 0.0053 0.0076 0.0023 (rgb, head/4), logit mean -5.1432; non-finite 0 of 14745600; first 8 0.0024 0.0214 0.0461 -4.6328 0.0157 0.0316 0.0538 -4.6289
[worker] serve frame 0: 143.4 ms (proxy 6.0 [copy 4.2, submit 1.8], network+composite 47.9, readback 83.1, reply 6.4)
[worker] serve frame 1: 40.5 ms (proxy 3.2 [copy 1.5, submit 1.7], network+composite 23.8, readback 10.0, reply 3.5)
[worker] serve frame 2: 45.4 ms (proxy 6.1 [copy 3.8, submit 2.3], network+composite 23.3, readback 10.7, reply 5.4)
[worker] serve frame 29: 21.2 ms (proxy 3.7 [copy 2.5, submit 1.2], network+composite 13.4, readback 2.9, reply 1.2)
[worker] serve frame 59: 24.7 ms (proxy 4.4 [copy 2.8, submit 1.6], network+composite 13.2, readback 5.5, reply 1.7)
[worker] serve frame 89: 24.5 ms (proxy 4.5 [copy 3.0, submit 1.5], network+composite 13.5, readback 4.5, reply 2.0)
[worker] serve frame 119: 22.4 ms (proxy 3.6 [copy 2.3, submit 1.4], network+composite 13.2, readback 4.5, reply 1.1)

```
