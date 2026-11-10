# run r2026-11-09-shm-window

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --source window --size 1920x1080 --shm --capture-transport shm --save-before shm-window-before.png --save-after shm-window-after.png --worker-log`

exit **3** after 10.0s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: chromium (pid 18945, 85.0 MiB); resident but not contending: msedge (pid 1300500, 273.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: chromium (pid 18945, 85.0 MiB); resident but not contending: msedge (pid 1300500, 272.0 MiB))

```
  CreateSession
  session /org/freedesktop/portal/desktop/session/1_5185867/nsl_port
  SelectSources
  Start  (the compositor will ask you to choose a screen)
  stream node=180 serial=7816 0x0
  OpenPipeWireRemote
  window stream reports no size; using the requested 1920x1080
  transport: shared memory (memfd fd=7); one pread per frame
  pipeline pid 2798825: gst-launch-1.0 -q pipewiresrc fd=5 target-object=7816 ! queue max-size-buffers=1 leaky=downstream ! videoconvert ! videoscale ! video/x-raw,format=RGBA,width=1920,height=1080,pixel-aspect-ratio=1/1 ! fdsink fd=7 sync=false
source window  capture 1920x1080  ->  work 1920x1080 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 5cb5ac2 (+54 uncommitted) · worker built from patch 25cf5f62fbc4 at port 9d08f41 · OUT OF SYNC — the worker was built from patch 25cf5f62fbc4, this checkout has a522cd30bbb2: re-apply the patch and rebuild, the run below is not the code in this checkout
version: OUT OF SYNC — the worker was built from patch 25cf5f62fbc4, this checkout has a522cd30bbb2: re-apply the patch and rebuild, the run below is not the code in this checkout
[main] shared memory agreed: 16.6 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 1920x1080, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (18 modified) patch 25cf5f62fbc4c875e5b017bd33306dabf96b720f
[worker] serve: frame channel open (16.6 MB, NeuralScreen_2798266_c7de5637)
[worker] serve: pixel channel open (1920x1080, 8.3 MB, NeuralScreenOut_2798266_92705e)
[worker] serve: mid-frame channel open (8.3 MB, NeuralScreenOut_2798266_92705em)
[main] shared memory: frames in and pixels out through /dev/shm (frame 16.6MB, pixels 8.3MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: vkQueueWaitIdle(queue_) failed: -4
pipeline failed: the worker stopped after 0 of 4 reply bytes
Traceback (most recent call last):
  File "/opt/neuralscreen/state/repo/minimal/__main__.py", line 399, in main
    summary = pipe.run(frames=args.frames,
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 583, in run
    pair_before, last_after, index = self._serial_loop(frames, on_frame)
                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 720, in _serial_loop
    after = self.process_one(index, present=True)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 345, in process_one
    return self._one_frame(index, timeout=timeout, present=present)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 400, in _one_frame
    result = self._timed("recv", self.worker.recv, index, timeout)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 299, in _timed
    return fn(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/worker.py", line 429, in recv
    return self.reader.recv(index, timeout)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/protocol.py", line 1037, in recv
    raise payload
  File "/opt/neuralscreen/state/repo/protocol.py", line 696, in _run
    magic_raw = _read_exact(self._worker.stdout, 4)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/protocol.py", line 441, in _read_exact
    raise EOFError(f"the worker stopped after {len(chunks)} of {size} reply bytes")
EOFError: the worker stopped after 0 of 4 reply bytes

```
