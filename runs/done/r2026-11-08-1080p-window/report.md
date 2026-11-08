# run r2026-11-08-1080p-window

runner `005dd2c6ea9e` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --frames 120 --source window --size 1920x1080 --shm --save-before 1080p-window-before.png --save-after 1080p-window-after.png --worker-log`

exit **2** after 122.3s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 162.0 MiB); resident but not contending: chromium (pid 18945, 99.0 MiB); resident but not contending: msedge (pid 54723, 318.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 162.0 MiB); resident but not contending: chromium (pid 18945, 99.0 MiB); resident but not contending: msedge (pid 54723, 321.0 MiB))

```
  CreateSession
  session /org/freedesktop/portal/desktop/session/1_2459590/nsl_port
  SelectSources
  Start  (the compositor will ask you to choose a screen)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
startup failed: the portal handshake failed (TimeoutError): 

```
