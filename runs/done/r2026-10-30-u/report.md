# run r2026-10-30-u

runner `e44571d7dd12` · entry `minimal-small` · env from policy: NS_WORKER_CMD

`xvfb-run -a uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --save-after small-120.png --worker-log`

exit **0** after 16.9s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo 54b04da (+2346 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 11.289s (10.63 fps headline, 17.74 fps steady), worker exit 0
timing: capture 3.5ms  send 14.3ms  recv 71.2ms  display 3.2ms   (mean 92.2ms/frame, 10.8 fps; median 56.4ms/frame, 17.7 fps steady)
send spread: min 11.1  median 14.1  max 19.0 ms at frame 11 of 120   (steady — a fixed interval, not contention)
recv spread: min 30.1  median 35.7  max 4180.5 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
  after  -> small-120.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3299 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -13.8828..0.4585 mean -1.45525; residual mean -0.0036 -0.0246 -0.0185 (rgb, head/4), logit mean -5.6340; non-finite 0 of 14745600; first 8 -0.2062 -0.3843 -0.4197 -6.5273 -0.1914 -0.3982 -0.4487 -6.0664
[worker] serve frame 0: 135.9 ms (proxy 5.6 [copy 3.7, submit 1.9], network+composite 43.5, readback 78.5, reply 8.2)
[worker] serve frame 1: 42.2 ms (proxy 7.9 [copy 4.4, submit 3.4], network+composite 23.2, readback 4.2, reply 7.0)
[worker] serve frame 2: 43.9 ms (proxy 8.1 [copy 5.2, submit 2.9], network+composite 23.6, readback 3.7, reply 8.5)
[worker] serve frame 29: 35.4 ms (proxy 7.7 [copy 5.8, submit 1.9], network+composite 15.3, readback 4.1, reply 8.2)
[worker] serve frame 59: 34.8 ms (proxy 8.6 [copy 5.1, submit 3.5], network+composite 12.9, readback 4.9, reply 8.5)
[worker] serve frame 89: 30.2 ms (proxy 7.7 [copy 5.8, submit 2.0], network+composite 11.1, readback 4.0, reply 7.4)
[worker] serve frame 119: 29.8 ms (proxy 5.7 [copy 3.1, submit 2.7], network+composite 13.2, readback 3.7, reply 7.1)

```
