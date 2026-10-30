# run r2026-10-30-r

runner `e44571d7dd12` · entry `minimal-unfused` · env from policy: DLSS5VK_UNFUSED, NS_WORKER_CMD

`uv run python -m minimal --frames 3 --headless --source synthetic --size 2560x1440 --save-after unfused.png --worker-log`

exit **0** after 7.6s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 19535ad (+2321 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 3 done, 0 skipped, 5.365s (0.56 fps headline, 4.26 fps steady), worker exit 0
timing: capture 5.2ms  send 13.8ms  recv 1628.1ms  display 2.9ms   (mean 1649.9ms/frame, 0.6 fps; median 234.6ms/frame, 4.3 fps steady)
  after  -> unfused.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph unfused - reference kernels (DLSS5VK_UNFUSED=1)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3308 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 306.8 ms (proxy 7.6 [copy 5.9, submit 1.7], network+composite 212.0, readback 78.9, reply 8.3)
[worker] serve frame 1: 206.5 ms (proxy 5.4 [copy 3.4, submit 2.0], network+composite 189.2, readback 5.1, reply 6.8)
[worker] serve frame 2: 210.8 ms (proxy 9.7 [copy 6.3, submit 3.4], network+composite 189.9, readback 4.7, reply 6.5)

```
