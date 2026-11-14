# run r2026-11-11-ws-window-c

runner `6a0703c28681` · entry `minimal` · env from policy: NS_WORKER_CMD

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --frames 120 --source window --size 2560x1440 --work-scale 0.75 --shm --save-before ws-window-c-before.png --save-after ws-window-c-after.png --worker-log`

exit **0** after 17.7s

gpu before: WARN [util 17% of the 25% bar] (resident but not contending: msedge (pid 3047582, 488.0 MiB); resident but not contending: chromium (pid 3225234, 215.0 MiB)); after: WARN [util 4% of the 25% bar] (resident but not contending: msedge (pid 3047582, 507.0 MiB); resident but not contending: chromium (pid 3225234, 215.0 MiB))

```
  CreateSession
  session /org/freedesktop/portal/desktop/session/1_315902/nsl_port
  SelectSources
  Start  (the compositor will ask you to choose a screen)
  stream node=189 serial=6053 0x0
  OpenPipeWireRemote
  window stream reports no size; using the requested 2560x1440
  pipe buffer 64 -> 1024 KiB
  pipeline pid 533804: gst-launch-1.0 -q pipewiresrc fd=5 target-object=6053 ! queue max-size-buffers=1 leaky=downstream ! videoconvert ! videoscale ! video/x-raw,format=RGBA,width=2560,height=1440,pixel-aspect-ratio=1/1 ! fdsink fd=1
source window  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 3aeaa84 (+72 uncommitted) · worker built from patch 58e98d824bce at port 9d08f41 · in sync
[main] shared memory agreed: 23.0 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 8.852s (13.56 fps headline, 30.09 fps steady), worker exit 0
timing: capture 6.0ms  send 2.7ms  recv 59.6ms  display 3.2ms   (mean 71.5ms/frame, 14.0 fps; median 33.2ms/frame, 30.1 fps steady)
recv split (means): copy 1.8ms (min 1.2, max 4.9) + waiting 57.8ms   <- the copy is ours; the wait is the worker and the handoff
send spread: min 1.7  median 2.4  max 8.0 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 17.6  median 21.7  max 4531.2 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture split: wait 0.4ms  read 5.6ms   (read near 9ms at 2560x1440 with a 1024 KiB pipe means we are draining a stocked pipe; far above that means the compositor was dribbling)
capture cpu: the pipeline used 1.34s over 8.85s = 15% of one core
  before -> ws-window-c-before.png
  after  -> ws-window-c-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: work scale: the client's frame is 2560x1440 and the network runs at 1920x1080, so the colour is resized down on the way in and the published image back up (one bilinear dispatch each way)
[worker] serve: built from port 9d08f41 (19 modified) patch 58e98d824bce70856b56ae4c7f1456d53e1889e6
[worker] serve: frame channel open (23.0 MB, NeuralScreen_533492_540b0220)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_533492_b1a91f)
[worker] serve: mid-frame channel open (14.7 MB, NeuralScreenOut_533492_b1a91fm)
[main] shared memory: frames in and pixels out through /dev/shm (frame 23.0MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3272 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -8.8906..0.7627 mean -1.28137; residual mean 0.0026 0.0029 0.0008 (rgb, head/4), logit mean -5.1506; non-finite 0 of 8294400; first 8 -0.1201 -0.0906 -0.0251 -5.9062 -0.1157 -0.0835 -0.0247 -5.7461
[worker] serve frame 0: 99.4 ms (proxy 2.8 [copy 2.0, submit 0.9], network+composite 44.9, readback 46.8, reply 4.8)
[worker] serve frame 1: 28.3 ms (proxy 3.2 [copy 1.8, submit 1.4], network+composite 16.0, readback 7.7, reply 1.4)
[worker] serve frame 2: 27.6 ms (proxy 3.6 [copy 2.2, submit 1.3], network+composite 16.6, readback 4.8, reply 2.7)
[worker] serve frame 29: 18.0 ms (proxy 3.1 [copy 1.9, submit 1.2], network+composite 8.9, readback 4.2, reply 1.8)
[worker] serve frame 59: 18.7 ms (proxy 4.6 [copy 3.1, submit 1.5], network+composite 8.6, readback 3.7, reply 1.7)
[worker] serve frame 89: 17.9 ms (proxy 4.9 [copy 2.1, submit 2.8], network+composite 8.8, readback 3.0, reply 1.2)
[worker] serve frame 119: 21.2 ms (proxy 4.7 [copy 3.1, submit 1.6], network+composite 8.9, readback 5.3, reply 2.3)
[worker] serve: input stream closed after 120 frame(s), 20.78 ms mean\n

```
