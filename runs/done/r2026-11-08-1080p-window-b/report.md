# run r2026-11-08-1080p-window-b

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --source window --size 1920x1080 --shm --save-before 1080p-window-b-before.png --save-after 1080p-window-b-after.png --worker-log`

exit **0** after 42.3s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 153.0 MiB); resident but not contending: chromium (pid 18945, 115.0 MiB); resident but not contending: msedge (pid 54723, 338.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 152.0 MiB); resident but not contending: chromium (pid 18945, 109.0 MiB); resident but not contending: msedge (pid 54723, 318.0 MiB))

```
  CreateSession
  session /org/freedesktop/portal/desktop/session/1_2623496/nsl_port
  SelectSources
  Start  (the compositor will ask you to choose a screen)
  stream node=165 serial=4483 0x0
  OpenPipeWireRemote
  window stream reports no size; using the requested 1920x1080
  pipe buffer 64 -> 1024 KiB
  pipeline pid 1723585: gst-launch-1.0 -q pipewiresrc fd=5 target-object=4483 ! videoconvert ! videoscale ! video/x-raw,format=RGBA,width=1920,height=1080,pixel-aspect-ratio=1/1 ! queue max-size-buffers=1 leaky=downstream ! fdsink fd=1
source window  capture 1920x1080  ->  work 1920x1080 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo adb26ff (+49 uncommitted) · worker built from patch f2cd1f272c4c at port 9d08f41 · in sync
[main] shared memory agreed: 16.6 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 9.498s (12.63 fps headline, 27.66 fps steady), worker exit 0
timing: capture 7.6ms  send 2.8ms  recv 62.8ms  display 3.5ms   (mean 76.7ms/frame, 13.0 fps; median 36.2ms/frame, 27.7 fps steady)
recv split (means): copy 2.3ms (min 1.1, max 6.0) + waiting 60.5ms   <- the copy is ours; the wait is the worker and the handoff
send spread: min 1.7  median 2.5  max 5.8 ms at frame 14 of 120   (a one-off at frame 14 — not the warm-up, so worth looking at)
recv spread: min 18.1  median 22.9  max 4735.5 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
display spread: min 1.6  median 3.1  max 24.2 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture split: wait 0.7ms  read 6.9ms   (read near 9ms at 2560x1440 with a 1024 KiB pipe means we are draining a stocked pipe; far above that means the compositor was dribbling)
capture cpu: the pipeline used 8.52s over 9.50s = 90% of one core
          ! that work runs while the worker waits: the same 2560x1440 frame cost send 114.2ms through the portal against 67.3ms produced synthetically
  before -> 1080p-window-b-before.png
  after  -> 1080p-window-b-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (18 modified) patch f2cd1f272c4c4aaa27628dc19e95ef0b3a7c0e28
[worker] serve: frame channel open (16.6 MB, NeuralScreen_1720827_a27ab854)
[worker] serve: pixel channel open (1920x1080, 8.3 MB, NeuralScreenOut_1720827_8e8163)
[worker] serve: mid-frame channel open (8.3 MB, NeuralScreenOut_1720827_8e8163m)
[main] shared memory: frames in and pixels out through /dev/shm (frame 16.6MB, pixels 8.3MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3754 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -7.6445..0.5913 mean -1.04705; residual mean -0.0090 -0.0014 0.0053 (rgb, head/4), logit mean -4.1677; non-finite 0 of 8294400; first 8 0.0012 0.0293 0.0215 -4.0156 0.0010 0.0296 0.0213 -4.0664
[worker] serve frame 0: 118.0 ms (proxy 4.2 [copy 3.0, submit 1.1], network+composite 42.9, readback 63.9, reply 7.1)
[worker] serve frame 1: 27.8 ms (proxy 3.2 [copy 1.9, submit 1.2], network+composite 15.8, readback 6.0, reply 2.8)
[worker] serve frame 2: 27.3 ms (proxy 3.9 [copy 2.3, submit 1.6], network+composite 16.3, readback 5.0, reply 2.2)
[worker] serve frame 29: 18.2 ms (proxy 3.3 [copy 1.7, submit 1.6], network+composite 9.7, readback 3.9, reply 1.4)
[worker] serve frame 59: 26.1 ms (proxy 4.6 [copy 2.6, submit 2.0], network+composite 9.9, readback 7.5, reply 4.2)
[worker] serve frame 89: 23.3 ms (proxy 9.6 [copy 3.7, submit 5.9], network+composite 8.8, readback 3.4, reply 1.5)
[worker] serve frame 119: 21.6 ms (proxy 2.7 [copy 1.5, submit 1.2], network+composite 9.5, readback 5.5, reply 4.0)
[worker] serve: input stream closed after 120 frame(s), 21.71 ms mean\n

```
