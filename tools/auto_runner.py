#!/usr/bin/env python3
"""Turn a run request in the repository into a result in the repository.

The loop it closes: someone commits `runs/queue/<id>.json` naming an entry point and its
arguments; this runs it on the machine with the GPU and commits what happened to a results
branch. Nothing here decides what is safe to run — that is the point. The policy file and
the systemd unit that starts this live outside the repository, root-owned, so a commit
cannot loosen them; this process is the executor, and the sandbox it runs inside is the
bound. See `tools/runner_policy.example.toml` and `tools/neuralscreen-runner.service`.

What it does hold to:

  * no shell, ever. A request names an entry from the policy and gives a list of strings;
    they are passed to execve as they are, so `$(...)` in an argument is an argument.
  * no surprise entry points. An entry the policy does not name is refused, and refusal is
    written down and pushed like any other outcome, because a request nobody ran and nobody
    noticed is the one failure mode worth engineering against.
  * one run per id, ever. The id is the directory it lands in; `runs/done/<id>` means it
    happened, and a request whose id is there is skipped.
  * the runner's own checkout. It clones into its own directory and never touches the
    developer's working tree, which may have uncommitted work in it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

MAX_ARG = 512
ENTRY_NAME = "entry"


class Refused(Exception):
    """The request is not something this runner will do."""


class RunnerError(Exception):
    """The runner itself could not proceed - and the reason goes in the journal.

    Anything git says is carried up rather than swallowed: a clone that fails inside a
    systemd unit with a bare exit code sends whoever reads the journal looking in the wrong
    place, which is exactly what happened the first time this ran.
    """


def fingerprint(path: Path) -> str:
    """Which copy of a file is running, in twelve characters.

    The first run inside the unit failed from a traceback that pointed at line 80 of a file
    I had already replaced: the pull landed and the install step did not, and nothing said
    so. A stamp makes "which code is running" answerable from the journal instead of
    inferable from a line number.
    """
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except OSError:
        return "unreadable"


def log(message: str) -> None:
    print(f"[runner] {message}", file=sys.stderr, flush=True)


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True,
                            check=False)
    if check and result.returncode != 0:
        raise RunnerError(f"git {' '.join(args)} failed ({result.returncode}): "
                          f"{result.stderr.strip() or result.stdout.strip()}")
    return result


def load_policy(path: Path) -> dict:
    with open(path, "rb") as handle:
        policy = tomllib.load(handle)
    for key in ("repo_url", "worktree", "results_branch"):
        if key not in policy:
            raise SystemExit(f"the policy at {path} is missing {key!r}")
    policy.setdefault("request_branch", "main")
    policy.setdefault("max_timeout_s", 900)
    policy.setdefault("default_timeout_s", 300)
    policy.setdefault("verbose", True)
    entries = {}
    for entry in policy.get("entry", []):
        name = entry.get("name")
        argv = entry.get("argv")
        if not name or not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
            raise SystemExit(f"a policy entry is malformed: {entry!r}")
        entries[name] = entry
    policy["entries"] = entries
    return policy


def prepare_checkout(policy: dict) -> Path:
    """The runner's own clone, updated to the request branch. Never the user's tree."""
    worktree = Path(policy["worktree"]).expanduser()
    if not (worktree / ".git").exists():
        worktree.parent.mkdir(parents=True, exist_ok=True)
        log(f"cloning {policy['repo_url']} into {worktree}")
        clone = subprocess.run(["git", "clone", policy["repo_url"], str(worktree)],
                               capture_output=True, text=True)
        if clone.returncode != 0:
            raise RunnerError(
                f"could not clone {policy['repo_url']}: "
                f"{clone.stderr.strip() or clone.stdout.strip()}\n"
                f"  (a name that will not resolve and a key that will not authenticate both "
                f"look like this from here; the line above is git's own reason)")
    git(worktree, "fetch", "origin", "--prune")
    git(worktree, "checkout", "-B", policy["request_branch"],
        f"origin/{policy['request_branch']}")
    git(worktree, "reset", "--hard", f"origin/{policy['request_branch']}")
    return worktree


def validate(request: dict, policy: dict, source: Path) -> tuple[dict, list[str], int, list[str]]:
    if not isinstance(request, dict):
        raise Refused("the request is not an object")
    entry_name = request.get(ENTRY_NAME)
    if not isinstance(entry_name, str) or entry_name not in policy["entries"]:
        raise Refused(f"entry {entry_name!r} is not in the policy "
                      f"(it names {sorted(policy['entries'])})")
    args = request.get("args", [])
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise Refused("args must be a list of strings")
    for arg in args:
        if len(arg) > MAX_ARG or "\x00" in arg or "\n" in arg:
            raise Refused(f"argument is too long or carries a newline: {arg[:60]!r}")
    timeout = int(request.get("timeout_s", policy["default_timeout_s"]))
    if timeout <= 0 or timeout > policy["max_timeout_s"]:
        raise Refused(f"timeout {timeout}s is outside 1..{policy['max_timeout_s']}")
    artifacts = request.get("artifacts", [])
    if not isinstance(artifacts, list) or not all(isinstance(a, str) for a in artifacts):
        raise Refused("artifacts must be a list of strings")
    for artifact in artifacts:
        if artifact.startswith("/") or ".." in Path(artifact).parts:
            raise Refused(f"artifact {artifact!r} is not a relative path inside the repo")
    note = request.get("note", "")
    if not isinstance(note, str):
        raise Refused("note must be a string")
    return policy["entries"][entry_name], args, timeout, artifacts


def wrap_for_container(entry: dict, policy: dict, argv: list[str], worktree: Path,
                       run_dir: Path) -> list[str]:
    """Put the command in the sandbox the entry asks for, or run it where we are."""
    if not entry.get("container", policy.get("container", False)):
        return argv
    image = entry.get("image", policy.get("image"))
    if not image:
        raise Refused("the entry asks for a container but the policy names no image")
    mounts = entry.get("mounts", policy.get("mounts", []))
    # No network by default: the sandbox is the bound, and a run that needs the network
    # (a build that fetches its own dependencies) says so in the policy, per entry.
    network = entry.get("network", policy.get("network", "none"))
    command = ["podman", "run", "--rm", f"--network={network}",
               "--device", entry.get("device", policy.get("device", "nvidia.com/gpu=all")),
               "--ipc=host",
               "-v", f"{worktree}:/work:ro", "-v", f"{run_dir}:/out:rw",
               "-w", "/work"]
    for mount in mounts:
        command += ["-v", str(mount)]
    return command + [image, *argv]


def run_request(request: dict, policy: dict, worktree: Path, run_dir: Path,
                dry_run: bool = False) -> int:
    entry, args, timeout, artifacts = validate(request, policy, run_dir)
    argv = list(entry["argv"]) + args
    if entry.get("cwd"):
        os.chdir(worktree / entry["cwd"]) if not dry_run else None
    command = wrap_for_container(entry, policy, argv, worktree, run_dir)

    (run_dir / "command.txt").write_text(" ".join(command) + "\n")
    log(f"running: {' '.join(command)}")
    if dry_run:
        return 0

    env = dict(os.environ)
    # A policy entry may carry environment of its own: which worker binary to run is a
    # property of the machine, and the policy is where machine properties belong.
    env.update({str(key): str(value) for key, value in (entry.get("env") or {}).items()})
    # HOME outside the run directory. Inside it, everything a program caches under $HOME -
    # Wine prefixes, mesa shader caches, GLCache - is published as part of the result: the
    # first real run committed 179,000 characters of file listing for it.
    env["HOME"] = str(state_dir(policy, "home") / run_dir.name)
    Path(env["HOME"]).mkdir(parents=True, exist_ok=True)
    env.pop("GIT_ASKPASS", None)          # a run does not need the runner's push credential
    started = time.monotonic()
    try:
        finished = subprocess.run(command, cwd=str(worktree), env=env, timeout=timeout,
                                  capture_output=True, text=True)
        code, out, err = finished.returncode, finished.stdout, finished.stderr
    except subprocess.TimeoutExpired as expired:
        code = 124
        out = (expired.stdout or b"").decode("utf-8", "replace") if isinstance(expired.stdout, bytes) else (expired.stdout or "")
        err = ((expired.stderr or b"").decode("utf-8", "replace") if isinstance(expired.stderr, bytes) else (expired.stderr or "")) + \
              f"\n[runner] killed after {timeout}s\n"
    elapsed = time.monotonic() - started

    (run_dir / "stdout.log").write_text(out or "")
    (run_dir / "stderr.log").write_text(err or "")
    for artifact in artifacts:
        source = worktree / artifact
        if source.exists():
            shutil.copy2(source, run_dir / Path(artifact).name)
        else:
            log(f"artifact {artifact} was not produced")
    (run_dir / "result.json").write_text(json.dumps(
        {"exit_code": code, "seconds": round(elapsed, 3), "argv": argv,
         "artifacts": artifacts}, indent=2) + "\n")
    (run_dir / "report.md").write_text(
        f"# run {run_dir.name}\n\n"
        f"`{' '.join(argv)}`\n\n"
        f"exit **{code}** after {elapsed:.1f}s\n\n"
        f"```\n{(out or '')[-4000:]}\n```\n\n"
        f"stderr:\n\n```\n{(err or '')[-4000:]}\n```\n")
    return code


def publish(worktree: Path, policy: dict, run_dir: Path, exit_code: int,
            dry_run: bool = False) -> None:
    """Commit the result on top of the results branch and push it.

    The commit is built with plumbing rather than `git commit`, and that is not pedantry:

      * its FIRST parent is the previous results tip, so every pass fast-forwards. Committing
        on the checkout instead would build each result on a fresh request branch, and the
        second push would be rejected as non-fast-forward - only the first run would ever
        publish.
      * its second parent is the request branch, so the result stays diffable against the
        code it ran on without carrying a copy of that code as its history.
      * the working tree is left on the request branch, which is what the entries ran against.

    The tree is the request branch's tree plus runs/, so a result is still readable next to
    the exact code that produced it.
    """
    if dry_run:
        log(f"would publish {run_dir} to {policy['results_branch']}")
        return
    results, request = policy["results_branch"], policy["request_branch"]
    restore_local_results(policy, worktree)
    revision = git(worktree, "rev-parse", f"origin/{request}").stdout.strip()
    (run_dir / "revision.txt").write_text(revision + "\n")

    # The tree is the request branch's code - what the run actually used - with everything the
    # results branch has accumulated under runs/ laid over it. Staging runs/ from the checkout
    # alone would drop the previous runs' results: the checkout is reset to the request branch
    # every pass, so it remembers nothing.
    git(worktree, "read-tree", f"origin/{request}")
    parents = []
    if git(worktree, "rev-parse", "--verify", f"origin/{results}", check=False).returncode == 0:
        parents.append(f"origin/{results}")
        git(worktree, "checkout", f"origin/{results}", "--", "runs")
    parents.append(f"origin/{request}")

    # A request that has run does not belong in the snapshot: the queue is the request
    # branch's business, and the results branch should show what happened, not what was asked.
    for stale in (worktree / "runs" / "queue").glob("*.json"):
        if (worktree / "runs" / "done" / stale.stem).exists():
            stale.unlink()

    git(worktree, "add", "-A", "runs")
    tree = git(worktree, "write-tree").stdout.strip()

    # An identity of its own: the runner has none, and a commit that fails for want of a name
    # would lose the run's only trace.
    message = f"run {run_dir.name}: exit {exit_code} on {revision[:12]}"
    made = git(worktree, "-c", "user.name=neuralscreen-runner",
               "-c", "user.email=runner@localhost", "commit-tree", tree,
               *[arg for parent in parents for arg in ("-p", parent)], "-m", message)
    commit = made.stdout.strip()
    push = git(worktree, "push", "origin", f"{commit}:refs/heads/{results}", check=False)
    if push.returncode != 0:
        log(f"push failed: {push.stderr.strip()}")
        raise SystemExit(2)
    log(f"published {run_dir.name} to {results} (on {revision[:12]})")


def state_dir(policy: dict, kind: str) -> Path:
    """Where runs are remembered on this machine, beside the clone but never in it.

    The clone is reset every pass, so it can hold no memory. The results branch can, but only
    if the push succeeded - and when it does not, a ledger made of remote state says "never
    ran" about a run that just took four minutes of GPU. So there are two ledgers, and the
    local one is written before the run rather than after it.
    """
    root = Path(policy["worktree"]).expanduser().parent / kind
    root.mkdir(parents=True, exist_ok=True)
    return root


def restore_local_results(policy: dict, worktree: Path) -> list[str]:
    """Put runs that never reached the branch back into the tree, so a refused push is not a
    lost run: the next pass publishes them along with its own."""
    local = Path(policy["worktree"]).expanduser().parent / "done"
    if not local.exists():
        return []
    restored = []
    for entry in sorted(local.iterdir()):
        target = worktree / "runs" / "done" / entry.name
        if entry.is_dir() and not target.exists():
            shutil.copytree(entry, target)
            restored.append(entry.name)
    if restored:
        log(f"publishing {len(restored)} run(s) that a previous push left behind: "
            f"{', '.join(restored)}")
    return restored


def done_ids(worktree: Path, policy: dict) -> set[str]:
    """The ledger: which ids the results branch already holds.

    Not the working tree, and not the local history: this checkout is reset to the request
    branch every pass, so anything it remembers from a previous run is gone. The results
    branch is the only place a run's outcome survives, which makes it the only honest place
    to ask "has this already happened?".
    """
    listing = git(worktree, "ls-tree", "-d", "--name-only",
                  f"origin/{policy['results_branch']}", "runs/done/", check=False)
    if listing.returncode != 0:
        return set()
    return {line.rsplit("/", 1)[-1] for line in listing.stdout.split() if line.strip()}


def publish_pending(policy: dict, worktree: Path, already: set[str], dry_run: bool = False) -> None:
    """Publish results that never reached the branch, whether or not anything is queued.

    A push can be refused - a read-only key, a remote that was briefly unavailable - and the
    run it belonged to is then sitting in the state directory, done but unpublished. Waiting
    for a new request to carry it out would mean a paused queue silently loses it, and the
    rescue would be timed by luck.
    """
    local = state_dir(policy, "done")
    if not local.exists():
        return
    pending = [d for d in sorted(local.iterdir()) if d.is_dir() and d.name not in already]
    if not pending:
        return
    log(f"{len(pending)} result(s) never reached the branch: "
        f"{', '.join(d.name for d in pending)}")
    restore_local_results(policy, worktree)
    exit_code = 0
    try:
        exit_code = int(json.loads((pending[-1] / "result.json").read_text()).get("exit_code", 0))
    except (OSError, ValueError):
        pass
    publish(worktree, policy, pending[-1], exit_code, dry_run=dry_run)


def process(policy: dict, worktree: Path, dry_run: bool = False) -> int:
    already = done_ids(worktree, policy)
    queue = sorted((worktree / "runs" / "queue").glob("*.json"))
    if not queue:
        log("nothing queued")
    attempted = state_dir(policy, "attempted")
    for request_path in queue:
        run_id = request_path.stem
        run_dir = worktree / "runs" / "done" / run_id
        if (attempted / run_id).exists():
            # Written before the run, not after: a pass that dies half way through must not
            # decide on the next pass that nothing happened.
            log(f"{run_id}: already attempted on this machine, skipping")
            continue
        if run_id in already:
            log(f"{run_id}: already on {policy['results_branch']}, skipping")
            continue
        if run_dir.exists():
            log(f"{run_id}: already done, skipping")
            continue
        run_dir.mkdir(parents=True)
        (attempted / run_id).write_text("")
        try:
            request = json.loads(request_path.read_text())
            shutil.copy2(request_path, run_dir / "request.json")
            request_path.unlink()
            exit_code = run_request(request, policy, worktree, run_dir, dry_run=dry_run)
        except Refused as refusal:
            exit_code = 126
            log(f"{run_id}: refused: {refusal}")
            (run_dir / "report.md").write_text(
                f"# run {run_id}\n\n**Refused.** {refusal}\n\n"
                f"Nothing was executed. The entry points this runner knows:\n\n" +
                "".join(f"* `{name}`: `{' '.join(entry['argv'])}`\n"
                        for name, entry in sorted(policy["entries"].items())))
            (run_dir / "result.json").write_text(json.dumps(
                {"exit_code": exit_code, "refused": str(refusal)}, indent=2) + "\n")
        except Exception as error:                     # noqa: BLE001 - recorded, not eaten
            exit_code = 125
            log(f"{run_id}: the runner itself failed: {error!r}")
            (run_dir / "report.md").write_text(f"# run {run_id}\n\n**The runner failed.** "
                                               f"`{error!r}`\n")
        # A copy outside the clone, so the result survives the reset that follows it - and so
        # a push that was refused can be retried by the next pass instead of the run being
        # repeated.
        local = state_dir(policy, "done") / run_id
        if not local.exists():
            shutil.copytree(run_dir, local)
        # Whatever ran may have written a home/ into the result before this was fixed; it is
        # never part of what a result means.
        stale_home = run_dir / "home"
        if stale_home.exists():
            shutil.rmtree(stale_home)
        publish(worktree, policy, run_dir, exit_code, dry_run=dry_run)
        already.add(run_id)

    # Unconditionally, and after the loop rather than before it: a queue whose only entries
    # were already attempted would otherwise return here and leave a finished run unpublished
    # until an unrelated request happened to arrive.
    publish_pending(policy, worktree, already, dry_run=dry_run)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--policy", default="/etc/neuralscreen-runner/policy.toml",
                        help="the policy, outside the repository and root-owned")
    parser.add_argument("--once", action="store_true", help="one pass, then exit (default)")
    parser.add_argument("--dry-run", action="store_true",
                       help="validate and print, run nothing, push nothing")
    parser.add_argument("--request", help="only this request file (for testing)")
    args = parser.parse_args(argv)

    policy_path = Path(args.policy)
    if not policy_path.exists():
        raise SystemExit(f"no policy at {policy_path}: install "
                         f"tools/runner_policy.example.toml as root first")
    policy = load_policy(policy_path)
    log(f"runner {fingerprint(Path(__file__))} · policy {fingerprint(policy_path)} "
        f"· entry points: {', '.join(sorted(policy['entries']))}")
    # Which ssh the unit handed us, and whether it is the one the repository ships. A unit
    # that was pulled but never reinstalled looks exactly like a rejected key: ssh reads
    # /etc/ssh/ssh_config, the sandbox will not let it, and the fetch fails saying the
    # repository's access rights are wrong.
    ssh_command = os.environ.get("GIT_SSH_COMMAND", "")
    log(f"ssh: {ssh_command or '(unset: git uses its own default)'}")
    if "/opt/neuralscreen/ssh_config" not in ssh_command:
        log("  ^ this unit is not the one in the repository: pull, reinstall it into "
            "~/.config/systemd/user/, daemon-reload, then start it again. Without -F, ssh "
            "reads /etc/ssh/ssh_config and the sandbox makes it refuse that file.")

    pause = policy.get("pause_file")
    if pause and Path(pause).exists():
        log(f"paused: {pause} exists, nothing runs")
        return 0

    try:
        worktree = prepare_checkout(policy)
    except RunnerError as error:
        log(str(error))
        return 3
    if args.request:
        source = Path(args.request)
        queue = worktree / "runs" / "queue"
        queue.mkdir(parents=True, exist_ok=True)
        target = queue / source.name
        shutil.copy2(source, target)
    return process(policy, worktree, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
