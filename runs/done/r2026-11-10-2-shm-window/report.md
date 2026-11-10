# run r2026-11-10-2-shm-window

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --source window --size 1920x1080 --shm --capture-transport shm --save-before shm-window-before.png --save-after shm-window-after.png --worker-log`

exit **0** after 13.9s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: chromium (pid 18945, 111.0 MiB); resident but not contending: msedge (pid 1300500, 303.0 MiB)) after waiting 15s; after: WARN (resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: chromium (pid 18945, 111.0 MiB); resident but not contending: msedge (pid 1300500, 295.0 MiB))

```
  CreateSession
  session /org/freedesktop/portal/desktop/session/1_5247814/nsl_port
  SelectSources
  Start  (the compositor will ask you to choose a screen)
  stream node=188 serial=8076 0x0
  OpenPipeWireRemote
  window stream reports no size; using the requested 1920x1080
  transport: shared memory (memfd fd=7); one pread per frame
  pipeline pid 2930806: gst-launch-1.0 -q pipewiresrc fd=5 target-object=8076 ! queue max-size-buffers=1 leaky=downstream ! videoconvert ! videoscale ! video/x-raw,format=RGBA,width=1920,height=1080,pixel-aspect-ratio=1/1 ! fdsink fd=7 sync=false
source window  capture 1920x1080  ->  work 1920x1080 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 20c4f6b (+55 uncommitted) · worker built from patch a522cd30bbb2 at port 9d08f41 · in sync
[main] shared memory agreed: 16.6 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 8.731s (13.74 fps headline, 32.96 fps steady), worker exit 0
timing: capture 6.6ms  send 1.9ms  recv 58.1ms  display 2.7ms   (mean 69.3ms/frame, 14.4 fps; median 30.3ms/frame, 33.0 fps steady)
recv split (means): copy 1.7ms (min 0.8, max 3.4) + waiting 56.4ms   <- the copy is ours; the wait is the worker and the handoff
send spread: min 0.9  median 1.9  max 3.8 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 15.4  median 19.3  max 4602.6 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture split: wait 0.0ms  read 6.6ms   (read ~19ms at 2560x1440 means we are draining a stocked pipe; far above that means the compositor was dribbling)
capture cpu: the pipeline used 6.58s over 8.73s = 75% of one core
          ! that work runs while the worker waits: the same 2560x1440 frame cost send 114.2ms through the portal against 67.3ms produced synthetically
  before -> shm-window-before.png
  after  -> shm-window-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (18 modified) patch a522cd30bbb2cb65c0f9ee46053c25aa3b2a9c23
[worker] serve: frame channel open (16.6 MB, NeuralScreen_2930275_dccdc606)
[worker] serve: pixel channel open (1920x1080, 8.3 MB, NeuralScreenOut_2930275_aca534)
[worker] serve: mid-frame channel open (8.3 MB, NeuralScreenOut_2930275_aca534m)
[main] shared memory: frames in and pixels out through /dev/shm (frame 16.6MB, pixels 8.3MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3635 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -10.1172..1.3877 mean -1.28463; residual mean 0.0040 0.0069 0.0087 (rgb, head/4), logit mean -5.2167; non-finite 0 of 8294400; first 8 0.0800 0.0081 -0.0531 -4.9219 0.0741 0.0050 -0.0558 -4.7734
[worker] serve frame 0: 95.1 ms (proxy 3.0 [copy 2.1, submit 0.9], network+composite 36.8, readback 51.3, reply 4.1)
[worker] serve frame 1: 26.2 ms (proxy 6.4 [copy 4.6, submit 1.7], network+composite 14.5, readback 3.7, reply 1.6)
[worker] serve frame 2: 21.6 ms (proxy 3.2 [copy 2.0, submit 1.3], network+composite 12.7, readback 3.9, reply 1.8)
[worker] serve frame 29: 20.7 ms (proxy 3.4 [copy 2.0, submit 1.4], network+composite 9.8, readback 4.7, reply 2.8)
[worker] serve frame 59: 17.6 ms (proxy 3.6 [copy 2.1, submit 1.5], network+composite 9.5, readback 3.2, reply 1.3)
[worker] serve frame 89: 20.7 ms (proxy 6.2 [copy 2.6, submit 3.7], network+composite 8.0, readback 4.8, reply 1.7)
[worker] serve frame 119: 18.2 ms (proxy 2.8 [copy 1.7, submit 1.1], network+composite 9.0, readback 4.8, reply 1.6)
[worker] serve: input stream closed after 120 frame(s), 18.65 ms mean\n

```
