"""M0 — the environment gate, as a test rather than a script.

This is the single question that decides whether the Linux port is viable at
all: does the DLSS5 NR worker initialise NGX under Wine on this machine?

It needs no game, no display window, and no Python pipeline. `nvngx.dll --test`
builds a D3D12 device, creates NGX feature 18 and runs 300 evaluates on a
synthetic 640x360 pattern, then exits 0 if at least 250 succeeded.

These tests are skipped unless NX_RUN_M0=1 is set, so the default suite stays
green on machines (like CI) with no GPU. Run them with:

    NX_RUN_M0=1 python -m pytest tests/test_m0_env_gate.py -v -s
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
NATIVE = REPO / "native"
WORKER = NATIVE / "nvngx.dll"
NR_DLL = NATIVE / "nvngx_dlssnr.dll"

pytestmark = pytest.mark.skipif(
    os.environ.get("NX_RUN_M0") != "1",
    reason="M0 runs on the GPU box only; set NX_RUN_M0=1 to enable")


def _require(path: Path, what: str) -> None:
    if not path.is_file():
        pytest.fail(f"{what} is missing: {path}")


def test_worker_binary_is_present():
    """The worker is a PE executable named nvngx.dll (NGX requires the name)."""
    _require(WORKER, "the worker binary")


def test_nr_runtime_is_present():
    """nvngx_dlssnr.dll is gitignored (159 MB) and must be supplied manually."""
    _require(NR_DLL, "the NVIDIA NR runtime (nvngx_dlssnr.dll)")


def test_sidecar_dlls_are_present():
    """The worker statically imports SpoutDX.dll, which imports Spout.dll."""
    _require(NATIVE / "SpoutDX.dll", "SpoutDX.dll")
    _require(NATIVE / "Spout.dll", "Spout.dll")


def test_wine_is_available():
    from shutil import which
    if which("wine") is None:
        pytest.fail("wine is not installed — M0 cannot run")


from minimal.worker import DLL_OVERRIDES, worker_env


@pytest.fixture(scope="module")
def m0_result():
    """Run the worker's built-in test mode once and capture its output.

    Skips when wine is missing rather than erroring: test_wine_is_available
    below already reports that case with a readable message, and four
    FileNotFoundError tracebacks on top of it are just noise.
    """
    from shutil import which
    if which("wine") is None:
        pytest.skip("wine is not installed — M0 cannot run (see test_wine_is_available)")

    log = NATIVE / "dlss5-feed-host.log"
    if log.exists():
        log.unlink()

    # worker_env() is the same launch environment the pipeline and the gate use
    # — see tests/test_worker_env_consistency.py, which fails if they drift.
    env = worker_env()

    proc = subprocess.run(
        ["wine", str(WORKER), "--test"],
        cwd=str(NATIVE), env=env, capture_output=True, text=True, timeout=600)

    log_text = log.read_text(errors="replace") if log.exists() else ""
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "log": log_text,
        "env": {
            "WINEDLLOVERRIDES": env.get("WINEDLLOVERRIDES"),
            "DXVK_ENABLE_NVAPI": env.get("DXVK_ENABLE_NVAPI"),
        },
    }


def test_m0_uses_the_canonical_environment(m0_result):
    """The run that produced the log used the expected overrides.

    Without this the diagnostics below could be explaining an earlier failure
    that the environment had already fixed.
    """
    assert m0_result["env"]["WINEDLLOVERRIDES"] == DLL_OVERRIDES
    assert m0_result["env"]["DXVK_ENABLE_NVAPI"] == "1"


def test_m0_no_ngx_core_not_found_error(m0_result):
    """0xBAD00001 means NGX Core was never found — a wiring problem, not a GPU one."""
    combined = m0_result["stdout"] + m0_result["stderr"] + m0_result["log"]
    assert "0xBAD00001" not in combined, (
        "NGX Core is still not being found. The registry entry is missing or "
        "wrong — run tools/wine_ngx_setup.sh.\n"
        + "\n".join(l for l in combined.splitlines()
                    if "NGX" in l or "ngx" in l)[-1500:])


def test_m0_no_platform_error(m0_result):
    """0xBAD00002 means NGX Core loaded but NVAPI could not report the GPU."""
    combined = m0_result["stdout"] + m0_result["stderr"] + m0_result["log"]
    assert "0xBAD00002" not in combined, (
        "NGX Core's platform check failed. dxvk-nvapi is not answering: check "
        "DXVK_ENABLE_NVAPI=1, that DXVK's dxgi.dll and d3d11.dll are installed "
        "and overridden, and that dxvk-nvapi's nvapi64.dll is present.\n"
        + "\n".join(l for l in combined.splitlines()
                    if "nvapi" in l.lower() or "NvAPI" in l)[-1500:])


def test_m0_worker_runs(m0_result):
    """The worker must at least start under Wine and reach its test path."""
    combined = m0_result["stdout"] + m0_result["stderr"] + m0_result["log"]
    assert "dlss5-feed-host64" in combined or "host" in combined, (
        "the worker produced no recognisable output at all — Wine did not run it. "
        f"rc={m0_result['returncode']}\n{combined[-2000:]}")


def test_m0_ngx_initialises(m0_result):
    """NGX must initialise: this is the gate. A failure names its own stage."""
    combined = m0_result["stdout"] + m0_result["stderr"] + m0_result["log"]
    assert "NVSDK_NGX_D3D12_Init" in combined, (
        "the worker never reached NGX init — it died earlier (D3D12 device, "
        f"adapter selection). rc={m0_result['returncode']}\n{combined[-2000:]}")
    assert "Success" in combined, (
        "NVSDK_NGX_D3D12_Init did not report Success.\n"
        + "\n".join(l for l in combined.splitlines()
                    if "Init" in l or "adapter" in l or "device" in l)[-2000:])


def test_m0_feature18_is_created(m0_result):
    """NGX feature 18 must be created — the DLSS5 neural-rendering feature."""
    combined = m0_result["stdout"] + m0_result["stderr"] + m0_result["log"]
    assert "feature 18 ready" in combined, (
        "the NR feature was never created.\n"
        + "\n".join(l for l in combined.splitlines()
                    if "feature" in l.lower() or "create" in l.lower())[-2000:])


def test_m0_evaluates_succeed(m0_result):
    """At least 250 of the 300 evaluates must succeed."""
    combined = m0_result["stdout"] + m0_result["stderr"] + m0_result["log"]
    m = re.search(r"--test finished: (\d+)/(\d+) evaluates succeeded", combined)
    assert m, f"the worker never reported a test summary.\n{combined[-2000:]}"
    good, total = int(m.group(1)), int(m.group(2))
    assert good >= 250, f"only {good}/{total} evaluates succeeded"
    assert m0_result["returncode"] == 0, (
        f"the worker exited {m0_result['returncode']} despite {good}/{total}")