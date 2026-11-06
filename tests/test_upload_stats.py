"""The stats upload must not say "uploaded" unless the remote has the file.

A run's log went missing while the terminal printed "stats: uploaded 20261106-223743.log". The
push had exited 0 having pushed nothing: the systemd runner shares that clone and does
`git checkout -f -B main origin/main` + `git reset --hard origin/main` every tick, so a commit made
a second earlier can be gone before the push.

These run the real script against a real bare remote — no mocks — because the failure was in the
interaction between git's refs and a second writer, and a mock of git cannot have that.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "tools" / "upload_stats.sh"


def _git(*args, cwd=None, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)


def _scratch(tmp_path: Path) -> tuple[Path, Path]:
    """A bare remote and a clone of it with one commit on main."""
    remote = tmp_path / "remote.git"
    _git("init", "--bare", "-b", "main", str(remote))
    work = tmp_path / "work"
    _git("clone", str(remote), str(work))
    _git("config", "user.email", "t@example.invalid", cwd=work)
    _git("config", "user.name", "Test", cwd=work)
    (work / "runs" / "local").mkdir(parents=True)
    (work / "runs" / "local" / ".gitkeep").write_text("")
    _git("add", "-A", cwd=work)
    _git("commit", "-q", "-m", "init", cwd=work)
    _git("push", "-q", "-u", "origin", "main", cwd=work)
    return remote, work


def _upload(work: Path, log: Path, status: int = 0):
    env = {"PATH": "/usr/bin:/bin", "HOME": str(work)}
    return subprocess.run(["bash", str(SCRIPT), str(work), str(log), str(status)],
                          capture_output=True, text=True, env=env)


def _remote_files(remote: Path) -> set[str]:
    out = _git("ls-tree", "-r", "--name-only", "main", cwd=remote)
    return set(out.stdout.split())


def _write_run(work: Path, name: str = "20261106-223743.log") -> Path:
    log = work / "runs" / "local" / name
    log.write_text("[perf] a run that happened\n")
    return log


def test_a_finished_run_lands_on_the_remote(tmp_path):
    remote, work = _scratch(tmp_path)
    log = _write_run(work)
    result = _upload(work, log)
    assert "NOT uploaded" not in result.stderr, result.stderr
    assert "uploaded" in result.stdout
    assert "runs/local/20261106-223743.log" in _remote_files(remote)


def test_the_claim_is_backed_by_the_remote_not_by_the_push(tmp_path):
    """The assertion the old script never made: ask the remote what it has."""
    remote, work = _scratch(tmp_path)
    log = _write_run(work)
    _upload(work, log)
    remote_head = _git("rev-parse", "main", cwd=remote).stdout.strip()
    local_head = _git("rev-parse", "HEAD", cwd=work).stdout.strip()
    assert remote_head == local_head


def test_a_commit_lost_to_the_runner_still_uploads(tmp_path):
    """The incident: committed, then the tree is reset before the push can run."""
    remote, work = _scratch(tmp_path)
    log = _write_run(work)
    _git("add", "-A", cwd=work)
    _git("commit", "-q", "-m", "stats: local run (doomed)", cwd=work)
    _git("reset", "--hard", "origin/main", cwd=work)      # what the runner's tick does
    log.write_text("[perf] a run that happened\n")        # the log survives on disk

    result = _upload(work, log)
    assert "uploaded" in result.stdout, result.stdout + result.stderr
    assert "runs/local/20261106-223743.log" in _remote_files(remote)


def test_a_second_upload_of_the_same_log_is_not_a_lie(tmp_path):
    """Re-running must not say "nothing new" as though it had verified anything."""
    remote, work = _scratch(tmp_path)
    log = _write_run(work)
    _upload(work, log)
    again = _upload(work, log)
    assert "uploaded" in again.stdout
    assert "runs/local/20261106-223743.log" in _remote_files(remote)


def test_an_unreachable_remote_is_reported_as_not_uploaded(tmp_path):
    """The whole point: a failed upload must not read as a success."""
    _, work = _scratch(tmp_path)
    log = _write_run(work)
    _git("remote", "set-url", "origin", str(tmp_path / "gone.git"), cwd=work)

    result = _upload(work, log)
    assert "NOT uploaded" in result.stderr, result.stdout + result.stderr
    assert "uploaded " not in result.stdout.replace("NOT uploaded", "")


def test_a_log_outside_the_repo_is_still_handled(tmp_path):
    """$LOG arrives absolute; the commit has to name a repo-relative path."""
    remote, work = _scratch(tmp_path)
    log = _write_run(work)
    assert log.is_absolute()
    _upload(work, log)
    assert "runs/local/" in _git("show", "--stat", "--format=", "HEAD", cwd=work).stdout


def test_the_status_reaches_the_commit_message(tmp_path):
    remote, work = _scratch(tmp_path)
    log = _write_run(work)
    _upload(work, log, status=139)
    message = _git("log", "-1", "--format=%s", cwd=work).stdout
    assert "exit 139" in message, message


def test_the_launcher_uses_the_tested_script():
    """A copy inside neuralscreen.sh is a copy that no test above covers."""
    source = (REPO / "neuralscreen.sh").read_text(encoding="utf-8")
    assert "tools/upload_stats.sh" in source
    assert "upload_stats() {" not in source, "the inline copy is back"
