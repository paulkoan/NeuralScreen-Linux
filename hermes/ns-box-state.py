#!/usr/bin/env python3
"""What the box is actually running, reported without anyone being asked.

The deployed policy is the one input that changes only when the human does something: it lives
outside the repository, it is installed by hand, and until now the only way to learn a change had
landed was to ask them whether it had. That is the question this answers.

The runner publishes the file to the results branch whenever its hash changes - whether or not
anything ran - so the box's own state is readable from here as a file. The publishing commit's
subject carries the hash of the file the box is *running*, because the published copy is redacted
and its own digest is therefore not the deployed one.

Prints the state when there is something to say, and nothing when there is not. The caller holds a
marker of the last thing said, so a message that has not changed is not repeated: this prints the
current state every time, and the watchdog speaks once per distinct text. It prints nothing at all
when it cannot read the branch, because a failed fetch is not news about the box.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/data/neuralscreen-linux")
REVIEWED = REPO / "ops" / "policy.toml"


def git(*args: str, timeout: int = 20) -> str:
    try:
        done = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True,
                              text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout if done.returncode == 0 else ""


def deployed_hash(subject: str) -> str:
    """The deployed file's hash, read out of the publishing commit's subject.

    The published copy is redacted, so its own digest would answer a different question. This reads
    the format tools/auto_runner.py writes (`POLICY_COMMIT_SUBJECT`); tests/test_box_state.py pins
    the two against each other, because the runner lives in this repository and this does not.
    """
    match = re.search(r"policy ([0-9a-f]{6,})", subject or "")
    return match.group(1) if match else "unknown"


def main() -> int:
    if not (REPO / ".git").exists():
        return 0
    git("fetch", "-q", "origin", "results", timeout=25)
    published = git("show", "origin/results:runs/policy.toml")
    if not published.strip():
        return 0

    # The commit that last wrote the file, and when. Its subject names the deployed hash:
    # "policy 92cc2c01922f: the file the box is running under".
    subject = git("log", "-1", "--format=%s", "origin/results", "--", "runs/policy.toml").strip()
    when = git("log", "-1", "--format=%ci", "origin/results", "--", "runs/policy.toml").strip()
    commit = git("log", "-1", "--format=%h", "origin/results", "--", "runs/policy.toml").strip()
    deployed = deployed_hash(subject)

    reviewed = REVIEWED.read_text() if REVIEWED.exists() else ""
    if not reviewed:
        return 0

    lines = [f"The box's policy is {deployed}, published {when} as {commit}."]
    if published == reviewed:
        lines.append("It matches ops/policy.toml exactly, so the box is running the reviewed copy.")
    else:
        lines.append("It does NOT match ops/policy.toml. The box is running something the "
                     "repository does not have, which is fine if that is deliberate - the diff "
                     "is `git show origin/results:runs/policy.toml` against ops/policy.toml.")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
