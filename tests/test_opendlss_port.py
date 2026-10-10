"""The Linux port of OpenDLSS-NR: patch and build script, checked as artifacts.

These are not our sources — they are a patch against an MIT project and a build
script — so what is worth testing is the set of things that, if they silently
changed, would cost someone an afternoon on the GPU box.
"""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PORT = ROOT / "experiments" / "opendlss_port"
SCRIPT = PORT / "build_linux.sh"
PATCH = PORT / "linux-port.patch"


def test_the_build_script_is_valid_shell():
    assert SCRIPT.exists(), "the build script is the deliverable"
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)


def test_the_beta_define_reaches_volk():
    """The port's only non-obvious trap.

    volk.h gates the VK_NV_cuda_kernel_launch entry points behind
    VK_ENABLE_BETA_EXTENSIONS. The Windows build compiles volk.c in the same cl
    invocation as src/, so it gets the define for free; a build script that
    compiles volk.c separately must pass it or the link fails with five undefined
    references — and nothing about that failure points at volk.
    """
    text = SCRIPT.read_text()
    volk_lines = [ln for ln in text.splitlines() if "volk.c" in ln and "-c" in ln]
    assert volk_lines, "no volk.c compile line found"
    joined = " ".join(volk_lines)
    assert "-DVK_ENABLE_BETA_EXTENSIONS" in joined, (
        "volk.c must be compiled with VK_ENABLE_BETA_EXTENSIONS, or the "
        "cuda-kernel-launch globals are never defined")


def test_the_script_fetches_the_pinned_deps_itself():
    """The failure this was written for, on the real box:

        cc1: fatal error: tools/volk/volk.c: No such file or directory

    which names the missing file and not the reason. fetch_tools.ps1 does that job on
    Windows, so a Linux build that assumes it has been run fails on a clean clone. The
    script has to fetch both deps at the same pins and say so when it cannot.
    """
    text = SCRIPT.read_text()
    assert "fetch_dep" in text, "it must fetch tools/ rather than depend on the docs"
    assert "v1.4.363" in text and "vulkan-sdk-1.4.357.0" in text, (
        "the tags must match fetch_tools.ps1, or the Linux build compiles against "
        "different Vulkan headers than the Windows one")
    assert "could not fetch" in text, "it must fail loudly, not reach the compiler"

    fetch_at = text.index("fetch_dep zeux/volk")
    compile_at = text.index("-c tools/volk/volk.c")
    assert fetch_at < compile_at, "fetching has to happen before the compile that needs it"


def test_the_shader_invocation_matches_upstreams():
    """Same flags as scripts/build_shaders.ps1, or the SPIR-V is not the same
    artifact the project tests against."""
    text = SCRIPT.read_text()
    assert "-V --target-env vulkan1.3" in text
    assert "-I" in text and "shaders" in text
    assert "scripts/ptx/" in text, "the PTX emitters are part of the build"


def test_the_patch_carries_the_four_fixes():
    """Each fix is here because MSVC accepted something gcc does not. Losing one
    silently breaks the Linux build, and the patch is the only record of why."""
    patch = PATCH.read_text()
    assert patch.startswith("From "), "expected a git format-patch"
    for marker, why in (
            ("static const Chain& emptyChain()",
             "the default argument that constructs a nested type with NSDMIs"),
            ("memcpy: MSVC pulls this in transitively",
             "the missing <cstring> includes"),
            ("scripts/build_linux.sh", "the build script itself")):
        assert marker in patch, f"the patch no longer carries {why}"

    # Two headers needed <cstring>, and a patch that only fixes one still fails.
    assert patch.count("memcpy: MSVC pulls this in transitively") == 2
    # A diff has to have at least one hunk per file it touches.
    assert patch.count("\n@@ ") >= 4


def test_the_readme_keeps_its_evidence():
    """The claims that matter are the measured ones; the README is where they live
    for whoever picks this up next."""
    readme = (PORT / "README.md").read_text()
    assert "13/13" in readme and "66" in readme, "the verified build counts"
    assert "VK_ERROR_INCOMPATIBLE_DRIVER" in readme, (
        "the boundary: it builds here, it needs a GPU to run")
    assert "GL_EXT_float_e4m3" in readme, (
        "the glslang version constraint, which a distro glslang can fail on")
    assert "vkBasalt" in readme, "the implicit layer that would poison a measurement"
