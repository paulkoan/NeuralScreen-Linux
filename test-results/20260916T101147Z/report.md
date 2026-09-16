# NeuralScreen MVP — test report

- **run:** 20260916T101147Z (UTC)
- **git:** 1de22b3 on main
- **python:** Python 3.11.15
- **pytest exit:** 1 (FAILURES — see raw/pytest.txt)
- **M0 gate:** included

## Summary line

```
tests/test_m0_env_gate.py::test_m0_no_ngx_core_not_found_error PASSED    [ 39%]
tests/test_m0_env_gate.py::test_m0_no_platform_error PASSED              [ 40%]
================== 1 failed, 66 passed, 15 skipped in 12.88s ===================
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
| `raw/m1_gate.txt` | M1 gate: both variants |
| `raw/m1/pass/` | NR pass on a known test card — the deciding artifact |
| `raw/m1/capture/` | the same on the real screen (capture test) |
| `raw/m1/*/analysis.txt` | how much the pass changed each frame |
| `raw/dlss5-feed-host.log` | the worker's own log |

## What to do with this

Commit and push `test-results/20260916T101147Z/` — it is read directly from the repo.
