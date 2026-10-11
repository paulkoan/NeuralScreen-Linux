"""Which code a run is actually running, said out loud at the start of it.

This exists because a run was reported from a *stale binary* and nothing in the output
said so: an apply failed (`error: src/serve.cpp: already exists in working directory`),
the build script was consequently not there to run, and the pipeline went on to start the
previous build of the port. The console showed a run of code that no longer existed in
any checkout, and the only way to find out was to guess from the shape of the timings.

So the port bakes what it was built from into the binary (`dlss5vk stamp`, and the same
line logged by serve on startup), the checkout records which patch was applied to it
(`.ns-patch-id`, written by experiments/opendlss_port/apply_to_port.sh), and this module
puts the two next to the commit of this repository — so "we are in sync" is a statement
about the artifacts rather than about anyone's memory of which commands ran.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "experiments" / "opendlss_port" / "linux-port.patch"

# Interpreters and launchers are not the thing being run: `bash run_worker.sh` is the
# Wine worker, which has no stamp to give, and asking a shell for one would be nonsense.
_NOT_THE_BINARY = {"bash", "sh", "dash", "zsh", "fish", "env", "wine", "wine64",
                   "python", "python3", "uv", "sudo"}


def _run(args: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None


def repo_state(repo: Path = REPO) -> tuple[str, int] | None:
    """(short HEAD, number of uncommitted files) for this checkout, or None."""
    head = _run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"])
    if head is None or head.returncode != 0:
        return None
    status = _run(["git", "-C", str(repo), "status", "--porcelain"])
    dirty = len([line for line in (status.stdout if status else "").splitlines() if line.strip()])
    return head.stdout.strip(), dirty


def patch_id(path: Path = PATCH) -> str | None:
    """The commit this checkout's port patch was cut from, from its own 'From' header."""
    try:
        text = path.read_text()
    except OSError:
        return None
    match = re.search(r"^From ([0-9a-f]{40}) ", text, re.MULTILINE)
    return match.group(1) if match else None


def worker_stamp(cmd: list[str] | None) -> dict | None:
    """Ask the worker binary what it was built from, if it is the kind that knows.

    Returns {'port', 'modified', 'patch', 'line'}, or None for anything that is not a
    stamped native binary — the Wine worker, a launcher script, a missing file.
    """
    if not cmd:
        return None
    binary = Path(cmd[0])
    if binary.name in _NOT_THE_BINARY or not binary.is_file() or not os.access(binary, os.X_OK):
        return None
    result = _run([str(binary), "stamp"])
    if result is None or result.returncode != 0:
        return None
    line = result.stdout.strip()
    match = re.match(r"port (\S+) \((\d+) modified\) patch (\S+)", line)
    if not match:
        return None
    return {"line": line, "port": match.group(1), "modified": int(match.group(2)),
            "patch": match.group(3)}


def verdict(stamp: dict | None, expected: str | None) -> str:
    """Is the binary the one this checkout's patch should have produced?"""
    if stamp is None:
        return "unknown — the worker reports no stamp (not the native mode, or not rebuilt)"
    if stamp["patch"] == "unset":
        return ("unknown — the binary was built without a patch id: apply the patch with "
                "experiments/opendlss_port/apply_to_port.sh and rebuild")
    if not expected:
        return "unknown — this checkout has no patch id in linux-port.patch"
    if stamp["patch"][:12] == expected[:12]:
        return "in sync"
    return (f"OUT OF SYNC — the worker was built from patch {stamp['patch'][:12]}, this "
            f"checkout has {expected[:12]}: re-apply the patch and rebuild, the run below "
            f"is not the code in this checkout")


def version_lines(worker_cmd: list[str] | None, repo: Path = REPO,
                  patch_path: Path = PATCH) -> list[str]:
    """The line(s) to print at the start of a run, and after it."""
    where = repo_state(repo)
    expected = patch_id(patch_path)
    stamp = worker_stamp(worker_cmd)
    parts = []
    parts.append(f"repo {where[0]} ({'clean' if where[1] == 0 else f'+{where[1]} uncommitted'})"
                 if where else "repo unknown")
    if stamp:
        parts.append(f"worker built from patch {stamp['patch'][:12]} at port {stamp['port']}")
    else:
        parts.append("worker reports no stamp")
    parts.append(verdict(stamp, expected))
    line = "version: " + " · ".join(parts)
    # An out-of-sync run gets its own line: it is the answer to "why is the output not
    # what the sources say", and burying it at the end of a long line hides it.
    if verdict(stamp, expected).startswith("OUT OF SYNC"):
        return [line, "version: " + verdict(stamp, expected)]
    return [line]
