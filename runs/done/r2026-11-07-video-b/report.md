# run r2026-11-07-video-b

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --headless --frames 600 --shm --save-after video-b.png`

exit **0** after 28.6s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 129.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 335.0 MiB)) after waiting 120s; after: WARN (resident but not contending: signal-desktop (pid 18889, 116.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 336.0 MiB))

```
source video  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 59a900d (+2774 uncommitted) · worker built from patch 088280e62d50 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 600 done, 0 skipped, 25.84s (23.22 fps headline, 28.4 fps steady), worker exit 0
timing: capture 6.4ms  send 2.8ms  recv 30.2ms  display 3.2ms   (mean 42.6ms/frame, 23.5 fps; median 35.2ms/frame, 28.4 fps steady)
source: replayed fixtures/stream-1440p-2s.mp4 — 601 frames decoded, 13 loops
send spread: min 1.6  median 2.7  max 6.9 ms at frame 0 of 600   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 20.5  median 23.5  max 3899.3 ms at frame 0 of 600   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.3  median 5.3  max 45.8 ms at frame 483 of 600   (a one-off at frame 483 — not the warm-up, so worth looking at)
  after  -> video-b.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)

```
