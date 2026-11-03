# run r2026-11-03-split

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 60 --headless --source synthetic --size 2560x1440 --shm --worker-env DLSS5VK_SERVE_SPLIT=1 --worker-log`

exit **0** after 5.8s

gpu before: WARN (resident but not contending: signal-desktop (pid 43509, 58.0 MiB); resident but not contending: Telegram (pid 988444, 36.0 MiB); resident but not contending: signon-ui (pid 3062205, 17.0 MiB)); after: BUSY (utilization 58%; signal-desktop (pid 43509, 58.0 MiB); Telegram (pid 988444, 36.0 MiB); signon-ui (pid 3062205, 17.0 MiB))

```
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo dc67e0a (+35 uncommitted) · worker built from patch 088280e62d50 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 60 done, 0 skipped, 5.05s (11.88 fps headline, 52.03 fps steady), worker exit 0
timing: capture 3.1ms  send 1.8ms  recv 76.5ms  display 0.0ms   (mean 81.4ms/frame, 12.3 fps; median 19.2ms/frame, 52.0 fps steady)
send spread: min 1.5  median 1.7  max 6.6 ms at frame 0 of 60   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 13.9  median 14.8  max 3722.2 ms at frame 0 of 60   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 088280e62d5047a684d65df2a3fb2dcf84d5f9d1
[worker] serve: frame channel open (29.5 MB, NeuralScreen_2950739_da04f9ac)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_2950739_9300c1)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field: the reprojection is the identity
[worker] serve: and the five-tap history filter is the centre tap, which is the pixel
[worker] serve: itself - so no published byte can move for it
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2882 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -6.5039..0.5020 mean -0.90768; residual mean 0.0144 0.0112 0.0110 (rgb, head/4), logit mean -3.7771; non-finite 0 of 14745600; first 8 -0.0168 -0.0381 -0.0440 -4.9414 -0.0143 -0.0451 -0.0468 -4.4062
[worker] serve frame 0: 98.4 ms (proxy 3.6 [copy 2.5, submit 1.1], network 11.0, composite 0.2, readback 63.1, reply 0.0)
[worker] serve frame 1: 15.1 ms (proxy 2.6 [copy 1.7, submit 0.9], network 11.1, composite 0.3, readback 0.0, reply 0.0)
[worker] serve frame 2: 14.7 ms (proxy 2.5 [copy 1.7, submit 0.9], network 11.1, composite 0.3, readback 0.0, reply 0.0)
[worker] serve frame 29: 14.0 ms (proxy 2.5 [copy 1.6, submit 0.9], network 10.5, composite 0.3, readback 0.0, reply 0.0)

```
