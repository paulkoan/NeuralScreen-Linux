"""Which code a run is running: the stamp, the apply script, and the line that says so.

A run was reported from a stale binary and nothing in its output could have said so. The
apply failed (`error: src/serve.cpp: already exists in working directory`), so the build
script was not there to run, so the pipeline started the previous build — and the console
showed a run of code that existed in no checkout. These tests are about the three things
that now make that impossible to miss: the binary carries what it was built from, the
checkout records which patch was applied, and a run prints both next to its own commit.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PORT = ROOT / "experiments" / "opendlss_port"
PATCH = PORT / "linux-port.patch"
APPLY = PORT / "apply_to_port.sh"

from minimal.version import patch_id, repo_state, verdict, version_lines, worker_stamp  # noqa: E402

STAMP = "port 9d08f41 (8 modified) patch {}\n"
GOOD = "e17393354d6ef17415a6072d7875e8a49472189b"   # a made-up id, for parsing
# The id this checkout's patch actually carries: read it rather than pinning it, or
# every re-cut of the patch breaks tests that are not about the patch.
REAL = patch_id(PATCH)


def fake_worker(tmp_path: Path, body: str, name: str = "dlss5vk") -> Path:
    """An executable that answers `stamp` the way the real binary does."""
    binary = tmp_path / name
    binary.write_text(body)
    binary.chmod(0o755)
    return binary


def test_the_binary_says_what_it_was_built_from(tmp_path):
    binary = fake_worker(tmp_path, f'#!/bin/sh\necho "{STAMP.format(GOOD).strip()}"\n')
    stamp = worker_stamp([str(binary)])
    assert stamp == {"line": STAMP.format(GOOD).strip(), "port": "9d08f41",
                     "modified": 8, "patch": GOOD}


def test_a_binary_built_without_a_patch_id_says_so(tmp_path):
    """`unset` is what build_linux.sh writes when .ns-patch-id is not there — a binary
    built from sources nobody can name, which is a different thing from in sync."""
    binary = fake_worker(tmp_path, '#!/bin/sh\necho "port abc1234 (3 modified) patch unset"\n')
    assert worker_stamp([str(binary)])["patch"] == "unset"
    assert verdict(worker_stamp([str(binary)]), GOOD).startswith("unknown")


def test_a_launcher_is_not_asked_for_a_stamp():
    """`bash native/run_worker.sh` is the Wine worker: it has no stamp, and asking a
    shell for one is how a version check turns into noise on every run."""
    assert worker_stamp(["bash", "native/run_worker.sh"]) is None
    assert worker_stamp(["/nonexistent/dlss5vk"]) is None
    assert worker_stamp([]) is None
    assert verdict(None, GOOD).startswith("unknown")


def test_an_out_of_sync_binary_is_named_not_implied(tmp_path):
    """The whole point: the reader is told, in words, that the run is not this code."""
    binary = fake_worker(tmp_path, '#!/bin/sh\necho "port 9d08f41 (8 modified) patch aaaa111122223333444455556666777788889999"\n')
    lines = version_lines([str(binary)])
    assert len(lines) == 2, "an out-of-sync run gets a second line rather than a suffix"
    assert "OUT OF SYNC" in lines[1]
    assert "aaaa11112222" in lines[1] and REAL[:12] in lines[1]


def test_in_sync_is_said_plainly(tmp_path, monkeypatch):
    """And the happy path stays one line: a check nobody reads is not a check."""
    import minimal.version as version

    binary = fake_worker(tmp_path, f'#!/bin/sh\necho "port 9d08f41 (8 modified) patch {REAL}"\n')
    monkeypatch.setattr(version, "PATCH", PATCH)          # the real patch, the real id
    monkeypatch.setattr(version, "REPO", ROOT)
    lines = version_lines([str(binary)])
    assert len(lines) == 1
    assert "in sync" in lines[0]
    assert REAL[:12] in lines[0]
    assert repo_state(ROOT) is not None


def test_the_patch_the_checkout_carries_has_an_id():
    """The comparison is only meaningful because the patch file identifies its commit."""
    assert re.fullmatch(r"[0-9a-f]{40}", patch_id(PATCH) or "")
    assert patch_id(Path("/nonexistent")) is None


# --- the apply script: the step that failed --------------------------------------

def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_the_apply_script_finds_every_file_the_patch_adds():
    """It derives the list from the patch, because the hand-written step missed one.

    The step that was supposed to clear the way named `scripts/build_linux.sh` and not
    `src/serve.cpp`, so the apply stopped on the file it had missed. Whatever the patch
    adds has to be in this list, and this is the check that the two agree.
    """
    expected = set(re.findall(r"^diff --git a/(\S+) b/\S+\nnew file mode", PATCH.read_text(), re.M))
    assert expected, "the patch adds no files, so the guard proves nothing"
    awk = (r'/^diff --git /{line=$0; sub(/^.* b\//, "", line); f=line} '
           r'/^new file mode/{print f}')
    got = subprocess.run(["awk", awk, str(PATCH)], capture_output=True, text=True)
    assert set(got.stdout.split()) == expected


def test_applying_the_patch_twice_works(tmp_path):
    """The regression test for the afternoon: apply, apply again, and it must be clean.

    A checkout that already has the patch's added files is the normal state after one
    apply — and it is exactly what made `git apply` refuse.
    """
    author = ["-c", "user.email=a@b", "-c", "user.name=a"]
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init", "-q")
    (source / "README").write_text("base\n")
    git(source, "add", ".")
    git(source, *author, "commit", "-qm", "base")
    (source / "scripts").mkdir()
    (source / "scripts" / "build_linux.sh").write_text("#!/usr/bin/env bash\necho built\n")
    (source / "src").mkdir()
    (source / "src" / "serve.cpp").write_text("// the mode that failed to apply\n")
    git(source, "add", ".")
    git(source, *author, "commit", "-qm", "the port")
    patch = tmp_path / "port.patch"
    patch.write_bytes(subprocess.run(["git", "-C", str(source), "format-patch", "-1", "--stdout"],
                                     capture_output=True).stdout)
    port_id = git(source, "rev-parse", "HEAD").strip()

    port = tmp_path / "port"
    port.mkdir()
    git(port, "init", "-q")
    (port / "README").write_text("base\n")
    git(port, "add", ".")
    git(port, *author, "commit", "-qm", "base")

    for attempt in (1, 2):
        result = subprocess.run(["bash", str(APPLY), str(port), str(patch)],
                                capture_output=True, text=True)
        assert result.returncode == 0, f"attempt {attempt} failed: {result.stderr}"

    assert (port / "src" / "serve.cpp").exists()
    assert (port / "scripts" / "build_linux.sh").exists()
    assert (port / ".ns-patch-id").read_text().strip() == port_id, (
        "the checkout has to record which patch it carries, or a run cannot say")
    assert "removed" in result.stdout, "the second run should say what it cleared"