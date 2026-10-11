# run r2026-10-11-g

`uv run python -m minimal --source image --input-image fixtures/youtube-1440p.png --headless --frames 60 --worker-log --shm --no-motion --send-ahead 2`

exit **0** after 6.1s

```
source image (fixtures/youtube-1440p.png)  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /home/paul/dev/OpenDLSS-NR/build/dlss5vk serve --model /home/paul/dev/odl-model
version: repo 9adc8d9 (+4 uncommitted) · worker built from patch ea90414e2b00 at port 9d08f41 · OUT OF SYNC — the worker was built from patch ea90414e2b00, this checkout has c2c4279a9623: re-apply the patch and rebuild, the run below is not the code in this checkout
version: OUT OF SYNC — the worker was built from patch ea90414e2b00, this checkout has c2c4279a9623: re-apply the patch and rebuild, the run below is not the code in this checkout
[main] shared memory agreed: 29.5 MB, the frame does not go through the pipe
frame 0 is the worker's warm-up: the window stays black until its first answer lands
frames: 60 done, 0 skipped, 5.442s (11.03 fps), worker exit 0
timing: capture 1.8ms  send 2.1ms  recv 79.9ms  display 4.0ms   (total 87.9ms/frame, 11.4 fps)
send spread: min 1.6  median 2.0  max 8.7 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)
recv spread: min 12.1  median 16.6  max 3805.4 ms at frame 0 of 60   (one-off at frame 0 — the worker's warm-up, not a per-frame cost)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
[worker] serve: 2560x1440, model /home/paul/dev/odl-model, shaders /home/paul/dev/OpenDLSS-NR/build/shaders, seed 0
[worker] serve: built from port 9d08f41 (11 modified) patch ea90414e2b0055cd1e7477c260e98faf3bb84571
[worker] serve: frame channel open (29.5 MB, NeuralScreen_3448529_4cc23ed8)
[worker] serve: pixel channel open (2560x1440, 14.7 MB, NeuralScreenOut_3448529_08f82e)
[main] shared memory: frames in and pixels out through /dev/shm (frame 29.5MB, pixels 14.7MB)
[worker] serve: the caller declared no motion field (nothing here reads one)
[worker] serve: device NVIDIA GeForce RTX 4080 SUPER
[worker] serve: warming up (the PTX modules are JIT-compiled on first use)
[worker] serve: warm-up 2970 ms
[worker] serve: frame 0 carries reset (no history is kept, so it is a no-op)
[worker] serve: head -8.7188..0.7407 mean -1.05684, non-finite 0 of 15073280; first 8 0.0334 0.0340 0.0328 -4.8047 0.0280 0.0312 0.0285 -4.6172
[worker] serve frame 0: 77.8 ms (proxy 2.5, network+composite 19.7, readback 49.6, reply 6.0)
[worker] serve frame 1: 22.3 ms (proxy 3.9, network+composite 12.7, readback 4.2, reply 1.4)
[worker] serve frame 2: 19.7 ms (proxy 3.4, network+composite 12.2, readback 2.7, reply 1.4)
[worker] serve frame 29: 21.9 ms (proxy 4.4, network+composite 12.2, readback 3.8, reply 1.6)
[worker] serve frame 59: 19.9 ms (proxy 3.8, network+composite 11.8, readback 2.9, reply 1.4)

```
