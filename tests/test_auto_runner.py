"""The auto-runner's guardrails, against a real git remote and fake entries.

The runner executes whatever the policy names, on a machine with the GPU. These tests are
about the things that must stay true no matter what a run request says: that an entry the
policy does not name is refused and never executed, that arguments are arguments and never
a shell, that a request runs once, and that a refusal is written down and pushed rather than
swallowed. There is no GPU here and none is needed: the entries are stubs.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "tools" / "auto_runner.py"

OK_STUB = """\
import pathlib, sys
pathlib.Path("ran.txt").write_text(" ".join(sys.argv[1:]))
pathlib.Path("before.png").write_bytes(b"PNG from the stub")
print("the stub ran")
"""

BOOM_STUB = """\
import sys
print("about to fail")
sys.exit(3)
"""


def git(*args: str, cwd: Path | None = None, check: bool = True):
    return subprocess.run(["git", *args], cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, check=check)


def commit(cwd: Path, message: str) -> None:
    git("-c", "user.name=seed", "-c", "user.email=seed@example.invalid", "add", "-A", cwd=cwd)
    git("-c", "user.name=seed", "-c", "user.email=seed@example.invalid", "commit", "-m", message,
        cwd=cwd)


class World:
    def __init__(self, root: Path):
        self.root = root
        self.remote = root / "remote.git"
        self.seed = root / "seed"
        self.worktree = root / "runner-clone"
        self.policy = root / "policy.toml"
        self.pause = root / "PAUSE"

    def queue(self, request: dict) -> str:
        """Queue a request the way the loop does: commit it to main and push."""
        (self.seed / "runs" / "queue" / f"{request['id']}.json").write_text(
            json.dumps(request, indent=2))
        commit(self.seed, f"queue {request['id']}")
        git("push", "origin", "HEAD:main", cwd=self.seed)
        return request["id"]

    def run(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(RUNNER), "--policy", str(self.policy), "--once", *extra],
            capture_output=True, text=True)

    def done_dir(self, run_id: str) -> Path:
        return self.worktree / "runs" / "done" / run_id

    def results_tree(self) -> str:
        return git("ls-tree", "-r", "--name-only", "results",
                   cwd=self.remote, check=False).stdout

    def log(self) -> str:
        return git("log", "--oneline", "results", cwd=self.remote, check=False).stdout


@pytest.fixture
def world(tmp_path: Path) -> World:
    w = World(tmp_path)
    git("init", "--bare", str(w.remote))
    git("clone", str(w.remote), str(w.seed))
    (w.seed / "runs" / "queue").mkdir(parents=True)
    (w.seed / "runs" / "queue" / ".gitkeep").write_text("")
    (w.seed / "stubs").mkdir()
    (w.seed / "stubs" / "ok.py").write_text(OK_STUB)
    (w.seed / "stubs" / "boom.py").write_text(BOOM_STUB)
    commit(w.seed, "seed the queue")
    git("push", "origin", "HEAD:main", cwd=w.seed)
    w.policy.write_text(f"""
repo_url = "{w.remote}"
worktree = "{w.worktree}"
request_branch = "main"
results_branch = "results"
max_timeout_s = 60
default_timeout_s = 20
pause_file = "{w.pause}"
container = false

[[entry]]
name = "ok"
argv = ["{sys.executable}", "stubs/ok.py"]

[[entry]]
name = "boom"
argv = ["{sys.executable}", "stubs/boom.py"]
""")
    return w


def test_a_request_runs_and_lands_on_the_results_branch(world: World):
    run_id = world.queue({"id": "r001", "entry": "ok", "args": ["--frames", "60"],
                          "artifacts": ["before.png"], "note": "the happy path"})
    finished = world.run()
    assert finished.returncode == 0, finished.stderr

    done = world.done_dir(run_id)
    result = json.loads((done / "result.json").read_text())
    assert result["exit_code"] == 0, result
    assert result["argv"][-2:] == ["--frames", "60"], result["argv"]
    assert "the stub ran" in (done / "report.md").read_text()
    assert (done / "before.png").read_bytes() == b"PNG from the stub", "the artifact was not collected"
    assert (done / "request.json").exists(), "the request should be kept with its result"
    assert (world.worktree / "ran.txt").read_text() == "--frames 60"
    assert not (world.worktree / "runs" / "queue" / f"{run_id}.json").exists(), \
        "the request is still queued: it would run again"

    tree = world.results_tree()
    assert f"runs/done/{run_id}/report.md" in tree, tree
    assert f"runs/done/{run_id}/before.png" in tree, tree
    # The results branch is a snapshot of the tree the run happened on - the point of it is
    # that a result can be read next to the code that produced it - so the queue's own
    # .gitkeep is along for the ride. What must not be there is the request itself.
    assert f"runs/queue/{run_id}.json" not in tree, "the request was published with the result"
    assert world.log().strip(), "nothing was pushed"


def test_an_entry_the_policy_does_not_name_is_refused_and_never_runs(world: World):
    run_id = world.queue({"id": "r002", "entry": "root-shell", "args": ["-c", "touch pwned"]})
    finished = world.run()
    assert finished.returncode == 0, finished.stderr

    report = (world.done_dir(run_id) / "report.md").read_text()
    assert "Refused" in report, report
    assert "root-shell" in report
    assert json.loads((world.done_dir(run_id) / "result.json").read_text())["exit_code"] == 126
    assert not (world.worktree / "ran.txt").exists(), "the stub ran, so something executed"
    assert not list(world.root.rglob("pwned")), "the argument was interpreted somewhere"
    assert f"runs/done/{run_id}/report.md" in world.results_tree(), \
        "a refusal nobody can see is the failure mode worth engineering against"


def test_arguments_are_arguments_and_never_a_shell(world: World):
    """execve, not a shell: every one of these is a string that reaches the program."""
    hostile = ["$(touch pwned)", "; touch pwned2", "`touch pwned3`", "&& touch pwned4"]
    run_id = world.queue({"id": "r003", "entry": "ok", "args": hostile})
    assert world.run().returncode == 0

    assert (world.worktree / "ran.txt").read_text() == " ".join(hostile), \
        "the arguments did not arrive as arguments"
    assert not list(world.root.rglob("pwned*")), "something interpreted them after all"
    assert json.loads((world.done_dir(run_id) / "result.json").read_text())["exit_code"] == 0


def test_a_timeout_beyond_the_policy_is_refused(world: World):
    run_id = world.queue({"id": "r004", "entry": "ok", "timeout_s": 100000})
    assert world.run().returncode == 0
    report = (world.done_dir(run_id) / "report.md").read_text()
    assert "Refused" in report and "timeout" in report, report
    assert not (world.worktree / "ran.txt").exists()


def test_an_artifact_path_cannot_leave_the_repo(world: World):
    run_id = world.queue({"id": "r005", "entry": "ok", "artifacts": ["../../etc/passwd"]})
    assert world.run().returncode == 0
    assert "Refused" in (world.done_dir(run_id) / "report.md").read_text()
    assert not (world.done_dir(run_id) / "passwd").exists()


def test_a_failing_run_is_recorded_not_hidden(world: World):
    run_id = world.queue({"id": "r006", "entry": "boom"})
    assert world.run().returncode == 0, "a failing run is a result, not a runner failure"
    result = json.loads((world.done_dir(run_id) / "result.json").read_text())
    assert result["exit_code"] == 3, result
    report = (world.done_dir(run_id) / "report.md").read_text()
    assert "about to fail" in report and "exit **3**" in report
    assert f"runs/done/{run_id}/result.json" in world.results_tree()


def test_a_request_runs_once_even_though_the_checkout_is_reset(world: World):
    """The dedupe has to survive the reset, or every pass re-runs every request forever."""
    run_id = world.queue({"id": "r007", "entry": "ok"})
    assert world.run().returncode == 0
    first = (world.done_dir(run_id) / "result.json").read_text()
    history = world.log()

    second = world.run()
    assert second.returncode == 0
    assert "already on results, skipping" in second.stderr, second.stderr
    assert world.log() == history, "the second pass pushed something"
    assert (world.worktree / "ran.txt").read_text() == "", \
        "the stub ran again: the working tree is reset every pass, so the ledger has to be " \
        "the results branch"
    assert json.loads(first)["exit_code"] == 0


def test_the_pause_file_stops_everything(world: World):
    run_id = world.queue({"id": "r008", "entry": "ok"})
    world.pause.write_text("")
    finished = world.run()
    assert finished.returncode == 0
    assert "paused" in finished.stderr
    assert not (world.worktree / "ran.txt").exists(), "something ran while paused"
    assert f"runs/done/{run_id}" not in world.results_tree()


def test_a_missing_policy_is_a_clear_refusal(tmp_path: Path):
    finished = subprocess.run(
        [sys.executable, str(RUNNER), "--policy", str(tmp_path / "nope.toml"), "--once"],
        capture_output=True, text=True)
    assert finished.returncode != 0
    assert "no policy at" in finished.stderr


def test_the_example_policy_names_only_what_the_runner_may_run():
    """The shipped example is what people copy to /etc; it must not be a wildcard."""
    text = (REPO / "tools" / "runner_policy.example.toml").read_text()
    names = [line for line in text.splitlines() if line.startswith("name =")]
    assert len(names) >= 3, names
    for line in names:
        assert "bash -c" not in line and "/bin/sh" not in line, line
    assert "pause_file" in text and "results_branch" in text
    # No container by default: it needs a system package, and the user asked for nothing
    # outside /opt/neuralscreen. The policy should say so rather than leave it implied.
    assert "container = false" in text, "the default should need no system packages"
    assert "nvidia-container-toolkit" in text, "if the container is off, say what it would need"


def test_the_watcher_declares_every_flag_its_body_uses():
    """A cron tick caught this the honest way: `--verbose` was read but never declared.

    --help exits before the body runs, so asking it what it accepts is a cheap way to notice
    that a flag the code branches on was never added - which is otherwise only visible when
    the job fires, and the job is silent by design.
    """
    finished = subprocess.run([sys.executable, str(REPO / "tools" / "results_watch.py"), "--help"],
                              capture_output=True, text=True)
    assert finished.returncode == 0, finished.stderr
    source = (REPO / "tools" / "results_watch.py").read_text()
    for flag in ("--all", "--check", "--verbose", "--branch"):
        assert flag in source, flag
        assert flag in finished.stdout, f"{flag} is read but not declared:\n{finished.stdout}"


def test_the_runner_authenticates_with_a_key_and_never_a_token():
    """A deploy key scoped to one repository, held on the machine that uses it.

    A token in the policy would be a secret in a versioned file; an ssh key the runner
    generates for itself is neither, and can be revoked without touching anything else.
    """
    unit = (REPO / "tools" / "neuralscreen-runner.service").read_text()
    policy = (REPO / "tools" / "runner_policy.example.toml").read_text()
    assert "/opt/neuralscreen/deploy_key" in unit, "the unit must name the key"
    assert "/etc/" not in unit, "the user asked for nothing in /etc - keep it that way"
    assert "systemctl --user" in unit, "it is a user unit: no sudo anywhere"
    assert "/etc/" not in policy, "the policy points at /opt/neuralscreen, not /etc"
    assert "sudo" not in unit.split("[Service]")[1], "the service section must need no root"
    assert "IdentitiesOnly=yes" in unit, \
        "without IdentitiesOnly the service would try its own keys as well"
    assert "UserKnownHostsFile=" in unit
    # DNS has to be reachable or every fetch fails as "could not resolve host", which reads
    # like a credential problem and is not one.
    assert "IPAddressAllow=localhost" in unit, "the resolver must be allowed, or DNS is blocked"

    # Settings, not prose: this file talks about tokens on purpose, and a check that reads
    # the comments would fail the moment someone explains why there is no token.
    settings = [line for line in policy.splitlines()
                if line.strip() and not line.strip().startswith("#")]
    assert any(line.startswith("repo_url") and "git@github.com:" in line for line in settings), \
        "the policy should clone over ssh"
    assert not any("https://" in line for line in settings), \
        "an https remote needs a token; the key is the point"
    for pattern in ("github_pat_", "ghp_", "BEGIN OPENSSH PRIVATE KEY"):
        assert pattern not in policy, f"the policy carries what looks like a credential: {pattern}"
    for line in settings:
        lowered = line.lower()
        assert not any(word in lowered for word in ("token =", "password =", "secret =")), line


def test_a_git_failure_carries_gits_own_reason(world: World, tmp_path: Path):
    """The first real run failed with exit 128 and no explanation, because I threw git's
    stderr away. A clone that fails inside a systemd unit has to say why in the journal."""
    bad = tmp_path / "policy-bad.toml"
    bad.write_text(world.policy.read_text().replace(str(world.remote), str(tmp_path / "nope.git")))
    finished = subprocess.run([sys.executable, str(RUNNER), "--policy", str(bad), "--once"],
                              capture_output=True, text=True)
    assert finished.returncode != 0
    assert "could not clone" in finished.stderr, finished.stderr
    assert any(said in finished.stderr for said in
               ("does not exist", "does not appear to be a git repository",
                "Could not read from remote", "not a git repository")), finished.stderr


def test_the_unit_allows_what_name_resolution_needs():
    """AF_NETLINK and the resolver: without them DNS fails as a network outage."""
    unit = (REPO / "tools" / "neuralscreen-runner.service").read_text()
    assert "AF_NETLINK" in unit, "name resolution needs AF_NETLINK, or every fetch fails"
    assert "IPAddressAllow=localhost" in unit
    assert "GIT_TERMINAL_PROMPT=0" in unit, "a prompt under systemd can only hang"


def test_the_journal_says_which_runner_and_policy_are_running(world: World):
    """A stale install reads exactly like a broken remote, so it has to be visible."""
    world.queue({"id": "r009", "entry": "ok"})
    finished = world.run()
    assert finished.returncode == 0, finished.stderr
    stamps = [line for line in finished.stderr.splitlines() if line.startswith("[runner] runner ")]
    assert stamps, finished.stderr
    assert "policy " in stamps[0], stamps[0]
    assert "entry points: boom, ok" in stamps[0], stamps[0]
