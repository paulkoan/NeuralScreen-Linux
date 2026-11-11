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
BOX_OFF = REPO / "hermes" / "ns-box-off.py"


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


def test_the_box_off_marker_clears_itself_when_a_result_lands(tmp_path, monkeypatch, capsys):
    """Declared, not inferred - and it ends by itself, so nobody has to report the box coming back.

    While the box is off the tick's item is blocked on a run that cannot happen, and reporting that
    as a stall is noise about a machine being switched off. The one message worth sending is the one
    that says it is over, and the arrival of a result is what says it.
    """
    box = load("box_off_under_test", BOX_OFF)
    monkeypatch.setattr(box, "MARKER", tmp_path / ".box-off")
    monkeypatch.setattr(box, "newest_result", lambda: "aaa111")

    box.mark("the box is off for the night")
    capsys.readouterr()
    assert box.MARKER.exists()

    box.status()
    assert capsys.readouterr().out.strip() == "the box is off for the night"

    monkeypatch.setattr(box, "newest_result", lambda: "bbb222")
    box.status()
    assert "The box is back" in capsys.readouterr().out
    assert not box.MARKER.exists(), "the declaration outlived the box coming back"


def test_a_failed_fetch_does_not_read_as_the_box_being_back(tmp_path, monkeypatch, capsys):
    """A network blip must not clear the declaration, or the noise returns on the next tick."""
    box = load("box_off_under_test", BOX_OFF)
    monkeypatch.setattr(box, "MARKER", tmp_path / ".box-off")
    monkeypatch.setattr(box, "newest_result", lambda: "aaa111")
    box.mark("the box is off")
    capsys.readouterr()

    monkeypatch.setattr(box, "newest_result", lambda: "")
    box.status()
    assert capsys.readouterr().out == ""
    assert box.MARKER.exists()
