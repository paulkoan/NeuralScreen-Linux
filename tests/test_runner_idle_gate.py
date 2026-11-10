"""The idle gate: hold a measurement until the card is not contending, then give up and run.

A pristine box is not achievable - the compositor and a browser always hold VRAM, and a game may
sit resident - so the gate waits for "not BUSY" and caps the wait. These tests pin that a WARN
goes straight through, a BUSY is waited out, and a permanently busy card is run on anyway with
the state recorded rather than the queue stalling forever.
"""
import json
import sys

import tools.auto_runner as runner


class FakeClock:
    """A clock the test advances, so the wait loop does not sleep for real."""

    def __init__(self):
        self.now = 0.0
        self.slept = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.slept += seconds
        self.now += seconds


def test_describe_gpu_names_the_state_and_the_reason():
    assert runner.describe_gpu(None).startswith("UNKNOWN")
    assert runner.describe_gpu(
        {"verdict": "WARN", "reasons": ["resident but not contending: steam (pid 1, 5670 MiB)"]}
    ) == "WARN (resident but not contending: steam (pid 1, 5670 MiB))"
    assert runner.describe_gpu({"verdict": "IDLE", "reasons": []}) == \
        "IDLE (nothing else is using the card)"


def test_a_warn_goes_straight_through(monkeypatch):
    monkeypatch.setattr(runner, "gpu_probe", lambda worktree, timeout=30, **kwargs: {"verdict": "WARN"})
    reading, waited = runner.wait_for_idle(None, {}, {})
    assert reading["verdict"] == "WARN"
    assert waited == 0.0


def test_a_busy_card_is_waited_out(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(runner.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(runner.time, "sleep", clock.sleep)
    states = [{"verdict": "BUSY"}, {"verdict": "BUSY"}, {"verdict": "IDLE"}]
    monkeypatch.setattr(runner, "gpu_probe",
                        lambda worktree, timeout=30, **kwargs: states.pop(0) if states else {"verdict": "IDLE"})
    reading, waited = runner.wait_for_idle(None, {"idle_poll_s": 10}, {})
    assert reading["verdict"] == "IDLE"
    assert waited == 20.0


def test_a_permanently_busy_card_is_run_on_anyway(monkeypatch):
    """A queue that never drains is worse than a number that says the card was busy."""
    clock = FakeClock()
    monkeypatch.setattr(runner.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(runner.time, "sleep", clock.sleep)
    monkeypatch.setattr(runner, "gpu_probe",
                        lambda worktree, timeout=30, **kwargs: {"verdict": "BUSY", "reasons": ["utilization 90%"]})
    reading, waited = runner.wait_for_idle(None, {"idle_wait_s": 60, "idle_poll_s": 15}, {})
    assert reading["verdict"] == "BUSY"
    assert waited == 60.0                      # capped by idle_wait_s, not by the poll interval


def test_the_entry_overrides_the_policy(monkeypatch):
    monkeypatch.setattr(runner, "gpu_probe", lambda worktree, timeout=30, **kwargs: {"verdict": "WARN"})
    clock = FakeClock()
    monkeypatch.setattr(runner.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(runner.time, "sleep", clock.sleep)
    reading, waited = runner.wait_for_idle(None, {"idle_wait_s": 5}, {"idle_wait_s": 600})
    assert waited == 0.0 and reading["verdict"] == "WARN"


def test_a_run_with_require_idle_records_the_card(tmp_path, monkeypatch):
    """End to end through run_request: the flag has to reach the result, not just a function."""
    worktree = tmp_path / "worktree"
    (worktree / "tools").mkdir(parents=True)
    (worktree / "tools" / "gpu_status.py").write_text(
        "import json; print(json.dumps({'verdict': 'WARN',"
        " 'reasons': ['resident but not contending: steam (pid 1, 5670 MiB)']}))\n")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    policy = {"worktree": str(worktree), "default_timeout_s": 30, "max_timeout_s": 300,
              "entries": {"demo": {"name": "demo", "argv": [sys.executable, "-c", "print('hi')"],
                                   "require_idle": True}}}
    request = {"id": "r-test", "entry": "demo", "args": [], "timeout_s": 30}
    assert runner.run_request(request, policy, worktree, run_dir) == 0
    result = json.loads((run_dir / "result.json").read_text())
    assert result["gpu_before"].startswith("WARN")
    assert result["gpu_after"].startswith("WARN")
    assert (run_dir / "report.md").read_text().count("gpu before: WARN") == 1


def test_a_run_without_require_idle_does_not_probe(tmp_path, monkeypatch):
    worktree = tmp_path / "worktree"
    (worktree / "tools").mkdir(parents=True)
    (worktree / "tools" / "gpu_status.py").write_text("raise SystemExit('should not run')\n")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    policy = {"worktree": str(worktree), "default_timeout_s": 30, "max_timeout_s": 300,
              "entries": {"demo": {"name": "demo", "argv": [sys.executable, "-c", "print('hi')"]}}}
    request = {"id": "r-test", "entry": "demo", "args": [], "timeout_s": 30}
    assert runner.run_request(request, policy, worktree, run_dir) == 0
    result = json.loads((run_dir / "result.json").read_text())
    assert result["gpu_before"] is None
    assert result["idle_waited_s"] == 0.0
