#!/usr/bin/env python3
"""Fetch the results branch and print whatever arrived since the last look.

This is the half of the loop that is *not* on the GPU box: it runs wherever the results are
read, fetches `origin/results`, and prints a summary of each run that has not been seen
before. Nothing is executed and nothing is written to the branch — a fetch, a diff against a
state file, and stdout for whoever is reading it.

    tools/results_watch.py                # fetch, print new results, remember them
    tools/results_watch.py --all          # every result on the branch, ignore the state
    tools/results_watch.py --check        # exit 1 if anything is new, print nothing else

Exit codes: 0 nothing new (or printed), 1 something new under --check, 2 the fetch failed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get("NS_RESULTS_STATE", Path.home() / ".cache" / "neuralscreen-results.json"))


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True,
                          check=check)


def fetch(branch: str) -> bool:
    result = git("fetch", "origin", f"{branch}:refs/remotes/origin/{branch}", check=False)
    if result.returncode != 0:
        # Before the first run there is no branch, which is not a failure and must not look
        # like one: until the runner has published something there is nothing to watch.
        if "couldn't find remote ref" in result.stderr:
            return True
        print(f"could not fetch {branch}: {result.stderr.strip()}", file=sys.stderr)
        return False
    return True


def ids_on(branch: str) -> list[str]:
    listing = git("ls-tree", "-d", "--name-only", f"origin/{branch}", "runs/done/", check=False)
    if listing.returncode != 0:
        return []
    return sorted(line.rsplit("/", 1)[-1] for line in listing.stdout.split() if line.strip())


def load_state() -> set[str]:
    try:
        return set(json.loads(STATE.read_text()))
    except Exception:
        return set()


def save_state(seen: set[str]) -> None:
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(sorted(seen)))
    except OSError as error:
        print(f"[watch] could not write {STATE}: {error}", file=sys.stderr)


def read(revision: str, path: str) -> str:
    return git("show", f"{revision}:{path}", check=False).stdout


def summary(branch: str, run_id: str) -> str:
    revision = f"origin/{branch}"
    result = read(revision, f"runs/done/{run_id}/result.json")
    command = read(revision, f"runs/done/{run_id}/command.txt").strip()
    report = read(revision, f"runs/done/{run_id}/report.md")
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        data = {}
    lines = [f"run {run_id}: exit {data.get('exit_code', '?')} in {data.get('seconds', '?')}s",
             f"  {command}"]
    refused = data.get("refused")
    if refused:
        lines.append(f"  REFUSED: {refused}")
    # The tail is where a timing run says what happened; the head is where a failure does.
    interesting = [line for line in report.splitlines()
                   if any(word in line for word in
                          ("fps", "frame", "ms", "error", "Error", "FAIL", "assert", "timing",
                           "spread", "frames:", "capture", "send", "recv", "display"))]
    for line in interesting[-12:]:
        lines.append(f"  | {line}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--branch", default="results")
    parser.add_argument("--all", action="store_true", help="ignore the state file")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 when there is something new, print nothing")
    parser.add_argument("--verbose", action="store_true",
                        help="say so even when nothing is new: a cron job wants silence")
    args = parser.parse_args(argv)

    if not fetch(args.branch):
        return 2
    present = ids_on(args.branch)
    seen = set() if args.all else load_state()
    new = [run_id for run_id in present if run_id not in seen]

    if args.check:
        return 1 if new else 0
    if not new:
        # Silent by default: this is meant to run on a timer, and a job that says "nothing
        # happened" every ten minutes is a job people stop reading.
        if args.verbose:
            print(f"no new results on {args.branch} ({len(present)} on the branch)")
        save_state(set(present))
        return 0
    for run_id in new:
        print(summary(args.branch, run_id))
        print()
    save_state(set(present) | set(new))
    return 0


if __name__ == "__main__":
    sys.exit(main())
