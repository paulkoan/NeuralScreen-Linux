# run r2026-11-07-videosrc

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --headless --frames 120 --shm --motion-guides --worker-log --save-after videosrc-after.png`

exit **1** after 16.6s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 116.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 336.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 116.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 335.0 MiB))

```
source video  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo c3aa6fb (+37 uncommitted) · worker built from patch 088280e62d50 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 120 done, 0 skipped, 14.01s (8.57 fps headline, 18.26 fps steady), worker exit 0
timing: capture 10.9ms  send 5.6ms  recv 69.9ms  display 3.9ms   (mean 90.3ms/frame, 11.1 fps; median 54.8ms/frame, 18.3 fps steady)
send spread: min 3.8  median 5.5  max 12.2 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 29.2  median 34.1  max 4207.1 ms at frame 0 of 120   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 5.1  median 10.6  max 50.0 ms at frame 43 of 120   (a one-off at frame 43 — not the warm-up, so worth looking at)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /opt/neuralscreen/model, shaders /opt/neuralscreen/port/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (17 modified) patch 088280e62d5047a684d65df2a3fb2dcf84d5f9d1
[worker] serve: frame channel open (29.5 MB, NeuralScreen_2637869_99a351dc)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_2637869_1a1f8f)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: blend scale 0.7397 (block70.layer0.blend_scale)
[worker] serve: graph fused (DLSS5VK_UNFUSED not set)
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 3287 ms
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve: head -10.5703..2.1426 mean -0.54321; residual mean 0.1111 0.0057 0.1539 (rgb, head/4), logit mean -3.2555; non-finite 0 of 14745600; first 8 0.4094 0.6533 -0.3296 -0.3892 0.4255 0.6670 -0.3159 -0.2235
[worker] serve frame 0: 147.8 ms (proxy 7.7 [copy 5.4, submit 2.3], network+composite 52.7, readback 80.6, reply 6.8)
[worker] serve frame 1: 42.3 ms (proxy 7.1 [copy 3.1, submit 3.9], network+composite 26.6, readback 6.7, reply 1.9)
[worker] serve frame 2: 42.7 ms (proxy 7.9 [copy 4.7, submit 3.1], network+composite 28.5, readback 3.8, reply 2.5)
[worker] serve frame 29: 29.5 ms (proxy 6.9 [copy 4.0, submit 2.9], network+composite 16.8, readback 3.5, reply 2.3)
[worker] serve frame 59: 27.8 ms (proxy 6.1 [copy 4.2, submit 1.9], network+composite 15.9, readback 3.2, reply 2.6)
[worker] serve frame 89: 31.1 ms (proxy 5.6 [copy 3.3, submit 2.3], network+composite 18.1, readback 5.1, reply 2.2)
[worker] serve frame 119: 36.4 ms (proxy 7.9 [copy 5.1, submit 2.7], network+composite 19.8, readback 5.8, reply 3.0)
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/opt/neuralscreen/state/repo/minimal/__main__.py", line 489, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "/opt/neuralscreen/state/repo/minimal/__main__.py", line 457, in main
    print(f"prefetch: drained {pf['drained']} frames on its own thread, "
                               ~~^^^^^^^^^^^
KeyError: 'drained'

```
