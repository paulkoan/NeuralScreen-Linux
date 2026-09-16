# NeuralScreen MVP — test report

- **run:** 20260916T080456Z (UTC)
- **git:** ec4b7fa on main
- **python:** Python 3.11.15
- **pytest exit:** 1 (FAILURES — see raw/pytest.txt)
- **M0 gate:** included

## Summary line

```
tests/test_m0_env_gate.py::test_m0_no_ngx_core_not_found_error PASSED    [ 29%]
tests/test_m0_env_gate.py::test_m0_no_platform_error PASSED              [ 30%]
================== 1 failed, 55 passed, 15 skipped in 12.92s ===================
```

## Artifacts

| file | what |
|---|---|
| `raw/pytest.txt` | full pytest output |
| `raw/environment.txt` | GPU, driver, Wine, Vulkan, session |
| `raw/wine_ngx_setup.txt` | what the NGX/DXVK setup applied |
| `raw/wine_ngx_environment.txt` | the prefix after setup |
| `raw/m0_gate.txt` | M0 gate output (direct path) |
| `raw/m0_gate_via_core.txt` | M0 gate output with NS_NGX_VIA_CORE=1 |
| `raw/via-core/` | same artifacts for the via-core variant |
| `raw/m1_gate.txt` | M1 gate: the live path end to end |
| `raw/m1/before.png` | the frame captured from the screen |
| `raw/m1/after.png` | the same frame after the NR pass |
| `raw/m1/analysis.txt` | how much the pass changed the frame |
| `raw/dlss5-feed-host.log` | the worker's own log |

## What to do with this

Commit and push `test-results/20260916T080456Z/` — it is read directly from the repo.
