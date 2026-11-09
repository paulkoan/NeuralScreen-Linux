# run r2026-11-09-capture-transport-probe

runner `005dd2c6ea9e` · entry `pytest` · env from policy: none

`uv run pytest tests/ -q`

exit **1** after 520.7s

gpu before: WARN (resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: chromium (pid 18945, 60.0 MiB)); after: WARN (resident but not contending: signal-desktop (pid 18889, 155.0 MiB); resident but not contending: chromium (pid 18945, 60.0 MiB))

```
_______ test_the_flag_is_not_read_as_a_policy_path __________________

tmp_path = PosixPath('/tmp/pytest-of-paul/pytest-0/test_the_flag_is_not_read_as_a0')

    def test_the_flag_is_not_read_as_a_policy_path(tmp_path):
        """The reported failure, pinned: the message must name the default path, not the flag."""
        r = run("--include-manual")
        combined = r.stdout + r.stderr
        assert "no policy at --include-manual" not in combined, (
            "the flag is being taken as the policy path again - that is the 2026-11-08 report")
>       assert "no policy at /opt/neuralscreen/policy.toml" in combined, (
            "with no policy argument the script must fall back to the default path")
E       AssertionError: with no policy argument the script must fall back to the default path
E       assert 'no policy at /opt/neuralscreen/policy.toml' in 'no WAYLAND_DISPLAY or DISPLAY in this shell\n  run this from a terminal inside the graphical session\n'

tests/test_run_manually.py:53: AssertionError
=========================== short test summary info ============================
SKIPPED [1] tests/test_capture_transport.py:80: capture transports - shmsink yes; shmsrc yes; memfd_create yes; pipe-max-size 1024 KiB (at the cap already); gst-launch-1.0 yes
SKIPPED [1] tests/test_check_model.py:139: no extraction on this box to check
SKIPPED [1] tests/test_check_model.py:176: needs a C++ compiler and the port's src/sha256.h
SKIPPED [1] tests/test_check_model.py:264: needs the extraction and the DLL on this box
SKIPPED [1] tests/test_check_model.py:274: needs the extraction and the DLL on this box
SKIPPED [1] tests/test_check_model.py:290: needs the extraction and the DLL on this box
SKIPPED [1] tests/test_m0_env_gate.py:40: M0 runs on the GPU box only; set NX_RUN_M0=1 to enable
SKIPPED [1] tests/test_m0_env_gate.py:45: M0 runs on the GPU box only; set NX_RUN_M0=1 to enable
SKIPPED [1] tests/test_m0_env_gate.py:50: M0 runs on the GPU box only; set NX_RUN_M0=1 to enable
SKIPPED [1] tests/test_m0_env_gate.py:56: M0 runs on the GPU box only; set NX_RUN_M0=1 to enable
SKIPPED [1] tests/test_m0_env_gate.py:102: M0 runs on the GPU box only; set NX_RUN_M0=1 to enable
SKIPPED [1] tests/test_m0_env_gate.py:112: M0 runs on the GPU box only; set NX_RUN_M0=1 to enable
SKIPPED [1] tests/test_m0_env_gate.py:122: M0 runs on the GPU box only; set NX_RUN_M0=1 to enable
SKIPPED [1] tests/test_m0_env_gate.py:133: M0 runs on the GPU box only; set NX_RUN_M0=1 to enable
SKIPPED [1] tests/test_m0_env_gate.py:141: M0 runs on the GPU box only; set NX_RUN_M0=1 to enable
SKIPPED [1] tests/test_m0_env_gate.py:153: M0 runs on the GPU box only; set NX_RUN_M0=1 to enable
SKIPPED [1] tests/test_m0_env_gate.py:162: M0 runs on the GPU box only; set NX_RUN_M0=1 to enable
SKIPPED [1] tests/test_native_serve.py:113: set NS_ODL_NATIVE_BIN to a built dlss5vk to drive the real mode
SKIPPED [1] tests/test_native_serve_shm.py:54: set NS_ODL_NATIVE_BIN to a built dlss5vk to drive the real mode
SKIPPED [1] tests/test_native_serve_shm.py:119: set NS_ODL_NATIVE_BIN to a built dlss5vk to drive the real mode
SKIPPED [1] tests/test_nr_schedule.py:121: needs the extracted 310.9.16 networks
SKIPPED [1] tests/test_nr_schedule.py:160: needs the extracted 310.9.16 networks
FAILED tests/test_cli_end_to_end.py::test_cli_runs_and_writes_both_pngs - Ass...
FAILED tests/test_cli_end_to_end.py::test_cli_before_and_after_differ - Asser...
FAILED tests/test_cli_end_to_end.py::test_cli_pngs_match_the_capture_resolution
FAILED tests/test_dll_version.py::test_it_reads_the_bundled_runtime - Asserti...
FAILED tests/test_history_sample.py::test_the_history_sample_is_checked_against_the_original
FAILED tests/test_history_sample.py::test_the_history_check_can_fail - Assert...
FAILED tests/test_opendlss_port.py::test_the_composite_is_checked_against_its_authorities
FAILED tests/test_run_manually.py::test_the_flag_is_not_read_as_a_policy_path
8 failed, 586 passed, 22 skipped in 520.20s (0:08:40)

```

stderr:

```
warning: The `native-tls` setting is deprecated and will be removed in a future release. Use `system-certs` instead.

```
