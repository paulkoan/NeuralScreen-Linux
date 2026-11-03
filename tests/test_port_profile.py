"""tools/port_profile.sh: the per-dispatch timing route, and what it insists on saying.

The port's pass is 12.0-13.5 ms at 2560x1440 against NGX's 7.1 ms, and the port can already
break that down by dispatch. This tool is only a way to run that from the runner, so the tests
are about the two things that would make it useless: running it against the wrong binary, or
against nothing at all and reporting success.
"""
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "port_profile.sh"


def test_the_tool_is_where_the_entry_point_will_look_for_it():
    assert TOOL.exists(), "the policy entry names this path"
    assert os.access(TOOL, os.X_OK), "committed without the executable bit"


def test_the_script_parses():
    out = subprocess.run(["bash", "-n", str(TOOL)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr


def test_a_missing_port_binary_is_refused_not_profiled():
    """No binary means no number: exit non-zero and say which path was tried."""
    out = subprocess.run(["bash", str(TOOL)], capture_output=True, text=True,
                         env={**os.environ,
                              "NEURALSCREEN_PORT_BIN": "/nonexistent/dlss5vk"})
    assert out.returncode != 0
    assert "/nonexistent/dlss5vk" in out.stderr


def test_a_missing_model_is_refused_too():
    """A profile with no weights would report an empty graph as a fast one."""
    bin_dir = REPO / "cache" / "scratch"
    fake = bin_dir / "fake-dlss5vk"
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake.write_text("#!/bin/bash\necho SHOULD-NOT-RUN\n")
    fake.chmod(0o755)
    try:
        out = subprocess.run(["bash", str(TOOL)], capture_output=True, text=True,
                             env={**os.environ,
                                  "NEURALSCREEN_PORT_BIN": str(fake),
                                  "NEURALSCREEN_MODEL_DIR": "/nonexistent/model"})
        assert out.returncode != 0
        assert "SHOULD-NOT-RUN" not in out.stdout, "the binary must not have been launched"
    finally:
        fake.unlink(missing_ok=True)


def test_the_readme_for_the_box_note_says_what_it_needs():
    """The entry point is the user's call and is not in this repo, so the file has to say so."""
    text = TOOL.read_text()
    assert "policy" in text.lower() and "port-profile" in text
    assert "must not be compared" in text, (
        "the profile route runs with barriers, so its total is not a frame time; a reader who "
        "takes it for one will chase the wrong number")