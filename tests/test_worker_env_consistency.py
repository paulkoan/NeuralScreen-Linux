"""The worker's launch environment must be identical everywhere it is set.

Three places launch the same worker with the same DLL overrides:

    minimal/worker.py        (the MVP pipeline)
    native/run_worker.sh     (the launcher the pipeline and M0 both use)
    tools/m0_env_gate.sh     (the gate)

bash cannot import the Python constant, so the string is duplicated. These
tests fail if any copy drifts. That matters more than it looks: a gate that
reports PASS while the pytest M0 run fails (or the reverse) is a puzzle
instead of a diagnosis, and the two failures we have already hit —
0xBAD00001 for a missing NGX Core, 0xBAD00002 for NVAPI being unreachable —
were both caused by launch environment, not by the code under test.

Unlike the M0 tests these are NOT gated behind NX_RUN_M0: they compare text
and need no GPU, Wine or NVIDIA runtime.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from minimal.worker import DLL_OVERRIDES, ENABLE_NVAPI

REPO = Path(__file__).resolve().parent.parent
RUN_WORKER = REPO / "native" / "run_worker.sh"
M0_GATE = REPO / "tools" / "m0_env_gate.sh"


def _sources() -> list[tuple[str, str]]:
    out = []
    for path in (RUN_WORKER, M0_GATE):
        if path.is_file():
            out.append((path.name, path.read_text(errors="replace")))
    return out


def test_the_overrides_are_not_empty():
    """A guard so a refactor cannot silently make every check below vacuous."""
    assert "d3d12=n,b" in DLL_OVERRIDES
    assert "d3d11=n,b" in DLL_OVERRIDES, (
        "d3d11 is required: dxvk-nvapi needs DXVK's d3d11 extension points, "
        "and without it NGX Core fails its platform check (0xBAD00002)")
    assert "dxgi=n,b" in DLL_OVERRIDES
    assert "nvapi64=n,b" in DLL_OVERRIDES
    assert DLL_OVERRIDES.endswith("nvngx_dlssnr=n")


def test_python_constant_is_usable_as_a_wine_override():
    """Each entry is dll=n,b and there are no stray spaces."""
    parts = DLL_OVERRIDES.split(";")
    assert parts, "empty override string"
    for part in parts:
        assert re.fullmatch(r"[A-Za-z0-9_.-]+=[a-z](,[a-z])*", part), (
            f"{part!r} is not a valid WINEDLLOVERRIDES entry")


@pytest.mark.parametrize("name,text", _sources() or [("(none)", "")])
def test_shell_scripts_use_the_same_overrides(name, text):
    """Every shell script that launches the worker carries the same string."""
    if not text:
        pytest.skip("no shell scripts found")
    assert DLL_OVERRIDES in text, (
        f"{name} does not contain the canonical WINEDLLOVERRIDES.\n"
        f"  expected: {DLL_OVERRIDES}\n"
        "  update it, or minimal/worker.py if the canonical value moved")


def test_python_module_sets_it():
    """minimal.worker must actually export the values it declares."""
    from minimal.worker import worker_env
    env = worker_env({})
    assert env["WINEDLLOVERRIDES"] == DLL_OVERRIDES
    assert env["DXVK_ENABLE_NVAPI"] == ENABLE_NVAPI


def test_ns_override_wins():
    """An explicit NS_WINEDLLOVERRIDES still takes precedence (escape hatch)."""
    from minimal.worker import worker_env
    env = worker_env({"NS_WINEDLLOVERRIDES": "d3d12=n"})
    assert env["WINEDLLOVERRIDES"] == "d3d12=n"


def test_enable_nvapi_is_set_everywhere():
    """DXVK_ENABLE_NVAPI=1 in Python and in every shell script."""
    assert ENABLE_NVAPI == "1"
    for name, text in _sources():
        assert "DXVK_ENABLE_NVAPI" in text, (
            f"{name} does not set DXVK_ENABLE_NVAPI — without it dxvk-nvapi "
            "leaves the NGX/DLSS part of NVAPI off and NGX Core cannot "
            "establish the platform (0xBAD00002)")