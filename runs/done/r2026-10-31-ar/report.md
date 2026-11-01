# run r2026-10-31-ar

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --work-scale 0.75 --worker-log`

exit **3** after 1.2s

```
source synthetic  capture 2560x1440  ->  work 1920x1080 (work scale 0.75, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 23b4846 (+2512 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: the client expects NGX upscaling (1920x1080 -> 2560x1440); this worker runs the network at one size. Run the pipeline without --work-scale.
pipeline failed: the worker died while sending frame 0 ([Errno 32] Broken pipe). Last stderr:
  serve: the client expects NGX upscaling (1920x1080 -> 2560x1440); this worker runs the network at one size. Run the pipeline without --work-scale.
Traceback (most recent call last):
  File "/opt/neuralscreen/state/repo/minimal/worker.py", line 385, in send
    send_frame(self.proc, index, rgba, motion, reset, pts,
  File "/opt/neuralscreen/state/repo/protocol.py", line 468, in send_frame
    worker.stdin.write(part)
BrokenPipeError: [Errno 32] Broken pipe

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/opt/neuralscreen/state/repo/minimal/__main__.py", line 266, in main
    summary = pipe.run(frames=args.frames,
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 359, in run
    pair_before, last_after, index = self._serial_loop(frames, on_frame)
                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 432, in _serial_loop
    after = self.process_one(index, present=True)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 236, in process_one
    self._timed("send", self.worker.send, index, frame, self.zero_motion,
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 205, in _timed
    return fn(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/worker.py", line 391, in send
    raise RuntimeError(
RuntimeError: the worker died while sending frame 0 ([Errno 32] Broken pipe). Last stderr:
  serve: the client expects NGX upscaling (1920x1080 -> 2560x1440); this worker runs the network at one size. Run the pipeline without --work-scale.

```
