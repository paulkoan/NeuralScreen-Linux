# run r2026-10-30-an

runner `e44571d7dd12` · entry `minimal-small` · env from policy: NS_WORKER_CMD

`xvfb-run -a uv run python -m minimal --frames 120 --headless --source synthetic --size 2560x1440 --no-motion --worker-log`

exit **0** after 11.5s

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model-small
version: repo 6bd6af8 (+20 uncommitted) · worker built from patch 0aabc30ec374 at port 9d08f41 · in sync
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 120 done, 0 skipped, 7.939s (15.12 fps headline, 37.26 fps steady), worker exit 0
timing: capture 4.1ms  send 9.0ms  recv 51.2ms  display 0.0ms   (mean 64.3ms/frame, 15.6 fps; median 26.8ms/frame, 37.3 fps steady)
send spread: min 5.5  median 8.3  max 16.0 ms at frame 3 of 120   (a one-off at frame 3 — not the warm-up, so worth looking at)
recv spread: min 11.0  median 15.0  max 4159.4 ms at frame 0 of 120   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model-small, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 0aabc30ec374cc01893092ebb8538d537e6cd888
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7671 (block30.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3204 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -13.8828..0.4585 mean -1.45525; residual mean -0.0036 -0.0246 -0.0185 (rgb, head/4), logit mean -5.6340; non-finite 0 of 14745600; first 8 -0.2062 -0.3843 -0.4197 -6.5273 -0.1914 -0.3982 -0.4487 -6.0664
[worker] serve frame 0: 177.2 ms (proxy 4.6 [copy 2.2, submit 2.4], network+composite 77.1, readback 95.5, reply 0.0)
[worker] serve frame 1: 58.7 ms (proxy 4.4 [copy 2.1, submit 2.3], network+composite 54.3, readback 0.0, reply 0.0)
[worker] serve frame 2: 59.7 ms (proxy 4.7 [copy 2.3, submit 2.4], network+composite 55.0, readback 0.0, reply 0.0)
[worker] serve frame 29: 13.0 ms (proxy 3.0 [copy 1.9, submit 1.1], network+composite 10.0, readback 0.0, reply 0.0)
[worker] serve frame 59: 18.7 ms (proxy 7.1 [copy 4.7, submit 2.5], network+composite 11.6, readback 0.0, reply 0.0)
[worker] serve frame 89: 13.8 ms (proxy 3.3 [copy 2.3, submit 1.0], network+composite 10.6, readback 0.0, reply 0.0)
[worker] serve frame 119: 11.4 ms (proxy 3.8 [copy 2.5, submit 1.3], network+composite 7.7, readback 0.0, reply 0.0)

```
