# run r2026-10-30-s

runner `e44571d7dd12` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 3 --headless --source synthetic --size 2560x1440 --save-after fused.png --worker-log`

exit **0** after 6.8s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo c4a724f (+17 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 3 done, 0 skipped, 5.005s (0.6 fps headline, 12.93 fps steady), worker exit 0
timing: capture 5.5ms  send 14.9ms  recv 1573.3ms  display 3.0ms   (mean 1596.6ms/frame, 0.6 fps; median 77.4ms/frame, 12.9 fps steady)
  after  -> fused.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3654 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 150.2 ms (proxy 8.6 [copy 5.8, submit 2.8], network+composite 52.6, readback 79.9, reply 9.1)
[worker] serve frame 1: 50.1 ms (proxy 8.2 [copy 5.7, submit 2.5], network+composite 26.8, readback 6.3, reply 8.7)
[worker] serve frame 2: 46.6 ms (proxy 6.9 [copy 4.3, submit 2.6], network+composite 27.9, readback 3.5, reply 8.3)

```
