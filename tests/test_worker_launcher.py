"""A relative worker command must not depend on the cwd the process inherited.

The policy configures NS_WORKER_CMD outside the repo, and `xvfb-run -a uv run python -m minimal`
does not guarantee the repository as the worker's cwd: r2026-10-30-l died with
`bash: native/run_worker.sh: No such file or directory` for exactly that reason. The launcher
resolves a relative script against the repo root, where the answer is known.
"""
import os

from minimal.worker import default_launcher


def test_a_relative_worker_script_resolves_against_the_repo(monkeypatch):
    monkeypatch.setenv("NS_WORKER_CMD", "bash native/run_worker.sh --prefix /tmp/w")
    parts = default_launcher()
    assert parts[0] == "bash"
    assert os.path.isabs(parts[1]), parts
    assert parts[1].endswith("/native/run_worker.sh"), parts
    assert parts[2:] == ["--prefix", "/tmp/w"]


def test_an_absolute_worker_command_is_left_alone(monkeypatch):
    monkeypatch.setenv("NS_WORKER_CMD", "/opt/x/serve --model /opt/m")
    assert default_launcher() == ["/opt/x/serve", "--model", "/opt/m"]


def test_a_relative_command_that_is_not_a_script_is_left_alone(monkeypatch):
    monkeypatch.setenv("NS_WORKER_CMD", "some-worker --flag")
    assert default_launcher() == ["some-worker", "--flag"]