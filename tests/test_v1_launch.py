"""v1: the app runs the native port, and the launcher refuses to start without its parts.

main_linux.py was written against the Wine/NGX worker and hard-coded native/run_worker.sh, so
the port - which is what v1 ships - could not be started from the app at all. NS_WORKER_CMD is
the switch. These tests pin the switch, the shipped config, and the launcher's refusals: a
launcher that starts with no binary and then fails somewhere deeper costs a debugging session.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
from pathlib import Path

import pytest

import pipeline_linux

REPO = Path(__file__).resolve().parent.parent
LAUNCHER = REPO / "neuralscreen.sh"
CONFIG = REPO / "config.v1.json"


class _FakeProc:
    def __init__(self, cmd, **kwargs):
        self.cmd = cmd
        self.kwargs = kwargs
        self.pid = 4242
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO()
        self.stderr = io.BytesIO()

    def poll(self):
        return None


class _FakeReader:
    def __init__(self, *args, **kwargs):
        pass


@pytest.fixture
def captured(monkeypatch):
    """Record the argv start_worker launches, without launching anything."""
    seen = {}

    def fake_popen(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["env"] = kwargs.get("env", {})
        return _FakeProc(cmd, **kwargs)

    monkeypatch.setattr(pipeline_linux.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(pipeline_linux, "WorkerReader", _FakeReader)
    monkeypatch.setattr(pipeline_linux, "_negotiate_shm", lambda *a, **k: None)
    return seen


PARAMS = {"profile": 1, "preset": 0, "style": 1, "auto_mask": 0, "ui_correction": 0,
          "intensity": 1.0, "local_tone": 1.0, "local_structure": 1.0, "skin_structure": -1.0}


def test_the_port_is_launched_when_ns_worker_cmd_says_so(captured, monkeypatch):
    monkeypatch.setenv("NS_WORKER_CMD", "/opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model")
    pipeline_linux.start_worker(PARAMS, 2560, 1440, 2)
    assert captured["cmd"][0] == "/opt/neuralscreen/port/build/dlss5vk"
    assert captured["cmd"][1] == "serve"
    assert "--model" in captured["cmd"]


def test_the_wine_launcher_is_still_the_default(captured, monkeypatch):
    monkeypatch.delenv("NS_WORKER_CMD", raising=False)
    pipeline_linux.start_worker(PARAMS, 2560, 1440, 2)
    assert captured["cmd"][0] == "bash"
    assert captured["cmd"][1].endswith("run_worker.sh")


def test_an_empty_override_is_refused(captured, monkeypatch):
    monkeypatch.setenv("NS_WORKER_CMD", "   ")
    with pytest.raises(ValueError):
        pipeline_linux.start_worker(PARAMS, 2560, 1440, 2)


def test_the_header_still_goes_out(captured, monkeypatch):
    """The port speaks the same header; a launch that skips it would hang on the first frame."""
    monkeypatch.setenv("NS_WORKER_CMD", "/bin/true serve")
    worker, logs, reader, stop = pipeline_linux.start_worker(PARAMS, 2560, 1440, 2)
    assert worker.stdin.getvalue(), "the stream header must be written before any frame"


def test_the_shipped_config_loads():
    from settings_io import load_config
    cfg = load_config(CONFIG)
    assert cfg["width"] == 2560 and cfg["height"] == 1440
    assert cfg["capture_in_worker"] is False, "the port has no desktop-duplication path"
    assert cfg["pixels_in_shm"] is True
    assert cfg["work_scale"] == 1.0


def test_the_config_is_valid_json_with_no_duplicate_keys():
    text = CONFIG.read_text()
    assert json.loads(text)["width"] == 2560


def test_the_launcher_is_executable_and_parses():
    assert LAUNCHER.exists()
    assert os.access(LAUNCHER, os.X_OK), "committed without the executable bit"
    out = subprocess.run(["bash", "-n", str(LAUNCHER)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr


def test_the_launcher_refuses_without_a_port_binary():
    out = subprocess.run(["bash", str(LAUNCHER)], capture_output=True, text=True,
                         env={**os.environ, "NEURALSCREEN_PORT_BIN": "/nonexistent/dlss5vk",
                              "DISPLAY": ":0"})
    assert out.returncode != 0
    assert "/nonexistent/dlss5vk" in out.stderr


def test_the_launcher_refuses_without_a_display(tmp_path):
    """The checks run in order, so this one needs the earlier ones satisfied to be reached."""
    fake_bin = tmp_path / "dlss5vk"
    fake_bin.write_text("#!/bin/bash\nexit 0\n")
    fake_bin.chmod(0o755)
    model = tmp_path / "model"
    model.mkdir()
    out = subprocess.run(["bash", str(LAUNCHER)], capture_output=True, text=True,
                         env={**{k: v for k, v in os.environ.items()
                                  if k not in ("DISPLAY", "WAYLAND_DISPLAY")},
                              "NEURALSCREEN_PORT_BIN": str(fake_bin),
                              "NEURALSCREEN_MODEL_DIR": str(model)})
    assert out.returncode != 0
    assert "WAYLAND_DISPLAY" in out.stderr or "DISPLAY" in out.stderr


def test_the_v1_hotkeys_parse_and_do_not_need_a_numpad():
    """A laptop has no keypad, and an override that fails to parse is dropped in silence."""
    from hotkeys import build_bindings, parse_binding

    cfg = json.loads(CONFIG.read_text())
    overrides = cfg["hotkeys"]
    for command, combo in overrides.items():
        assert parse_binding(combo) is not None, f"{command}: {combo!r} does not parse"

    bindings = build_bindings(overrides)
    by_command = {entry[2]: entry[3] for entry in bindings.values()}
    assert by_command["window"] == "Ctrl+Alt+5"
    assert by_command["toggle"] == "Ctrl+Alt+1"
    assert by_command["quit"] == "Ctrl+Alt+Q"


def test_the_parser_knows_the_top_row_digits_and_letters():
    """The gap that made every non-numpad rebind fail silently."""
    from hotkeys import parse_binding

    assert parse_binding("Ctrl+Alt+5") == (12, 0x35)
    assert parse_binding("Ctrl+Alt+Z") == (12, 0x7A)
    assert parse_binding("F5") is not None
