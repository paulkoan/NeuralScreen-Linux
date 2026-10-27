# run r2026-10-13-e

runner `40c3f9c1507d` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source image --input-image fixtures/youtube-1440p.png --headless --frames 61 --worker-log --shm --no-motion --send-ahead 2 --save-before before.png --save-after after.png`

exit **2** after 0.1s

```

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
error: Failed to query Python interpreter
  cause: failed to canonicalize path `/opt/neuralscreen/state/repo/.venv/bin/python`: Permission denied (os error 13)

```
