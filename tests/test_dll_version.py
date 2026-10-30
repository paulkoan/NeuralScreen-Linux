"""The version reader must agree with the binary, because a swapped DLL is a measurement input.

`2.1ms against 3.8ms` says nothing unless the next reader can tell which binary produced which
number. The bundled runtime's values are already established by the 310.8.16.0 investigation
(t_057cec57 / t_a31be3eb): 165,840,496 bytes, sha256 dcc0dc24..., file version 310.8.0.0. This
pins the reader against exactly that artifact, so a copy that is truncated or has been replaced
is visible before it is measured.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "dll_version.py"
BUNDLED = REPO / "native" / "nvngx_dlssnr.dll"

DOCUMENTED_SHA = "dcc0dc2414aedec4a8e084647070383be068554042587180c20c784d4772d36f"
DOCUMENTED_BYTES = 165_840_496
DOCUMENTED_VERSION = "310.8.0.0"


def run(path):
    return subprocess.run([sys.executable, str(TOOL), str(path)],
                          capture_output=True, text=True)


def test_it_reads_the_bundled_runtime():
    if not BUNDLED.is_file():
        import pytest
        pytest.skip("the bundled nvngx_dlssnr.dll is not present in this checkout")
    done = run(BUNDLED)
    assert done.returncode == 0, done.stderr
    assert f"sha256  {DOCUMENTED_SHA}" in done.stdout
    assert f"bytes   {DOCUMENTED_BYTES:,}" in done.stdout
    assert f"version {DOCUMENTED_VERSION}" in done.stdout, (
        "the bundled runtime is 310.8.0.0 - if this changed, either the DLL was replaced or "
        "the reader is wrong, and both invalidate every number compared against it")


def test_a_file_without_a_version_resource_is_refused(tmp_path):
    fake = tmp_path / "not-a-dll.dll"
    fake.write_bytes(b"MZ" + b"\0" * 512)
    done = run(fake)
    assert done.returncode == 2
    assert "version" in (done.stdout + done.stderr).lower()


def test_a_missing_file_is_refused(tmp_path):
    done = run(tmp_path / "nope.dll")
    assert done.returncode == 2