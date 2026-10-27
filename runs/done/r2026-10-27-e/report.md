# run r2026-10-27-e

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source image --input-image fixtures/stream-1440p-jpeg-q20.png --headless --frames 3 --worker-log --shm --no-motion --send-ahead 2 --save-before before.png --save-after after.png --bypass`

exit **0** after 1.5s

```
source image (fixtures/stream-1440p-jpeg-q20.png)  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 2cbbda1 (+6 uncommitted) · worker built from patch f0c60a1c2224 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 3 done, 0 skipped, 0.04s (75.33 fps), worker exit 0
timing: capture 3.0ms  send 2.7ms  recv 4.3ms  display 2.8ms   (total 12.7ms/frame, 78.5 fps)
  before -> before.png
  after  -> after.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (12 modified) patch f0c60a1c2224d1bbbe7ee86c692d391fb24359dc
[worker] serve: frame channel open (29.5 MB, NeuralScreen_2540566_1059e1db)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_2540566_10cdad)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it

```
