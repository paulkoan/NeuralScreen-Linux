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


@pytest.fixture(scope="module")
def m0_result():
    """Run the worker's built-in test mode once and capture its output."""
    log = NATIVE / "dlss5-feed-host.log"
    if log.exists():
        log.unlink()

    env = os.environ.copy()
    env.setdefault("WINEPREFIX", os.path.expanduser("~/.neuralscreen/wine"))
    # The worker loads nvngx_dlssnr.dll from its own directory.
    env["WINEDLLOVERRIDES"] = "nvngx_dlssnr=n"

    proc = subprocess.run(
        ["wine", str(WORKER), "--test"],
        cwd=str(NATIVE), env=env, capture_output=True, text=True, timeout=600)

    log_text = log.read_text(errors="replace") if log.exists() else ""
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "log": log_text,
    }


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