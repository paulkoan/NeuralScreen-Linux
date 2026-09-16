"""Every file in tools/ is a command, and has to ship that way.

This exists because one did not. `tools/wayland_probe.py` was written, committed
and pushed without the executable bit, so the documented invocation

    tools/wayland_probe.py --save-frame /tmp/shot.png

failed with `Permission denied` — on the GPU box, where iterating is expensive.
The file was fine; git had recorded it as 100644.

Two checks, because the failure has two halves: the bit on disk, and the bit git
actually records. Fixing only the first leaves the file executable in one working
copy and nowhere else.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
TOOLS = REPO / "tools"

# Files in tools/ that are libraries rather than commands, and so are not
# expected to carry a shebang or the executable bit.
NOT_COMMANDS: set[str] = {
    # Imported by frame_diff.py and wayland_probe.py to re-exec themselves into
    # the repo venv. It has to be importable by the *system* interpreter, so it
    # uses nothing but the standard library.
    "venv_boot.py",
}


def _tool_files() -> list[Path]:
    return sorted(p for p in TOOLS.iterdir()
                  if p.is_file() and p.name not in NOT_COMMANDS)


def test_there_are_tools_to_check():
    """A guard so a moved directory cannot make every check below vacuous."""
    assert _tool_files(), f"no files found in {TOOLS}"


def test_wayland_probe_is_covered():
    """The specific file that was broken must be in the set being checked."""
    assert "wayland_probe.py" in [p.name for p in _tool_files()]


def test_every_tool_is_executable_on_disk():
    not_executable = [p.name for p in _tool_files() if not os.access(p, os.X_OK)]
    assert not not_executable, (
        f"not executable: {', '.join(not_executable)}\n"
        "  these are documented as `tools/<name> ...`; run chmod +x on them")


def test_every_tool_has_a_shebang():
    """The exec bit is meaningless without one."""
    missing = []
    for path in _tool_files():
        if path.suffix not in (".sh", ".py"):
            continue
        first = path.read_text(errors="replace").splitlines()[:1]
        if not first or not first[0].startswith("#!"):
            missing.append(path.name)
    assert not missing, f"no shebang: {', '.join(missing)}"


def test_git_records_the_executable_bit():
    """The bit git ships is the one in its index, not the one on your disk."""
    if shutil.which("git") is None or not (REPO / ".git").exists():
        pytest.skip("not a git checkout")
    proc = subprocess.run(["git", "ls-files", "-s", "tools/"], cwd=REPO,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        pytest.skip(f"git could not list tools/: {proc.stderr.strip()}")

    tracked = 0
    wrong = []
    for line in proc.stdout.splitlines():
        meta, _, name = line.partition("\t")
        parts = meta.split()
        if len(parts) < 3:
            continue
        mode, path = parts[0], name.strip()
        if Path(path).name in NOT_COMMANDS:
            continue
        tracked += 1
        if mode != "100755":
            wrong.append(f"{path} is {mode}")

    assert tracked, "git listed no files under tools/"
    assert not wrong, (
        "committed without the executable bit:\n  " + "\n  ".join(wrong) + "\n"
        "  chmod +x them and commit the mode change, or the next checkout "
        "gets Permission denied")


def test_a_python_tool_runs_by_its_documented_path():
    """`tools/*.py ...` — exactly as the docstrings and README say — must work.

    Two separate failures hid behind this one invocation:

      * wayland_probe.py was committed non-executable, so it was
        `Permission denied`;
      * the shebang picks up whatever `python3` is on PATH, which without the
        venv activated is the system interpreter — no numpy, no cv2, no jeepney
        — and the tools died with a traceback instead of doing their job.

    Neither is visible from pytest alone, which runs under the venv interpreter
    and imports modules rather than executing them.
    """
    # frame_diff.py with no arguments prints usage and exits 3; the probe with
    # --check-only reports on the environment without opening the portal, so
    # neither puts a dialog on anyone's screen.
    for tool, argv in (("wayland_probe.py", ["--check-only"]),
                       ("frame_diff.py", [])):
        proc = subprocess.run([str(TOOLS / tool), *argv],
                              capture_output=True, text=True, timeout=180)
        combined = proc.stdout + proc.stderr
        assert "Traceback" not in combined, (
            f"{tool} crashed instead of running:\n" + combined[-2000:])

    # The probe additionally has to reach a verdict, not just avoid crashing.
    proc = subprocess.run([str(TOOLS / "wayland_probe.py"), "--check-only"],
                          capture_output=True, text=True, timeout=180)
    assert "RESULT:" in proc.stdout, (
        "the probe did not reach a verdict:\n"
        + (proc.stdout + proc.stderr)[-2000:])