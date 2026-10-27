"""check_history_sample.py: the demo's reprojection and five-tap filter, checked as arithmetic.

`serve`'s composite samples the history at the pixel itself, and the patch's header says why:
no motion is handed to it. That is honest only while the demo's own reprojection and filter
reduce to it when the field is zero — and that reduction is the thing worth a checker, because
it is the whole justification for the simpler expression that ships. HISTORY.md is what the
definition is; this is where the definition's arithmetic is checked rather than asserted.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PORT = ROOT / "experiments" / "opendlss_port"
SCRIPT = PORT / "check_history_sample.py"
DEFINITION = PORT / "HISTORY.md"
PATCH = PORT / "linux-port.patch"

ORIGINALS = ("demo/shaders/nr_common.glsl", "demo/shaders/velocity_unpack.comp",
             "demo/shaders/nr_composite.comp")
CHECKOUTS = [os.environ.get("NS_ODL_SRC"), "/opt/neuralscreen/port",
             str(Path.home() / "dev" / "OpenDLSS-NR"), "/opt/data/tmp/odl-src"]


def original() -> Path | None:
    for candidate in CHECKOUTS:
        if candidate and all((Path(candidate) / name).is_file() for name in ORIGINALS):
            return Path(candidate)
    return None


def run(*arguments) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *[str(a) for a in arguments]],
                          capture_output=True, text=True)


def test_the_definition_is_written_down_and_names_its_source():
    """The definition exists as a document, and it says which commit it came out of.

    A definition nobody can find is the reinvented one this card was opened to avoid, so the
    file has to exist, quote the filter it defines, and name the original's commit and paths.
    """
    assert DEFINITION.exists(), "the demo's filter and reprojection are written down somewhere"
    text = DEFINITION.read_text()
    assert "9d08f41" in text, "the commit the port's stamp names"
    assert "nr_common.glsl" in text and "velocity_unpack.comp" in text, "the sources, by path"
    assert "historySample(" in text and "historyUv(" in text, "quoted, not paraphrased"
    assert "five-tap" in text and "bilinear-weight trick" in text
    assert "check_history_sample.py" in text, "and the arithmetic that backs it, named"


def test_the_history_sample_is_checked_against_the_original():
    """Green, and it says what it read: the original, its files, and each claim as it goes."""
    assert SCRIPT.exists(), "the definition's arithmetic is checked, not asserted"
    source = SCRIPT.read_text()
    assert "nr_common.glsl" in source and "velocity_unpack.comp" in source, "both sources, named"
    assert "sha256" in source, "pinned: a shader that has moved is not the original"
    assert "linux-port.patch" in source, "and what ships is read too, not restated"

    pytest.importorskip("numpy")
    checkout = original()
    if checkout is None:
        pytest.skip("no checkout of the original on this machine")

    finished = run(checkout)
    assert finished.returncode == 0, finished.stdout + finished.stderr
    # One per claim: the files, the weights, the five taps, zero motion, the reprojection.
    assert finished.stdout.count("agree") >= 5, finished.stdout
    assert str(checkout) in finished.stdout, "it has to say which original it read"
    assert "zero motion" in finished.stdout and "reprojection" in finished.stdout


def test_the_check_refuses_an_original_that_moved():
    """A shader that is not the pinned one is not the definition.

    The pin is the file's bytes, so an edit anywhere in it — a comment included — has to be
    refused rather than transliterated: a checker that reads a modified copy is checking
    something nobody can name.
    """
    checkout = original()
    if checkout is None:
        pytest.skip("no checkout of the original on this machine")
    assert checkout is not None

    with tempfile.TemporaryDirectory() as tmp:
        moved = Path(tmp)
        for name in ORIGINALS:
            target = moved / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(checkout / name, target)
        shader = moved / "demo" / "shaders" / "nr_common.glsl"
        shader.write_text(shader.read_text() + "\n// and a harmless comment\n")

        finished = run(moved)
    assert finished.returncode == 2, finished.stdout + finished.stderr
    assert "not the original" in finished.stdout, finished.stdout


def test_the_history_check_can_fail():
    """And the arithmetic has to be able to disagree, or it is a checker that passes on anything.

    The definition is four weights and a grouping of them. Move one weight — the `w3` coefficient
    by a factor of two — and the four stop being the kernel's, which is the first thing the check
    claims, so it has to refuse with a DIFFER rather than pass over it.
    """
    checkout = original()
    if checkout is None:
        pytest.skip("no checkout of the original on this machine")
    pytest.importorskip("numpy")

    source = SCRIPT.read_text()
    coefficient = "w3 = f32(f32(cube - square) * f32(0.5))"
    assert coefficient in source, "the w3 coefficient moved; update this test with it"
    with tempfile.TemporaryDirectory() as tmp:
        broken = Path(tmp) / "check_history_sample.py"
        broken.write_text(source.replace(coefficient, "w3 = f32(f32(cube - square) * f32(0.25))"))
        finished = subprocess.run([sys.executable, str(broken), str(checkout), str(PATCH)],
                                  capture_output=True, text=True)
    assert finished.returncode == 1, finished.stdout + finished.stderr
    assert "DIFFER" in finished.stdout, finished.stdout
