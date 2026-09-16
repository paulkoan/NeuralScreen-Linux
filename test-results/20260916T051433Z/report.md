# NeuralScreen MVP — test report

- **run:** 20260916T051433Z (UTC)
- **git:** d98121d on main
- **python:** Python 3.11.15
- **pytest exit:** 1 (FAILURES — see raw/pytest.txt)
- **M0 gate:** included

## Summary line

```
E     MESA-EGL: warning: egl: failed to create dri2 screen
E     MESA-EGL: warning: egl: failed to create dri2 screen
================== 3 failed, 42 passed, 15 skipped in 10.93s ===================
```

## Artifacts

| file | what |
|---|---|
| `raw/pytest.txt` | full pytest output |
| `raw/environment.txt` | GPU, driver, Wine, Vulkan, session |
| `raw/m0_gate.txt` | M0 gate output |
| `raw/dlss5-feed-host.log` | the worker's own log |

## What to do with this

Commit and push `test-results/20260916T051433Z/` — it is read directly from the repo.
