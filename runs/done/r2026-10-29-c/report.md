# run r2026-10-29-c

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 30 --headless --source synthetic --size 2560x1440 --save-before before.png --save-after after.png --worker-log`

exit **3** after 5.6s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo bf479bd (+2155 uncommitted) · worker built from patch 819bea6f149e at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (12 modified) patch 819bea6f149ee975b922cfea802402d1bd9b7111
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3269 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve: write(stdout): Bad address
pipeline failed: the worker stopped after 0 of 14745600 reply bytes
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
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 231, in process_one
    result = self._timed("recv", self.worker.recv, index, timeout)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/loop.py", line 198, in _timed
    return fn(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/worker.py", line 390, in recv
    return self.reader.recv(index, timeout)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/protocol.py", line 912, in recv
    raise payload
  File "/opt/neuralscreen/state/repo/protocol.py", line 691, in _run
    data = _read_exact(self._worker.stdout, byte_count)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/neuralscreen/state/repo/protocol.py", line 361, in _read_exact
    raise EOFError(f"the worker stopped after {len(chunks)} of {size} reply bytes")
EOFError: the worker stopped after 0 of 14745600 reply bytes

```
