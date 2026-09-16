# NeuralScreen MVP — test report

- **run:** 20260916T152209Z (UTC)
- **git:** be451aa on main
- **python:** Python 3.11.15
- **pytest exit:** 0 (all passed)
- **M0 gate:** not run (pass --m0)

## Summary line

```
tests/test_m0_env_gate.py::test_m0_no_ngx_core_not_found_error SKIPPED   [ 44%]
tests/test_m0_env_gate.py::test_m0_no_platform_error SKIPPED (M0 run...) [ 45%]
======================= 106 passed, 26 skipped in 6.40s ========================
```

## Artifacts

| file | what |
|---|---|
| `raw/pytest.txt` | full pytest output |
| `raw/environment.txt` | GPU, driver, Wine, Vulkan, session |
| `raw/m1_gate.txt` | M1 gate: both variants |
| `raw/m1/pass/` | NR pass on a known test card — the deciding artifact |
| `raw/m1/capture/` | the same on the real screen (capture test) |
| `raw/m1/*/analysis.txt` | how much the pass changed each frame |
| `raw/dlss5-feed-host.log` | the worker's own log |

## What to do with this

Commit and push `test-results/20260916T152209Z/` — it is read directly from the repo.
