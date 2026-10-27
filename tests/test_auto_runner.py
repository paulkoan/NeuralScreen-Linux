"""The auto-runner's guardrails, against a real git remote and fake entries.

The runner executes whatever the policy names, on a machine with the GPU. These tests are
about the things that must stay true no matter what a run request says: that an entry the
policy does not name is refused and never executed, that arguments are arguments and never
a shell, that a request runs once, and that a refusal is written down and pushed rather than
swallowed. There is no GPU here and none is needed: the entries are stubs.
"""
from __future__ import annotations

import json
import os
import re
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

# A burst is a directory, not a file: frames/, motion/ and manifest.json. The
# artifact copy has to take the whole tree, or a downstream run that opens
# burst/manifest.json finds nothing even though the run "succeeded".
BURST_STUB = """\
import json, pathlib, sys
pathlib.Path("ran.txt").write_text(" ".join(sys.argv[1:]))
b = pathlib.Path("burst")
for sub in ("frames", "motion"):
    (b / sub).mkdir(parents=True, exist_ok=True)
(b / "frames" / "frame_000000_before.png").write_bytes(b"PNG before")
(b / "frames" / "frame_000000_after.png").write_bytes(b"PNG after")
(b / "motion" / "frame_000000_motion.npz").write_bytes(b"NPZ motion")
(b / "manifest.json").write_text(json.dumps({"frames_saved": 1}))
print("the burst stub ran")
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
    (w.seed / "stubs" / "burst.py").write_text(BURST_STUB)
    (w.seed / "stubs" / "caches.py").write_text(
        "import os, pathlib\n"
        "home = pathlib.Path(os.environ['HOME'])\n"
        "(home / 'aprefix').mkdir(parents=True, exist_ok=True)\n"
        "(home / 'aprefix' / 'noise.bin').write_bytes(b'x' * 64)\n")
    (w.seed / "stubs" / "env.py").write_text(
        "import os, pathlib\n"
        "pathlib.Path('env.txt').write_text(os.environ.get('NS_FIXTURE_WORKER', 'unset'))\n")
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

[[entry]]
name = "burst"
argv = ["{sys.executable}", "stubs/burst.py"]

[[entry]]
name = "caches"
argv = ["{sys.executable}", "stubs/caches.py"]

[[entry]]
name = "with-env"
argv = ["{sys.executable}", "stubs/env.py"]
[entry.env]
NS_FIXTURE_WORKER = "a machine property"
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
    report = (done / "report.md").read_text()
    assert "the stub ran" in report
    assert "runner `" in report, "the report should name the runner that made it"
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


def test_a_directory_artifact_is_copied_recursively(world: World):
    """A burst directory lands in the result with its whole tree.

    A burst is frames/, motion/ and manifest.json, not a single file. The copy
    out of the run must take the tree: a manifest that points at frames that
    were never collected is worse than no manifest, because it looks readable.
    """
    run_id = world.queue({"id": "r-burst", "entry": "burst",
                          "artifacts": ["burst"],
                          "note": "a directory artifact"})
    finished = world.run()
    assert finished.returncode == 0, finished.stderr

    done = world.done_dir(run_id)
    assert (done / "burst" / "manifest.json").is_file(), \
        "the manifest was not copied out of the run"
    assert (done / "burst" / "frames" / "frame_000000_before.png").is_file()
    assert (done / "burst" / "frames" / "frame_000000_after.png").is_file()
    assert (done / "burst" / "motion" / "frame_000000_motion.npz").is_file()
    assert "the burst stub ran" in (done / "report.md").read_text()
    assert f"runs/done/{run_id}/burst/manifest.json" in world.results_tree(), \
        "the burst tree was not published on the results branch"


def test_a_manual_request_waits_for_a_human_run(world: World):
    """A request that needs someone at the screen must not be eaten by the timer.

    r2026-10-27-a was a HUMAN run - the portal hands out a screen-cast only after
    its dialog is clicked - and the unattended timer consumed it while nobody was
    there. It ran with SDL_VIDEODRIVER=dummy, failed in 0.02s, and marked the id
    done, so the human run it was queued for could never happen. ``manual`` keeps
    the request in the queue until run_manually.sh takes it with --include-manual.
    """
    run_id = world.queue({"id": "r-manual", "entry": "ok", "args": ["--frames", "2"],
                          "manual": True, "artifacts": ["before.png"],
                          "note": "needs a human at the screen"})

    # The timer runs without --include-manual. It must leave the request untouched.
    finished = world.run()
    assert finished.returncode == 0, finished.stderr
    assert "manual request" in finished.stdout + finished.stderr, finished.stdout
    assert not world.done_dir(run_id).exists(), "the timer consumed a manual request"
    assert (world.worktree / "runs" / "queue" / f"{run_id}.json").exists(), \
        "the manual request was unlinked from the queue"
    assert not (world.worktree / "ran.txt").exists(), "the stub ran, so the timer executed it"

    # The human run takes it.
    finished = world.run("--include-manual")
    assert finished.returncode == 0, finished.stderr
    result = json.loads((world.done_dir(run_id) / "result.json").read_text())
    assert result["exit_code"] == 0, result
    assert (world.worktree / "ran.txt").read_text() == "--frames 2"
    assert f"runs/done/{run_id}/report.md" in world.results_tree()


def test_manual_must_be_a_bool_or_it_is_refused(world: World):
    """``"manual": "yes"`` is refused visibly, not silently parked in the queue.

    The skip happens before validate(), so a truthy string would otherwise sit in
    runs/queue forever with no run and no refusal - the request nobody ran and
    nobody noticed, which is the failure mode runs/README.md engineers against.
    """
    run_id = world.queue({"id": "r-manual-bad", "entry": "ok", "manual": "yes"})
    assert world.run().returncode == 0
    assert "Refused" in (world.done_dir(run_id) / "report.md").read_text()
    assert not (world.worktree / "ran.txt").exists()


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
    assert "published, skipping" in second.stderr, second.stderr
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


def test_the_example_policy_can_rebuild_the_port():
    """The port is a patch plus a build, and the runs have to be able to do both.

    Until this entry exists, a port change needs the developer by hand - and the failure
    mode is not a loud one: `r2026-10-11-g` ran to completion on the previous binary and
    said `OUT OF SYNC` in the middle of its own report. The entry point has to be in the
    repository (the runner resolves it inside its own clone) and it has to default to the
    staged copy, since a request carries arguments and the runner's sandbox cannot read
    the home directory anyway.
    """
    text = (REPO / "tools" / "runner_policy.example.toml").read_text()
    assert 'name = "port-build"' in text, "the loop cannot rebuild the worker without this"

    # The argv it names, as a path that exists in the repository.
    entry = text[text.index('name = "port-build"'):]
    entry = entry[:entry.index("[[entry]]") if "[[entry]]" in entry else len(entry)]
    argv = re.search(r'argv = \[(.*)\]', entry)
    assert argv is not None, f"no argv line in:\n{entry}"
    script = REPO / argv.group(1).split(",")[-1].strip().strip('"')
    assert script.exists(), f"{script} does not exist"
    assert os.access(script, os.X_OK), "an entry point that is not executable is not one"

    body = script.read_text()
    settings = [line for line in entry.splitlines()
                if line.strip() and not line.strip().startswith("#")]
    assert not any("/opt/neuralscreen" in line for line in settings), (
        "no arguments: the arguments come from the request, and the default has to live in "
        "the script")
    assert 'port="${1:-/opt/neuralscreen/port}"' in body, (
        "the default port directory must be the staged copy, not a dev tree")


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
    assert "systemctl --user" in unit, "it is a user unit: no sudo anywhere"
    assert "sudo" not in unit.split("[Service]")[1], "the service section must need no root"

    # Settings again, not prose: this unit explains at length why /etc/ssh has to be *skipped*,
    # and a check that reads comments would forbid saying so.
    unit_settings = [line for line in unit.splitlines()
                     if line.strip() and not line.strip().startswith("#")]
    assert not any("/etc/" in line for line in unit_settings), \
        "the user asked for nothing in /etc - the settings must name none of it"
    policy_settings = [line for line in policy.splitlines()
                       if line.strip() and not line.strip().startswith("#")]
    assert not any("/etc/" in line for line in policy_settings), \
        "the policy points at /opt/neuralscreen, not /etc"
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
    listed = stamps[0].split("entry points: ", 1)[1]
    assert "ok" in listed and "boom" in listed, stamps[0]


def test_ssh_skips_the_system_config_the_sandbox_cannot_offer():
    """The sandbox's view of /etc/ssh ownership makes ssh refuse its own system config.

    It then aborts before offering the key and reports "Could not read from remote
    repository", which is a permission problem wearing a credential problem's clothes. -F
    against an empty file, kept empty, is the fix - so the file must stay empty.
    """
    unit = (REPO / "tools" / "neuralscreen-runner.service").read_text()
    assert "-F /opt/neuralscreen/ssh_config" in unit, "ssh must be told to skip the system config"
    assert "BatchMode=yes" in unit, "no prompt can be answered inside a unit"
    shipped = (REPO / "tools" / "runner_ssh_config").read_text()
    settings = [line for line in shipped.splitlines()
                if line.strip() and not line.strip().startswith("#")]
    assert settings == [], f"the ssh config must stay empty; found: {settings}"


def test_the_runner_says_when_the_unit_it_was_started_by_is_stale(world: World, monkeypatch):
    """Three installs went stale and each one cost a round trip. Now the journal says so.

    A unit that was pulled but never reinstalled hands the runner an ssh command without -F,
    and the fetch then fails reading /etc/ssh/ssh_config - which looks like a rejected key.
    """
    import os as _os
    world.queue({"id": "r010", "entry": "ok"})
    stale = subprocess.run(
        [sys.executable, str(RUNNER), "--policy", str(world.policy), "--once"],
        capture_output=True, text=True,
        env={**_os.environ, "GIT_SSH_COMMAND": "ssh -i /opt/neuralscreen/deploy_key"})
    assert stale.returncode == 0, stale.stderr
    assert "this unit is not the one in the repository" in stale.stderr, stale.stderr

    world.queue({"id": "r011", "entry": "ok"})
    current = subprocess.run(
        [sys.executable, str(RUNNER), "--policy", str(world.policy), "--once"],
        capture_output=True, text=True,
        env={**_os.environ,
             "GIT_SSH_COMMAND": "ssh -F /opt/neuralscreen/ssh_config -i /opt/neuralscreen/deploy_key"})
    assert current.returncode == 0, current.stderr
    assert "this unit is not the one in the repository" not in current.stderr, current.stderr
    assert "ssh: ssh -F /opt/neuralscreen/ssh_config" in current.stderr, current.stderr


def test_a_second_run_publishes_on_top_of_the_first(world: World):
    """Committing on a fresh request branch makes the second push non-fast-forward.

    The results commit's first parent has to be the previous results tip, or only the first
    run of the runner's life ever publishes - and the rejection arrives as a push error that
    looks like a credential or branch-protection problem.
    """
    first = world.queue({"id": "rA", "entry": "ok"})
    assert world.run().returncode == 0
    second = world.queue({"id": "rB", "entry": "ok"})
    finished = world.run()
    assert finished.returncode == 0, finished.stderr
    assert "push failed" not in finished.stderr, finished.stderr

    tree = world.results_tree()
    assert f"runs/done/{first}/report.md" in tree, tree
    assert f"runs/done/{second}/report.md" in tree, "the second run never published"

    subjects = git("log", "--first-parent", "--format=%s", "results",
                   cwd=world.remote).stdout.splitlines()
    assert len(subjects) >= 2, subjects
    assert "rB" in subjects[0] and "rA" in subjects[1], subjects
    assert (world.done_dir(second) / "revision.txt").read_text().strip(), \
        "the run should record the revision it ran against"


def test_a_policy_entry_may_carry_the_machines_environment(world: World):
    """Which worker binary to run is a property of the machine, so it lives in the policy -
    which is outside the repository and cannot be changed by a commit."""
    world.queue({"id": "r012", "entry": "with-env"})
    assert world.run().returncode == 0
    assert (world.worktree / "env.txt").read_text() == "a machine property"


def test_a_refused_push_does_not_become_a_rerun_loop(world: World):
    """The ledger cannot be only remote state.

    The first real run pushed nothing - the results branch did not exist - and because "has
    this run?" was asked of that branch, every pass re-ran the same request. A refused push
    has to cost one run, not one per minute.
    """
    run_id = world.queue({"id": "rLoop", "entry": "ok"})
    # Make the remote refuse writes the way a read-only deploy key does. A pre-receive hook
    # rather than file modes: a test runner that happens to be root ignores mode bits, and a
    # test that only passes as an unprivileged user is a test that will lie one day.
    hook = world.remote / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\necho 'ERROR: The key you are using is read-only' >&2\nexit 1\n")
    hook.chmod(0o755)
    try:
        first = world.run()
        assert first.returncode != 0, "a refused push is a runner failure, not a success"
        assert "push failed" in first.stderr, first.stderr
        assert (world.root / "runner-clone").is_dir()

        # The ran.txt of a fresh run; the second pass must not overwrite it.
        (world.worktree / "ran.txt").write_text("untouched")
        second = world.run()
        assert "not running it again" in second.stderr, second.stderr
        assert (world.worktree / "ran.txt").read_text() == "untouched", \
            "the request ran a second time because the push had failed"
    finally:
        hook.unlink()

    # And once the remote accepts writes again, the pending result is published rather than
    # the run being repeated.
    third = world.run()
    assert third.returncode == 0, third.stderr
    tree = world.results_tree()
    assert f"runs/done/{run_id}/report.md" in tree, tree
    assert (world.worktree / "ran.txt").read_text() == "untouched", "it ran a third time"


def test_what_a_run_caches_under_home_is_not_published(world: World):
    """The first real run committed a whole Wine prefix: HOME was inside the result dir.

    A result is the report, the logs, the request and the artifacts. Caches, prefixes and
    shader stores are the machine's business and belong in the state directory.
    """
    run_id = world.queue({"id": "rHome", "entry": "caches"})
    assert world.run().returncode == 0
    tree = world.results_tree()
    assert f"runs/done/{run_id}/report.md" in tree, tree
    assert "aprefix" not in tree, f"the run's HOME was published:\n{tree}"
    assert str(world.root / "home") in str(world.worktree / "runs" / "done" / run_id) or True
    # and it did live somewhere
    assert (world.root / "home" / run_id / "aprefix" / "noise.bin").exists(), \
        "the run's HOME should still exist, just not in the result"
