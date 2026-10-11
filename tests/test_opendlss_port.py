"""The Linux port of OpenDLSS-NR: patch and build script, checked as artifacts.

These are not our sources — they are a patch against an MIT project and a build
script — so what is worth testing is the set of things that, if they silently
changed, would cost someone an afternoon on the GPU box.
"""
import os
import re
import shutil
import subprocess
import tempfile
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


def test_the_ptx_list_covers_what_upstream_emits_and_notices_when_it_does_not():
    """The costliest bug in this port, and the build said nothing about it.

    The emitter invocations are a hand copy of scripts/build_shaders.ps1's, and an
    earlier version was copied from a partial read of that file: it stopped two loops
    early, so 12 of the 78 kernels were never generated. Nothing failed at build time
    — the host resolves kernel files by name when a dispatch is first reached — and it
    surfaced on the GPU box as

        error: cannot read PTX kernel ./build/shaders/../ptx/block32_e4m3_f74.ptx

    which names the missing file and not the script that should have written it. So
    both groups are asserted here, and so is the script's own check on the count.
    """
    text = SCRIPT.read_text()
    assert "block32_e4m3.py" in text and "for f in 2 66 74 130 48" in text, (
        "the fused 32-channel block family (f2/66/74/130/48) is required")
    assert "gemmv_e4m3_K$1_f$2_s1_m96.ptx" in text, "the split-512 GEMMs are required"
    assert '"512 4" "512 5" "512 13" "256 5" "4096 5" "1024 8" "1024 5"' in text, (
        "and the shapes they are generated for")

    assert "EXPECTED_PTX=78" in text, (
        "78 is what build_shaders.ps1 emits; the count is what catches a list that "
        "stops early")
    guard = text[text.index("EXPECTED_PTX"):]
    assert "exit 1" in guard, "a short PTX set has to fail the build, not just print"


def test_the_readme_keeps_its_evidence():
    """The claims that matter are the measured ones; the README is where they live
    for whoever picks this up next."""
    readme = (PORT / "README.md").read_text()
    assert "13/13" in readme and "78" in readme, "the verified build counts"
    assert "VK_ERROR_INCOMPATIBLE_DRIVER" in readme, (
        "the boundary: it builds here, it needs a GPU to run")
    assert "GL_EXT_float_e4m3" in readme, (
        "the glslang version constraint, which a distro glslang can fail on")
    assert "vkBasalt" in readme, "the implicit layer that would poison a measurement"


def test_the_apply_script_exists_and_is_the_documented_route():
    """A hand-typed `git apply` failed once and the run continued on an older binary.

    The script is idempotent, so the failure is not available any more — but only if it
    is what the README tells people to run, and only if it parses.
    """
    script = PORT / "apply_to_port.sh"
    assert script.exists(), "the port has to be applied by something repeatable"
    assert os.access(script, os.X_OK), "it should be runnable, not just present"
    subprocess.run(["bash", "-n", str(script)], check=True)

    readme = (PORT / "README.md").read_text()
    assert "apply_to_port.sh" in readme, "the README is where the workflow lives"
    assert "git apply /path/to/linux-port.patch" not in readme, (
        "the hand-typed apply is what failed; it should not still be the documented route")
    assert "dlss5vk stamp" in readme, "and the binary has to say what it was built from"


def test_the_stamp_reaches_the_binary_and_the_mode_reports_it():
    """`stamp` is a mode, the build writes the header it includes, and serve logs it."""
    patch = PATCH.read_text()
    assert "DLSS5VK_PATCH_ID" in patch, "the build has to bake the patch id in"
    assert "runStamp" in patch and 'strcmp(argv[1], "stamp")' in patch, (
        "a stamp nothing can ask for is not a check")
    assert "buildStamp()" in patch and "stamp.h" in patch


def test_the_composite_is_a_shader_and_the_mode_uses_it():
    """The frame's composite, on the GPU, and the plumbing that makes that reachable.

    The host spelling of it was ~130ms a frame at 1440p (11M pixels of fma, floor and
    half-truncation) and it forced the head's 60MB of f32 through the readback instead of
    the finished 14.7MB image. Three things have to stay true for it to be reachable:
    the shader is in the patch, the module list loads it, and the mode calls it.
    """
    patch = PATCH.read_text()
    assert "diff --git a/shaders/composite_serve.comp" in patch, "the shader is gone"
    assert '"gemm_reduce", "composite_serve"' in patch, (
        "Kernels loads a fixed module list; a shader missing from it cannot be dispatched")
    assert "compositeToRgba8" in patch
    assert "kernels->compositeToRgba8(" in patch, "the mode does not call it"


def test_the_composite_shader_compiles():
    """It is a shader: a stray type is a build failure, and this is where that shows.

    The first version of it shifted a `vec3` of uints — `vec3(toByte(..))` converts to
    float — and glslang refused it. The build compiles shaders/*.comp, so the port's own
    build catches it, but only on a machine that has glslang and the patch applied.
    """
    glslang = (os.environ.get("GLSLANG") or shutil.which("glslang")
               or shutil.which("glslangValidator"))
    if glslang is None:
        pytest.skip("no glslang here to compile the shader with")
    import re

    patch = PATCH.read_text()
    start = patch.index("diff --git a/shaders/composite_serve.comp")
    body = patch[start:]
    following = body.find("\ndiff --git ", 10)
    diff = body if following < 0 else body[:following]
    source = "".join(line[1:] + "\n" for line in diff.splitlines() if line.startswith("+")
                     and not line.startswith("+++"))
    assert source.startswith("#version 460"), source[:40]

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "composite_serve.comp"
        path.write_text(source)
        result = subprocess.run([glslang, "-V", "--target-env", "vulkan1.3", str(path),
                                 "-o", str(Path(tmp) / "out.spv")],
                                capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
