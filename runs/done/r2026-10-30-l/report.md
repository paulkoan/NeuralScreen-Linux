# run r2026-10-30-l

runner `e44571d7dd12` · entry `ngx-live` · env from policy: NS_NR_PRESET, NS_WORKER_CMD

`xvfb-run -a uv run python -m minimal --frames 3 --headless --source synthetic --size 2560x1440 --save-after ngx-live.png --worker-log`

exit **3** after 3.6s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: bash native/run_worker.sh --prefix /opt/neuralscreen/wine
version: repo 2e21621 (+12 uncommitted) · worker reports no stamp · unknown — the worker reports no stamp (not the native mode, or not rebuilt)
frame 0 is the worker's warm-up: the window stays black until its first answer lands

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] bash: native/run_worker.sh: No such file or directory
pipeline failed: the worker died while sending frame 0 ([Errno 32] Broken pipe). Last stderr:
  bash: native/run_worker.sh: No such file or directory
Traceback (most recent call last):
  File "/opt/neuralscreen/state/repo/minimal/worker.py", line 376, in send
    send_frame(self.proc, index, rgba, motion, reset, pts,
  File "/opt/neuralscreen/state/repo/protocol.py", line 468, in send_frame
    worker.stdin.write(part)
BrokenPipeError: [Errno 32] Broken pipe

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/opt/neuralscreen/state/repo/minimal/__main__.py", line 246, in main
    summary = pipe.run(frames=args.frames,
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 351, in run
    pair_before, last_after, index = self._serial_loop(frames, on_frame)
                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 423, in _serial_loop
    after = self.process_one(index, present=True)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 229, in process_one
    self._timed("send", self.worker.send, index, frame, self.zero_motion,
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 198, in _timed
    return fn(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/worker.py", line 382, in send
    raise RuntimeError(
RuntimeError: the worker died while sending frame 0 ([Errno 32] Broken pipe). Last stderr:
  bash: native/run_worker.sh: No such file or directory

```
