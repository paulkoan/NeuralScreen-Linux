"""check_model.py: the model directory checked the way the loader checks it.

The port reads `<dir>/model/<file>` and verifies each stage against the manifest's
sha256. When that failed on the box the console said `stage SHA-256 mismatch: stage00`,
which names the symptom and not the culprit: the loader's hashing, the extractor's
writing, or a directory holding a manifest from one run and files from another. These
tests fix what the checker has to catch, including the case that produced that message.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.opendlss_weights.check_model import check, sha256_of  # noqa: E402

SCRIPT = ROOT / "experiments" / "opendlss_weights" / "check_model.py"
REAL = Path("/opt/data/tmp/odl_model")


def build(directory: Path, stages=(b"abcd", b"efghij")) -> Path:
    """A tiny but valid model directory: two stages, tensors tiling each exactly."""
    model = directory / "model"
    model.mkdir(parents=True)
    manifest = {"totals": {"blockCount": 2, "tensorCount": 4, "stageCount": len(stages)},
                "stages": [], "tensors": []}
    for index, payload in enumerate(stages):
        sid = f"stage{index:02d}"
        (model / f"{sid}.bin").write_bytes(payload)
        manifest["stages"].append({"id": sid, "file": f"{sid}.bin",
                                   "packedByteLength": len(payload),
                                   # uppercase: what the loader's sha256Hex emits
                                   "sha256": hashlib.sha256(payload).hexdigest().upper()})
        half = len(payload) // 2
        for n, (offset, length) in enumerate(((0, half), (half, len(payload) - half))):
            manifest["tensors"].append({"name": f"b{index}.w{n}", "block": index, "layer": n,
                                        "parameter": "layer", "stage": sid,
                                        "stageOffset": offset, "byteLength": length})
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return directory


def test_a_sound_directory_passes(tmp_path):
    problems, notes = check(build(tmp_path / "m"))
    assert problems == []
    assert any("OK" in note for note in notes)


def test_the_sha256_the_extractor_wrote_is_the_one_it_wrote_to_disk(tmp_path):
    """The hashes recompute the way extract.py computes them, or the check would cry wolf.

    This is the whole question when the loader reports a mismatch: whose hash is wrong.
    """
    directory = build(tmp_path / "m")
    manifest = json.loads((directory / "manifest.json").read_text())
    for stage in manifest["stages"]:
        # hashlib's hexdigest is lowercase; the manifest holds what the loader emits.
        assert sha256_of(directory / "model" / stage["file"]).upper() == stage["sha256"]


def test_a_changed_file_is_named(tmp_path):
    """One byte is enough — and same length, so the size check cannot catch it."""
    directory = build(tmp_path / "m")
    path = directory / "model" / "stage00.bin"
    path.write_bytes(b"abce" + path.read_bytes()[4:])
    problems, _ = check(directory)
    assert len(problems) == 1
    assert "stage00" in problems[0] and "does not match its manifest hash" in problems[0]


def test_a_truncated_file_is_named(tmp_path):
    directory = build(tmp_path / "m")
    (directory / "model" / "stage01.bin").write_bytes(b"ef")
    problems, _ = check(directory)
    assert any("holds 2 bytes" in problem for problem in problems)


def test_a_missing_stage_is_named(tmp_path):
    directory = build(tmp_path / "m")
    (directory / "model" / "stage01.bin").unlink()
    problems, _ = check(directory)
    assert any("no " in problem and "stage01" in problem for problem in problems)


def test_tensors_that_do_not_tile_their_stage_are_named(tmp_path):
    """Offsets are the only thing that says which bytes are which weight."""
    directory = build(tmp_path / "m")
    manifest = json.loads((directory / "manifest.json").read_text())
    manifest["tensors"][1]["stageOffset"] = 3          # a gap where byte 2 should be
    (directory / "manifest.json").write_text(json.dumps(manifest))
    problems, _ = check(directory)
    assert any("gap" in problem for problem in problems)


def test_a_tensor_running_past_its_stage_is_named(tmp_path):
    directory = build(tmp_path / "m")
    manifest = json.loads((directory / "manifest.json").read_text())
    manifest["tensors"][0]["byteLength"] = 999
    (directory / "manifest.json").write_text(json.dumps(manifest))
    problems, _ = check(directory)
    assert any("runs past" in problem for problem in problems)


def test_a_directory_without_a_manifest_says_so(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    problems, _ = check(empty)
    assert problems and "no manifest.json" in problems[0]


def test_the_command_exits_nonzero_and_prints_the_remedy(tmp_path):
    """The output is read while something is broken, so it has to carry the next command."""
    directory = build(tmp_path / "m")
    (directory / "model" / "stage00.bin").write_bytes(b"zzzz")
    result = subprocess.run([sys.executable, str(SCRIPT), str(directory)],
                            capture_output=True, text=True)
    assert result.returncode == 1
    assert "stage00" in result.stderr
    assert "extract.py --out" in result.stderr, "say how to fix it, not only what is wrong"

    ok = subprocess.run([sys.executable, str(SCRIPT), str(directory.parent / "nope")],
                        capture_output=True, text=True)
    assert ok.returncode == 2


@pytest.mark.skipif(not REAL.is_dir(), reason="no extraction on this box to check")
def test_the_extraction_this_box_holds_is_sound():
    """Our own extractor's output, against the checks the loader makes of it."""
    problems, notes = check(REAL)
    assert problems == [], problems
    assert any("71 blocks" in note for note in notes)

def test_a_lowercase_manifest_is_caught_before_the_loader_sees_it(tmp_path):
    """The mismatch that cost a run, in the shape it arrived in.

    The loader's sha256Hex formats with "0123456789ABCDEF" and Model compares the strings
    exactly. hashlib's hexdigest is lowercase, so a manifest written that way describes the
    bytes correctly and still fails with `stage SHA-256 mismatch` — the message that names
    a stage and no reason. The checker has to say which of the two it is.
    """
    directory = build(tmp_path / "m")
    manifest = json.loads((directory / "manifest.json").read_text())
    for stage in manifest["stages"]:
        stage["sha256"] = stage["sha256"].lower()
    (directory / "manifest.json").write_text(json.dumps(manifest))
    problems, _ = check(directory)
    assert problems and all("case" in problem for problem in problems), problems


def test_the_loaders_own_hash_is_what_the_manifest_must_match(tmp_path):
    """Compiled from the port's src/sha256.h, as the model loader calls it.

    This is the check that found the bug: the loader emits uppercase, the extractor wrote
    lowercase, and nothing else in the project could have noticed, because both sides agree
    with themselves. Skipped where the port's sources are not on this machine.
    """
    compiler = shutil.which("g++")
    sources = [Path(os.environ.get("NS_ODL_SRC", ".")),
               Path.home() / "dev" / "OpenDLSS-NR",
               Path("/opt/data/tmp/odl-src")]
    header = next((p / "src" / "sha256.h" for p in sources if (p / "src" / "sha256.h").is_file()), None)
    if compiler is None or header is None:
        pytest.skip("needs a C++ compiler and the port's src/sha256.h")

    program = tmp_path / "hash.cpp"
    program.write_text(
        '#include <cstdio>\n#include <fstream>\n#include <iterator>\n#include <string>\n'
        '#include "sha256.h"\n'
        'int main(int c, char** v) { std::ifstream in(v[1], std::ios::binary);'
        ' std::string b((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());'
        ' std::string hex = sha256Hex((const uint8_t*)b.data(), b.size());'
        ' printf("%s %s\\n", hex.c_str(), hex.c_str() + 16); return 0; }\n')
    binary = tmp_path / "hash"
    built = subprocess.run([compiler, "-std=c++20", "-O2", f"-I{header.parent}", str(program),
                            "-o", str(binary)], capture_output=True, text=True)
    assert built.returncode == 0, built.stderr

    # A known vector, and the real thing: 5 MB of stage file, where a chunking bug lives.
    stage = REAL / "model" / "stage00.bin" if REAL.is_dir() else None
    probe = tmp_path / "probe.bin"
    payload = probe if stage is None else stage
    if stage is None:
        probe.write_bytes(b"abc")

    got = subprocess.run([str(binary), str(payload)], capture_output=True, text=True).stdout.split()
    expect = hashlib.sha256(payload.read_bytes()).hexdigest()
    assert got[0] == expect.upper(), "the loader's hex is uppercase and nothing else will match"
    if stage is not None:
        manifest = json.loads((REAL / "manifest.json").read_text())
        assert manifest["stages"][0]["sha256"] == got[0], (
            "our manifest does not match what the loader computes for the same bytes")
