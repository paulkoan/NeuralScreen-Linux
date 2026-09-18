"""The experiments' reporting tail, and their environment.

Two things are shared between `mmap_bridge/run.sh` and `d3d12_sync/run.sh` and
would otherwise drift apart copy by copy:

  * the push, including the auth dance, which explains a "wrong credentials"
    failure as a missing terminal rather than a GitHub problem;
  * the Wine environment, which has to come from `minimal/worker.py` or the
    probe measures a different D3D12 stack than the worker.

The push is tested against a local bare repository rather than GitHub, so it is
deterministic and both branches — landed, and failed-with-the-commit-safe — can be
checked without a network or a credential.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
EXPERIMENTS = REPO / "experiments"
REPORT_SH = EXPERIMENTS / "lib" / "report.sh"


def run(argv, **kw):
    return subprocess.run(argv, capture_output=True, text=True, **kw)


def git_env() -> dict:
    """A git identity that does not depend on the machine's config."""
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
    })
    return env


# --- the shared file itself -------------------------------------------------

def test_both_runners_use_the_shared_reporting_tail():
    """A second copy of the push logic is how the two explanations drift apart."""
    for runner in (EXPERIMENTS / "mmap_bridge" / "run.sh",
                   EXPERIMENTS / "d3d12_sync" / "run.sh"):
        text = runner.read_text()
        assert "lib/report.sh" in text, f"{runner} does not source the shared tail"
        assert "push_report" in text, f"{runner} does not call push_report"
        # And it must not have grown its own copy back.
        assert "GIT_ASKPASS=" not in text, (
            f"{runner} sets GIT_ASKPASS itself again — that belongs in report.sh")
        assert "git push origin HEAD" not in text, (
            f"{runner} pushes by hand instead of calling push_report")


def test_the_shared_tail_is_valid_bash():
    r = run(["bash", "-n", str(REPORT_SH)])
    assert r.returncode == 0, r.stderr


# --- the environment --------------------------------------------------------

def test_the_runner_also_times_the_workers_own_loop():
    """The substrate probe says the GPU layer is cheap, so the 55ms has to be
    somebody's; the worker's own --test rate is what tells whose, and the project
    had never recorded it. The rate must be derived, not left to the reader."""
    runner = (EXPERIMENTS / "d3d12_sync" / "run.sh").read_text()
    assert "nvngx.dll" in runner and "--test" in runner, (
        "the runner must time the worker's own loop, not just the substrate")
    assert "ms/evaluate" in runner, (
        "the ms/evaluate derivation has to be in the tool")
    assert "host_test.log" in runner, "and its output has to be kept"


def test_the_probe_runs_in_the_workers_own_environment():
    """The overrides must come from minimal/worker.py, not a second copy here."""
    sync = EXPERIMENTS / "d3d12_sync"
    runner = (sync / "run.sh").read_text()
    assert "wine_env.py" in runner, "the runner must go through wine_env.py"

    helper = (sync / "wine_env.py").read_text()
    assert "worker_env" in helper and "minimal.worker" in helper, (
        "wine_env.py must import worker_env rather than restate the variables")

    # The giveaway that a copy has appeared: the override string itself.
    for path in sync.rglob("*"):
        if path.is_file() and path.suffix in (".py", ".sh", ".cpp"):
            assert "d3d12=n,b" not in path.read_text(errors="replace"), (
                f"{path.name} hardcodes the DLL overrides — those live in "
                f"minimal/worker.py and a second copy will drift")


def test_wine_env_reports_the_environment_it_would_use():
    r = run([sys.executable, str(EXPERIMENTS / "d3d12_sync" / "wine_env.py"),
             "--show"], cwd=REPO)
    assert r.returncode == 0, r.stderr
    assert "WINEDLLOVERRIDES=" in r.stdout
    # The prefix is derived from the user's home, never hardcoded to someone's.
    assert "WINEPREFIX=" in r.stdout


# --- the push, against a local origin --------------------------------------

def _make_work_tree(tmp_path: Path, origin_url: str) -> Path:
    """A throwaway clone-shaped repo, carrying experiments/lib/report.sh."""
    work = tmp_path / "work"
    work.mkdir()
    assert run(["git", "init", "-q", str(work)]).returncode == 0
    (work / "seed.txt").write_text("seed\n")
    run(["git", "-C", str(work), "add", "."], env=git_env())
    run(["git", "-C", str(work), "commit", "-q", "-m", "seed"], env=git_env())
    run(["git", "-C", str(work), "remote", "add", "origin", origin_url],
        env=git_env())

    libdir = work / "experiments" / "lib"
    libdir.mkdir(parents=True)
    shutil.copy(REPORT_SH, libdir / "report.sh")

    driver = libdir / "driver.sh"
    driver.write_text('#!/usr/bin/env bash\n'
                      'set -euo pipefail\n'
                      '. "$(dirname "$0")/report.sh"\n'
                      'push_report "$1" "$2" "${3:-}"\n')
    return work


def test_push_report_commits_and_pushes(tmp_path):
    origin = tmp_path / "origin.git"
    assert run(["git", "init", "--bare", "-q", str(origin)]).returncode == 0

    work = _make_work_tree(tmp_path, str(origin))
    out = work / "test-results" / "20260101T000000Z-fake"
    out.mkdir(parents=True)
    (out / "report.md").write_text("**RESULT: PASS — fake**\n")

    env = git_env()
    env.pop("NS_GIT_ASKPASS", None)
    env["HOME"] = str(tmp_path / "no-such-home")     # no askpass script there
    r = run(["bash", str(work / "experiments/lib/driver.sh"),
             str(out), "fake result subject", "a body line"], cwd=work, env=env)

    assert "auth: no askpass script" in r.stdout, (
        "a missing askpass must be named, not left to read as a GitHub problem")
    assert "committed: fake result subject" in r.stdout
    assert "pushed " in r.stdout, r.stdout + r.stderr

    # Landed at the origin, and the body survived.
    subject = run(["git", "-C", str(origin), "log", "-1", "--format=%s", "HEAD"],
                  env=git_env())
    body = run(["git", "-C", str(origin), "log", "-1", "--format=%b", "HEAD"],
               env=git_env())
    assert subject.stdout.strip() == "fake result subject"
    assert "a body line" in body.stdout


def test_push_report_keeps_the_commit_local_when_the_push_fails(tmp_path):
    """The failure has to be stated, and the commit has to survive it."""
    work = _make_work_tree(tmp_path, str(tmp_path / "no-such-remote.git"))
    out = work / "test-results" / "20260101T000001Z-fake"
    out.mkdir(parents=True)
    (out / "report.md").write_text("**RESULT: FAIL — fake**\n")

    env = git_env()
    env["HOME"] = str(tmp_path / "no-such-home")
    r = run(["bash", str(work / "experiments/lib/driver.sh"),
             str(out), "fake failing subject"], cwd=work, env=env)

    assert "push FAILED" in r.stderr + r.stdout
    assert "safe locally" in r.stderr + r.stdout

    subject = run(["git", "-C", str(work), "log", "-1", "--format=%s"],
                  env=git_env())
    assert subject.stdout.strip() == "fake failing subject", (
        "the commit must still exist locally after a failed push")


def test_the_experiment_runners_are_executable():
    for runner in (EXPERIMENTS / "mmap_bridge" / "run.sh",
                   EXPERIMENTS / "d3d12_sync" / "run.sh"):
        assert runner.stat().st_mode & 0o111, f"{runner} needs its exec bit"