# run r2026-11-10-6-ws-window-b

runner `f98364851fa4` · entry `minimal` · env from policy: NS_WORKER_CMD

policy `28b387ec388f` at /opt/neuralscreen/policy.toml · the file itself is beside this report as policy.toml

`uv run python -m minimal --frames 120 --source window --size 2560x1440 --work-scale 0.75 --shm --save-before ws-window-b-before.png --save-after ws-window-b-after.png --worker-log`

exit **2** after 121.8s

gpu before: WARN (resident but not contending: Telegram (pid 16290, 30.0 MiB); resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: msedge (pid 1300500, 282.0 MiB); resident but not contending: chromium (pid 3132450, 104.0 MiB)) after waiting 30s; after: BUSY (utilization 17%; Telegram (pid 16290, 30.0 MiB); signal-desktop (pid 18889, 155.0 MiB); msedge (pid 1300500, 263.0 MiB); chromium (pid 3132450, 104.0 MiB))

```
  CreateSession
  session /org/freedesktop/portal/desktop/session/1_5767395/nsl_port
  SelectSources
  Start  (the compositor will ask you to choose a screen)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
startup failed: the portal handshake failed (TimeoutError): 

```
