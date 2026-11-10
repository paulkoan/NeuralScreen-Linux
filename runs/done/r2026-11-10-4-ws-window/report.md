# run r2026-11-10-4-ws-window

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --source window --size 2560x1440 --work-scale 0.75 --shm --save-before ws-window-before.png --save-after ws-window-after.png --worker-log`

exit **0** after 181.1s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 337.0 MiB); resident but not contending: chromium (pid 3132450, 113.0 MiB)) after waiting 15s; after: WARN (resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 282.0 MiB); resident but not contending: chromium (pid 3132450, 113.0 MiB))

```
  CreateSession
  session /org/freedesktop/portal/desktop/session/1_5363520/nsl_port
  SelectSources
  Start  (the compositor will ask you to choose a screen)
  stream node=177 serial=8668 0x0
  OpenPipeWireRemote
  window stream reports no size; using the requested 2560x1440
  pipe buffer 64 -> 1024 KiB
  pipeline pid 3178751: gst-launch-1.0 -q pipewiresrc fd=5 target-object=8668 ! queue max-size-buffers=1 leaky=downstream ! videoconvert ! videoscale ! video/x-raw,format=RGBA,width=2560,height=1440,pixel-aspect-ratio=1/1 ! fdsink fd=1
source window  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo c6cc223 (+58 uncommitted) · worker built from patch f1908586c80c at port 9d08f41 · in sync
[main] shared memory agreed: 23.0 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 175.771s (0.68 fps headline, 10.65 fps steady), worker exit 0
timing: capture 1345.8ms  send 2.6ms  recv 110.4ms  display 3.8ms   (mean 1462.5ms/frame, 0.7 fps; median 93.9ms/frame, 10.6 fps steady)
recv split (means): copy 2.3ms (min 1.5, max 6.5) + waiting 108.1ms   <- the copy is ours; the wait is the worker and the handoff
send spread: min 1.6  median 2.4  max 12.2 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 19.0  median 66.8  max 4635.4 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 5.6  median 13.5  max 5745.3 ms at frame 93 of 120   (a one-off at frame 93 — not the warm-up, so worth looking at)
capture split: wait 1337.7ms  read 8.1ms   (read near 9ms at 2560x1440 with a 1024 KiB pipe means we are draining a stocked pipe; far above that means the compositor was dribbling)
capture cpu: the pipeline used 1.28s over 175.77s = 1% of one core
  before -> ws-window-before.png
  after  -> ws-window-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: work scale: the client's frame is 2560x1440 and the network runs at 1920x1080, so the colour is resized down on the way in and the published image back up (one bilinear dispatch each way)
[worker] serve: built from port 9d08f41 (19 modified) patch f1908586c80c992da865c66cb5bc196dc6121c7c
[worker] serve: frame channel open (23.0 MB, NeuralScreen_3178223_1675cefe)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3178223_77d403)
[main] shared memory: frames in and pixels out through /dev/shm (frame 23.0MB, pixels 14.7MB)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_3178223_77d403m)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3707 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -8.2109..0.4810 mean -1.11457; residual mean -0.0003 -0.0023 -0.0058 (rgb, head/4), logit mean -4.4243; non-finite 0 of 8294400; first 8 0.0554 0.0422 0.0523 -4.3828 0.0577 0.0536 0.0589 -4.6133
[worker] serve frame 0: 113.0 ms (proxy 5.0 [copy 3.9, submit 1.1], network+composite 41.6, readback 58.1, reply 8.2)
[worker] serve frame 1: 25.1 ms (proxy 4.8 [copy 2.7, submit 2.1], network+composite 11.7, readback 6.7, reply 2.0)
[worker] serve frame 2: 22.3 ms (proxy 5.2 [copy 4.1, submit 1.1], network+composite 11.7, readback 3.8, reply 1.7)
[worker] serve frame 29: 64.5 ms (proxy 3.0 [copy 1.6, submit 1.3], network+composite 55.9, readback 3.9, reply 1.9)
[worker] serve frame 59: 19.0 ms (proxy 3.6 [copy 2.8, submit 0.9], network+composite 8.8, readback 3.6, reply 3.0)
[worker] serve frame 89: 50.6 ms (proxy 3.0 [copy 1.8, submit 1.2], network+composite 43.1, readback 2.9, reply 1.6)
[worker] serve frame 119: 150.0 ms (proxy 3.1 [copy 1.7, submit 1.4], network+composite 136.9, readback 8.2, reply 1.8)
[worker] serve: input stream closed after 120 frame(s), 70.09 ms mean\n

```
