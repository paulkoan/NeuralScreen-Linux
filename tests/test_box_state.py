"""The bridge between the runner and the box-state check, pinned from both sides.

The deployed policy lives outside the repository and is installed by hand, so it changes only when
the human does something - and "I have done it" used to be a message only they could send. The
runner now publishes the file to the results branch whenever its hash changes, and
`hermes/ns-box-state.py` reads it back.

The two halves live in different trees: the runner is in this repository, the check is installed into
a profile, and they agree through a commit subject. So the shared format is asserted here rather
than left to a comment on one side - a change to either that the other does not follow would
otherwise show up as `unknown` on a box that is perfectly fine.

The check is tested from `hermes/`, the version-controlled copy. `hermes/install.sh --check` is what
keeps the installed one identical, so exercising that copy is exercising what runs.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "tools" / "auto_runner.py"
BOX_STATE = REPO / "hermes" / "ns-box-state.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_check_reads_the_subject_the_runner_writes():
    runner = load("runner_under_test", RUNNER)
    box = load("box_state_under_test", BOX_STATE)
    digest = "92cc2c01922f00ab"
    assert box.deployed_hash(runner.POLICY_COMMIT_SUBJECT.format(digest=digest[:12])) == digest[:12]


def test_an_unreadable_subject_says_so_rather_than_guessing():
    box = load("box_state_under_test", BOX_STATE)
    assert box.deployed_hash("") == "unknown"
    assert box.deployed_hash("run r2026-11-10-6-sma: exit 0 on abc123") == "unknown"
