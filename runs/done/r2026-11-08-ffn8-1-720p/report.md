# run r2026-11-08-ffn8-1-720p

runner `005dd2c6ea9e` · entry `port-profile` · env from policy: none

`bash tools/port_profile.sh 1280 720`

exit **1** after 3.6s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: chromium (pid 18945, 60.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: chromium (pid 18945, 60.0 MiB))

```
binary: /opt/neuralscreen/port/build/dlss5vk
model:  /opt/neuralscreen/model
size:   1280x720, minimum of 7 frames per dispatch

maxComputeSharedMemorySize 49152 bytes
400 trivial dispatches + barriers: 0.421 ms (1.05 us each)

```

stderr:

```
error: vkQueueWaitIdle(queue_) failed: -4

```
