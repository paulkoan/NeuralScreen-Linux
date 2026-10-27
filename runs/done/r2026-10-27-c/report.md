# run r2026-10-27-c

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source window --size 2560x1440 --frames 120 --worker-log --shm --send-ahead 2 --save-before gfn-before.png --save-after gfn-after.png`

exit **0** after 48.0s

```
  CreateSession
  session /org/freedesktop/portal/desktop/session/1_703269/nsl_port
  SelectSources
  Start  (the compositor will ask you to choose a screen)
  stream node=207 serial=4441 0x0
  OpenPipeWireRemote
  window stream reports no size; using the requested 2560x1440
  pipeline pid 1498073: gst-launch-1.0 -q pipewiresrc fd=5 target-object=4441 ! videoconvert ! videoscale ! video/x-raw,format=RGBA,width=2560,height=1440,pixel-aspect-ratio=1/1 ! queue max-size-buffers=1 leaky=downstream ! fdsink fd=1
source window  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 92da3bd (+4 uncommitted) · worker built from patch f0c60a1c2224 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 14.208s (8.45 fps), worker exit 0
timing: capture 27.7ms  send 9.7ms  recv 65.8ms  display 12.6ms   (total 115.7ms/frame, 8.6 fps)
send spread: min 4.7  median 9.5  max 18.3 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 0.1  median 20.3  max 5457.2 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
capture spread: min 19.4  median 27.3  max 58.5 ms at frame 1 of 120   (a one-off at frame 1 — not the warm-up, so worth looking at)
display spread: min 6.7  median 12.4  max 40.6 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
capture split: wait 0.1ms  read 27.4ms   (read ~19ms at 2560x1440 means we are draining a stocked pipe; read far above that means the compositor was dribbling)
capture cpu: the pipeline used 9.99s over 14.21s = 70% of one core
          ! that work runs while the worker waits: the same 2560x1440 frame cost send 114.2ms through the portal against 67.3ms produced synthetically
  before -> gfn-before.png
  after  -> gfn-after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (12 modified) patch f0c60a1c2224d1bbbe7ee86c692d391fb24359dc
[worker] serve: frame channel open (29.5 MB, NeuralScreen_1495198_30feb4ae)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_1495198_c9cc4c)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3987 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -9.0781..0.7104 mean -1.10982, non-finite 0 of 15073280; first 8 -0.0662 0.0403 -0.0043 -3.9941 -0.0602 0.0400 -0.0029 -3.8809
[worker] serve frame 0: 167.3 ms (proxy 15.6, network+composite 46.5, readback 92.9, reply 12.2)
[worker] serve frame 1: 58.2 ms (proxy 19.9, network+composite 21.3, readback 10.4, reply 6.5)
[worker] serve frame 2: 58.9 ms (proxy 20.7, network+composite 17.5, readback 14.0, reply 6.7)
[worker] serve frame 29: 54.1 ms (proxy 20.1, network+composite 17.0, readback 10.1, reply 7.0)
[worker] serve frame 59: 67.2 ms (proxy 23.5, network+composite 16.5, readback 19.3, reply 7.9)
[worker] serve frame 89: 60.1 ms (proxy 24.6, network+composite 17.2, readback 11.7, reply 6.6)
[worker] serve frame 119: 41.7 ms (proxy 18.4, network+composite 14.3, readback 4.8, reply 4.2)

```
