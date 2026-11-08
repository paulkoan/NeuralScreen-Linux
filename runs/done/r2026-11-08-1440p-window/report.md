# run r2026-11-08-1440p-window

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --source window --size 2560x1440 --shm --save-before 1440p-window-before.png --save-after 1440p-window-after.png --worker-log`

exit **0** after 16.4s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 153.0 MiB); resident but not contending: chromium (pid 18945, 66.0 MiB); resident but not contending: msedge (pid 54723, 342.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 153.0 MiB); resident but not contending: chromium (pid 18945, 66.0 MiB); resident but not contending: msedge (pid 54723, 318.0 MiB))

```
  CreateSession
  session /org/freedesktop/portal/desktop/session/1_3048728/nsl_port
  SelectSources
  Start  (the compositor will ask you to choose a screen)
  stream node=152 serial=5075 0x0
  OpenPipeWireRemote
  window stream reports no size; using the requested 2560x1440
  pipe buffer 64 -> 1024 KiB
  pipeline pid 2603137: gst-launch-1.0 -q pipewiresrc fd=5 target-object=5075 ! queue max-size-buffers=1 leaky=downstream ! videoconvert ! videoscale ! video/x-raw,format=RGBA,width=2560,height=1440,pixel-aspect-ratio=1/1 ! fdsink fd=1
source window  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 5ba9641 (+53 uncommitted) · worker built from patch f2cd1f272c4c at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 10.506s (11.42 fps headline, 20.72 fps steady), worker exit 0
timing: capture 9.5ms  send 4.3ms  recv 67.0ms  display 4.4ms   (mean 85.1ms/frame, 11.8 fps; median 48.3ms/frame, 20.7 fps steady)
recv split (means): copy 3.2ms (min 1.9, max 6.5) + waiting 63.8ms   <- the copy is ours; the wait is the worker and the handoff
send spread: min 2.5  median 4.0  max 11.4 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 26.6  median 31.1  max 4232.5 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture split: wait 0.5ms  read 9.0ms   (read near 9ms at 2560x1440 with a 1024 KiB pipe means we are draining a stocked pipe; far above that means the compositor was dribbling)
capture cpu: the pipeline used 2.90s over 10.51s = 28% of one core
  before -> 1440p-window-before.png
  after  -> 1440p-window-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (18 modified) patch f2cd1f272c4c4aaa27628dc19e95ef0b3a7c0e28
[worker] serve: frame channel open (29.5 MB, NeuralScreen_2602547_47156aeb)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_2602547_499b55)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_2602547_499b55m)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3255 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -8.1250..0.4529 mean -1.01768; residual mean -0.0012 -0.0014 -0.0034 (rgb, head/4), logit mean -4.0466; non-finite 0 of 14745600; first 8 0.0350 0.0317 0.0335 -4.6836 0.0371 0.0350 0.0318 -4.6172
[worker] serve frame 0: 150.4 ms (proxy 6.6 [copy 5.3, submit 1.3], network+composite 50.1, readback 85.6, reply 8.1)
[worker] serve frame 1: 36.2 ms (proxy 7.0 [copy 5.0, submit 2.0], network+composite 18.0, readback 8.9, reply 2.4)
[worker] serve frame 2: 35.8 ms (proxy 6.5 [copy 4.1, submit 2.4], network+composite 19.1, readback 7.0, reply 3.1)
[worker] serve frame 29: 27.7 ms (proxy 6.8 [copy 4.8, submit 2.0], network+composite 13.7, readback 4.8, reply 2.3)
[worker] serve frame 59: 30.0 ms (proxy 5.8 [copy 3.9, submit 2.0], network+composite 13.8, readback 7.2, reply 3.2)
[worker] serve frame 89: 32.7 ms (proxy 9.5 [copy 4.0, submit 5.6], network+composite 13.2, readback 6.6, reply 3.3)
[worker] serve frame 119: 25.6 ms (proxy 6.7 [copy 4.2, submit 2.4], network+composite 13.2, readback 3.6, reply 2.2)
[worker] serve: input stream closed after 120 frame(s), 29.59 ms mean\n

```
