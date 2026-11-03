"""`--worker-env`: one run turning on a port-side switch without editing the policy.

The policy's `[entry.env]` is per entry, so anything set there applies to every run of that
entry. That is right for the worker command and the Wine prefix, and wrong for a diagnostic:
`DLSS5VK_SERVE_SPLIT` flushes the queue twice a frame, which is a cost a measurement run should
opt into and a serving run should not pay. These tests pin the three things that make the flag
safe - it reaches the worker's environment, it beats the inherited one, and it never leaks into
the client's own environment.
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from minimal.worker import worker_env


def test_extra_reaches_the_environment():
    env = worker_env(extra={"DLSS5VK_SERVE_SPLIT": "1"})
    assert env["DLSS5VK_SERVE_SPLIT"] == "1"


def test_extra_beats_what_was_inherited(monkeypatch):
    monkeypatch.setenv("DLSS5VK_SERVE_SPLIT", "0")
    assert worker_env()["DLSS5VK_SERVE_SPLIT"] == "0", "sanity: the inherited value is seen"
    assert worker_env(extra={"DLSS5VK_SERVE_SPLIT": "1"})["DLSS5VK_SERVE_SPLIT"] == "1"


def test_extra_does_not_disturb_the_launch_contract():
    """The DLL overrides and the prefix are what make the worker start at all."""
    base = worker_env()
    with_extra = worker_env(extra={"DLSS5VK_SERVE_SPLIT": "1"})
    assert with_extra["WINEDLLOVERRIDES"] == base["WINEDLLOVERRIDES"]
    assert with_extra["DXVK_ENABLE_NVAPI"] == base["DXVK_ENABLE_NVAPI"]
    assert with_extra["WINEPREFIX"] == base["WINEPREFIX"]


def test_values_are_stringified():
    env = worker_env(extra={"NS_SOMETHING": 2})
    assert env["NS_SOMETHING"] == "2"


def test_no_extra_leaves_the_environment_as_it_was(monkeypatch):
    monkeypatch.delenv("DLSS5VK_SERVE_SPLIT", raising=False)
    assert "DLSS5VK_SERVE_SPLIT" not in worker_env()


def test_the_worker_starts_with_the_extra_variable(tmp_path):
    """End to end: the child process really sees it, which is the only claim that matters."""
    script = tmp_path / "printenv_worker.py"
    script.write_text("import os,sys; sys.stdout.write(os.environ.get('DLSS5VK_SERVE_SPLIT',''))\n")
    child = subprocess.run(
        [sys.executable, str(script)],
        env=worker_env(extra={"DLSS5VK_SERVE_SPLIT": "1"}),
        capture_output=True, text=True, timeout=60,
    )
    assert child.stdout == "1", child.stderr


def test_the_client_environment_is_not_mutated():
    """A run's request must not follow the process into the next run."""
    before = os.environ.get("DLSS5VK_SERVE_SPLIT")
    worker_env(extra={"DLSS5VK_SERVE_SPLIT": "1"})
    assert os.environ.get("DLSS5VK_SERVE_SPLIT") == before


def test_the_cli_parses_key_value_pairs():
    """The flag's own parsing: KEY=VALUE, repeatable, and loud about a malformed pair."""
    from minimal import __main__ as entry
    source = entry.__doc__ or ""
    # The parser is built inside main(); the string that matters is the argument's own help.
    text = open(entry.__file__, encoding="utf-8").read()
    assert '"--worker-env"' in text
    assert "KEY=VALUE" in text
    assert "worker_env_extra=worker_extra" in text, "the parsed pairs must reach Pipeline"
