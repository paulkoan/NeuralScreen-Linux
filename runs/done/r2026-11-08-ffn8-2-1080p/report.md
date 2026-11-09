# run r2026-11-08-ffn8-2-1080p

runner `005dd2c6ea9e` · entry `port-profile` · env from policy: none

`bash tools/port_profile.sh 1920 1080`

exit **1** after 3.9s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: chromium (pid 18945, 60.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: chromium (pid 18945, 60.0 MiB))

```
binary: /opt/neuralscreen/port/build/dlss5vk
model:  /opt/neuralscreen/model
size:   1920x1080, minimum of 7 frames per dispatch

maxComputeSharedMemorySize 49152 bytes
400 trivial dispatches + barriers: 0.409 ms (1.02 us each)

```

stderr:

```
error: vkQueueWaitIdle(queue_) failed: -4

```
