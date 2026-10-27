# run r2026-10-27-a

runner `40c3f9c1507d` · entry `minimal` · env from policy: NS_WORKER_CMD

`uv run python -m minimal --source window --size 2560x1440 --frames 120 --worker-log --shm --send-ahead 2 --save-before gfn-before.png --save-after gfn-after.png`

exit **2** after 0.0s

```

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.
error: Failed to query Python interpreter
  cause: failed to canonicalize path `/opt/neuralscreen/state/repo/.venv/bin/python`: Permission denied (os error 13)

```
