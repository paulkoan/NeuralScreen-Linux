# run r2026-11-07-video-a

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --headless --frames 600 --shm --save-after video-a.png`

exit **0** after 29.4s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 116.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 336.0 MiB)) after waiting 270s; after: WARN (resident but not contending: signal-desktop (pid 18889, 116.0 MiB); resident but not contending: chromium (pid 18945, 70.0 MiB); resident but not contending: msedge (pid 54723, 335.0 MiB))

```
source video  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
version: repo 59a900d (+38 uncommitted) · worker built from patch 088280e62d50 at port 9d08f41 · in sync
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
pygame 2.6.1 (SDL 2.28.4, Python 3.11.15)
Hello from the pygame community. https://www.pygame.org/contribute.html
frames: 600 done, 0 skipped, 26.927s (22.28 fps headline, 27.24 fps steady), worker exit 0
timing: capture 7.0ms  send 2.8ms  recv 31.1ms  display 3.5ms   (mean 44.4ms/frame, 22.5 fps; median 36.7ms/frame, 27.2 fps steady)
source: replayed fixtures/stream-1440p-2s.mp4 — 601 frames decoded, 13 loops
send spread: min 1.7  median 2.7  max 6.1 ms at frame 0 of 600   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
recv spread: min 21.2  median 24.3  max 3899.8 ms at frame 0 of 600   (one-off at frame 0 — sent before the worker's first reply lands, so the warm-up, not a per-frame cost)
capture spread: min 3.9  median 5.8  max 72.6 ms at frame 527 of 600   (a one-off at frame 527 — not the warm-up, so worth looking at)
  after  -> video-a.png

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)

```
