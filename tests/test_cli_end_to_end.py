"""M1 — the CLI entry point end to end.

Runs `python -m minimal` in-process against the mock worker and a virtual X
server, then checks the summary it prints and the PNGs it writes. This is the
M1 acceptance test: the command in docs/MVP-PLAN.md, exercised for real.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

MOCK_WORKER = REPO / "tests" / "mock_worker.py"


@pytest.fixture
def cli_env(xvfb_display, monkeypatch):
    """The environment `python -m minimal` needs to run against the mock."""
    monkeypatch.setenv("DISPLAY", xvfb_display)
    monkeypatch.setenv(
        "NS_WORKER_CMD", f"{sys.executable} {MOCK_WORKER}")
    monkeypatch.chdir(REPO)
    return xvfb_display


def test_cli_runs_and_writes_both_pngs(cli_env, tmp_path, capsys):
    """`--frames 3 --save-before/--save-after` exits 0 and writes two PNGs."""
    from minimal.__main__ import main

    before = tmp_path / "before.png"
    after = tmp_path / "after.png"

    code = main(["--frames", "3", "--headless",
                 "--save-before", str(before), "--save-after", str(after)])
    out = capsys.readouterr().out

    assert code == 0, f"the CLI exited {code}:\n{out}"
    assert before.is_file(), f"no 'before' PNG; output was:\n{out}"
    assert after.is_file(), f"no 'after' PNG; output was:\n{out}"
    assert before.stat().st_size > 0
    assert after.stat().st_size > 0
    assert "frames: 3 done" in out
    assert "0 skipped" in out


def test_cli_before_and_after_differ(cli_env, tmp_path):
    """The processed frame must not be identical to the captured one."""
    from minimal.__main__ import main
    import pygame

    before = tmp_path / "before.png"
    after = tmp_path / "after.png"
    assert main(["--frames", "2", "--headless",
                 "--save-before", str(before),
                 "--save-after", str(after)]) == 0

    b = pygame.image.load(str(before))
    a = pygame.image.load(str(after))
    barray = pygame.surfarray.array3d(b)
    aarray = pygame.surfarray.array3d(a)

    assert barray.shape == aarray.shape, "the frame size changed"
    assert not np.array_equal(barray, aarray), (
        "the 'after' image is identical to the 'before' image — the pixels did "
        "not go through the worker")


def test_cli_pngs_match_the_capture_resolution(cli_env, tmp_path):
    """The written frames are the size of the captured screen."""
    from minimal.__main__ import main
    import pygame
    from minimal.capture import Capture

    with Capture(monitor_idx=0) as cap:
        expect = cap.resolution

    after = tmp_path / "after.png"
    assert main(["--frames", "1", "--headless",
                 "--save-after", str(after)]) == 0
    surface = pygame.image.load(str(after))
    assert surface.get_size() == expect


def test_cli_list_monitors_runs(cli_env, capsys):
    from minimal.__main__ import main
    assert main(["--list-monitors"]) == 0
    assert "monitor 0" in capsys.readouterr().out


def test_cli_reports_a_dead_worker(cli_env):
    """A worker that dies is reported and the CLI exits non-zero."""
    from minimal.__main__ import main
    os.environ["NS_WORKER_CMD"] = f"{sys.executable} {MOCK_WORKER} --fail 2"
    try:
        code = main(["--frames", "8", "--headless"])
    finally:
        os.environ["NS_WORKER_CMD"] = f"{sys.executable} {MOCK_WORKER}"
    assert code != 0, "the CLI reported success despite a dead worker"