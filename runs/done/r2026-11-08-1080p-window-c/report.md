# run r2026-11-08-1080p-window-c

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --source window --size 1920x1080 --shm --save-before 1080p-window-c-before.png --save-after 1080p-window-c-after.png --worker-log`

exit **0** after 25.7s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 156.0 MiB); resident but not contending: chromium (pid 18945, 62.0 MiB); resident but not contending: msedge (pid 54723, 342.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 156.0 MiB); resident but not contending: chromium (pid 18945, 62.0 MiB); resident but not contending: msedge (pid 54723, 318.0 MiB))

```
  CreateSession
  session /org/freedesktop/portal/desktop/session/1_2744606/nsl_port
  SelectSources
  Start  (the compositor will ask you to choose a screen)
  stream node=53 serial=4762 0x0
  OpenPipeWireRemote
  window stream reports no size; using the requested 1920x1080
  pipe buffer 64 -> 1024 KiB
  pipeline pid 1969319: gst-launch-1.0 -q pipewiresrc fd=5 target-object=4762 ! queue max-size-buffers=1 leaky=downstream ! videoconvert ! videoscale ! video/x-raw,format=RGBA,width=1920,height=1080,pixel-aspect-ratio=1/1 ! fdsink fd=1
source window  capture 1920x1080  ->  work 1920x1080 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo ac1af3c (+51 uncommitted) · worker built from patch f2cd1f272c4c at port 9d08f41 · in sync
[main] shared memory agreed: 16.6 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 8.159s (14.71 fps headline, 32.77 fps steady), worker exit 0
timing: capture 5.7ms  send 2.4ms  recv 55.6ms  display 2.3ms   (mean 66.1ms/frame, 15.1 fps; median 30.5ms/frame, 32.8 fps steady)
recv split (means): copy 1.9ms (min 1.0, max 4.6) + waiting 53.7ms   <- the copy is ours; the wait is the worker and the handoff
send spread: min 1.7  median 2.3  max 6.0 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 16.3  median 20.1  max 4250.7 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture split: wait 0.5ms  read 5.1ms   (read near 9ms at 2560x1440 with a 1024 KiB pipe means we are draining a stocked pipe; far above that means the compositor was dribbling)
capture cpu: the pipeline used 2.05s over 8.16s = 25% of one core
  before -> 1080p-window-c-before.png
  after  -> 1080p-window-c-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (18 modified) patch f2cd1f272c4c4aaa27628dc19e95ef0b3a7c0e28
[worker] serve: frame channel open (16.6 MB, NeuralScreen_1967906_35c6d114)
[worker] serve: pixel channel open (1920x1080, 8.3 MB, NeuralScreenOut_1967906_586ed5)
[worker] serve: mid-frame channel open (8.3 MB, NeuralScreenOut_1967906_586ed5m)
[main] shared memory: frames in and pixels out through /dev/shm (frame 16.6MB, pixels 8.3MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3358 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -8.5469..1.4346 mean -1.03295; residual mean -0.0024 -0.0017 -0.0054 (rgb, head/4), logit mean -4.0938; non-finite 0 of 8294400; first 8 0.0091 0.0093 0.0688 -3.1953 0.0112 0.0095 0.0756 -3.6602
[worker] serve frame 0: 88.1 ms (proxy 2.9 [copy 2.1, submit 0.8], network+composite 34.4, readback 48.0, reply 2.8)
[worker] serve frame 1: 20.4 ms (proxy 2.6 [copy 1.6, submit 1.0], network+composite 14.0, readback 2.7, reply 1.1)
[worker] serve frame 2: 19.9 ms (proxy 3.3 [copy 2.2, submit 1.2], network+composite 12.8, readback 2.7, reply 1.1)
[worker] serve frame 29: 20.9 ms (proxy 4.8 [copy 3.2, submit 1.6], network+composite 9.1, readback 4.4, reply 2.6)
[worker] serve frame 59: 16.5 ms (proxy 3.0 [copy 1.6, submit 1.3], network+composite 10.2, readback 2.5, reply 0.8)
[worker] serve frame 89: 20.9 ms (proxy 7.2 [copy 1.8, submit 5.4], network+composite 8.8, readback 3.1, reply 1.7)
[worker] serve frame 119: 19.1 ms (proxy 4.1 [copy 2.8, submit 1.4], network+composite 8.7, readback 4.2, reply 2.1)
[worker] serve: input stream closed after 120 frame(s), 18.89 ms mean\n

```
