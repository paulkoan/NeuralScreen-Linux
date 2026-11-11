# run r2026-11-11-9-1-pub-on

runner `415e2181914a` · entry `minimal-small` · env from policy: NS_WORKER_CMD

policy `92cc2c01922f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --source video --input-video fixtures/stream-1440p-2s.mp4 --size 2560x1440 --work-scale 0.75 --headless --frames 300 --shm --worker-env DLSS5VK_SERVE_SPLIT=1 --publish-work --worker-log --save-after small-pub-on-after.png`

exit **2** after 0.5s

gpu before: WARN [util 4% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 153.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 287.0 MiB)); after: WARN [util 4% of the 25% bar] (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 153.0 MiB); resident but not contending: msedge (pid 1300500, 293.0 MiB); resident but not contending: chromium (pid 3132450, 251.0 MiB))

```

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
usage: minimal [-h] [--frames FRAMES] [--monitor MONITOR] [--bgra]
               [--source {auto,screen,wayland,window,synthetic,image,video}]
               [--capture-no-scale] [--capture-transport {pipe,shm}]
               [--size WxH] [--input-image PATH] [--input-video PATH]
               [--interpolate] [--interp-pace-ms MS] [--gil-switch-ms MS]
               [--param NAME=VALUE] [--work-scale F] [--hotkeys] [--indicator]
               [--no-indicator] [--ab-alternate SECONDS] [--report-gpu]
               [--report-diff] [--save-diff PATH] [--diff-gain DIFF_GAIN]
               [--windowed] [--prefetch] [--worker-env KEY=VALUE] [--bypass]
               [--send-ahead N] [--frame-timeout S] [--writev] [--shm]
               [--no-shm] [--motion] [--no-motion] [--motion-guides]
               [--motion-small] [--worker-log] [--headless]
               [--save-before PATH] [--save-after PATH] [--save-mid PATH]
               [--list-monitors]
minimal: error: unrecognized arguments: --publish-work

```
