"""`run_manually.sh --include-manual` must not read the flag as a filename.

Reported on 2026-11-08, verbatim:

    $ /opt/neuralscreen/run_manually.sh --include-manual
    no policy at --include-manual
      install tools/runner_policy.example.toml as that path first

The script took its policy from `$1`, so the flag became a path and the error named a missing
file that was never meant to be one. The script already passes `--include-manual` to the runner
itself - the wrapper exists *because* it is the thing that takes the manual requests - so the
flag is redundant as well as misread.

These tests run the script for real, with no display and a fake runner, because the failure was
in argument handling and nothing downstream of it.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

SCRIPT = REPO / "tools" / "run_manually.sh"


def run(*args, env_extra=None):
    env = dict(os.environ)
    # No compositor: the script's own check then fails fast, which is the point - it means
    # everything before it (policy, runner) was accepted.
    env["WAYLAND_DISPLAY"] = ""
    env["DISPLAY"] = ""
    env.update(env_extra or {})
    return subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env)


def test_help_exits_zero():
    r = run("--help")
    assert r.returncode == 0, r.stderr
    assert "usage:" in r.stderr
    assert "--include-manual" in r.stderr


def test_the_flag_is_not_read_as_a_policy_path(tmp_path):
    """The reported failure, pinned: the flag must not be taken as the policy path.

    Deliberately says nothing about whether the default policy exists. It does on the box and it
    did not in the sandbox this was written in, and the first version of this test asserted the
    sandbox's state - so it passed here and failed there, joining the box's red suite that blocks
    every code change the loop wants to make.
    """
    r = run("--include-manual")
    combined = r.stdout + r.stderr
    assert "no policy at --include-manual" not in combined, (
        "the flag is being taken as the policy path again - that is the 2026-11-08 report")
    # With no policy argument it uses the default: either that path is missing and the script says
    # so, or the policy is installed and the run gets as far as the display check.
    assert ("no policy at /opt/neuralscreen/policy.toml" in combined
            or "no WAYLAND_DISPLAY or DISPLAY" in combined), combined


def test_a_policy_argument_still_works(tmp_path):
    """It has to keep accepting a path, in either order, next to the flag."""
    policy = tmp_path / "policy.toml"
    policy.write_text("")
    runner = tmp_path / "runner.py"
    runner.write_text("")

    for args in (("--include-manual", str(policy)), (str(policy), "--include-manual")):
        r = run(*args, env_extra={"NEURALSCREEN_RUNNER": str(runner)})
        combined = r.stdout + r.stderr
        assert "no policy at" not in combined, (args, combined)
        assert "no WAYLAND_DISPLAY or DISPLAY" in combined, (
            f"{args}: expected to get past the policy and runner checks to the display check",
            combined)


def test_a_missing_policy_says_what_to_do_about_the_path_that_was_meant(tmp_path):
    """Both halves of the hint, because they are different situations.

    A path the caller named gets told the path came from the argument - the install line would
    be advice about the wrong file. The default path gets the install line, because that is the
    box's own setup step and the only thing that fixes it.
    """
    r = run(str(tmp_path / "absent.toml"))
    assert "no policy at" in r.stderr
    assert "that path was given as the policy argument" in r.stderr, r.stderr

    default = Path("/opt/neuralscreen/policy.toml")
    if not default.exists():
        r = run("--include-manual")
        assert "runner_policy.example.toml" in r.stderr, r.stderr
        assert "install -m 0644" in r.stderr, r.stderr


def test_an_unknown_flag_is_refused_rather_than_ignored():
    r = run("--include-manuall")            # the typo, which used to read as a path
    assert r.returncode == 2, r.returncode
    assert "unknown option: --include-manuall" in r.stderr
    assert "usage:" in r.stderr
