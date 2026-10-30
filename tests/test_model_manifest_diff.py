"""The manifest diff must tell "same network" apart from "different network, same shape".

This is the question the 310.9.16 DLL forces: extract.py cuts the largest resource, and a
byte-identical copy of the old network passes every check the old one does. The manifest hashes
are the only cheap discriminator, so the exit code has to mean something.
"""
import importlib.util
import json
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "model_manifest_diff.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("model_manifest_diff", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_manifest(path: Path, stage_hashes: list[str], names: list[str],
                   lengths: list[int] | None = None) -> Path:
    lengths = lengths or [100] * len(names)
    manifest = {
        "totals": {"blockCount": 71, "tensorCount": len(names), "stageCount": len(stage_hashes)},
        "fieldSplit": 28,
        "stages": [{"id": f"stage{i:02d}", "file": f"stage{i:02d}.bin",
                    "packedByteLength": 10, "sha256": sha}
                   for i, sha in enumerate(stage_hashes)],
        "tensors": [{"name": name, "block": 0, "layer": "layer0", "parameter": "layer",
                     "stage": "stage00", "stageOffset": 0, "byteLength": length}
                    for name, length in zip(names, lengths)],
    }
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path


def run(*args):
    import subprocess
    import sys
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, timeout=60)


def test_same_bytes_exits_zero(tmp_path):
    names = ["block0.layer0.layer", "block1.layer0.layer"]
    hashes = ["A" * 64, "B" * 64]
    old = write_manifest(tmp_path / "old.json", hashes, names)
    new = write_manifest(tmp_path / "new.json", hashes, names)
    done = run("--old", str(old), "--new", str(new))
    assert done.returncode == 0, done.stdout + done.stderr
    assert "SAME BYTES" in done.stdout


def test_different_bytes_same_structure_exits_one(tmp_path):
    names = ["block0.layer0.layer", "block1.layer0.layer"]
    old = write_manifest(tmp_path / "old.json", ["A" * 64, "B" * 64], names)
    new = write_manifest(tmp_path / "new.json", ["C" * 64, "B" * 64], names)
    done = run("--old", str(old), "--new", str(new))
    assert done.returncode == 1, done.stdout + done.stderr
    assert "DIFFERENT BYTES, SAME STRUCTURE" in done.stdout
    assert "first at stage00" in done.stdout


def test_different_structure_exits_one(tmp_path):
    old = write_manifest(tmp_path / "old.json", ["A" * 64], ["block0.layer0.layer"])
    new = write_manifest(tmp_path / "new.json", ["A" * 64], ["block0.layer0.other"])
    done = run("--old", str(old), "--new", str(new))
    assert done.returncode == 1, done.stdout + done.stderr
    assert "STRUCTURE DIFFERS" in done.stdout


def test_a_missing_manifest_is_refused(tmp_path):
    old = write_manifest(tmp_path / "old.json", ["A" * 64], ["block0.layer0.layer"])
    done = run("--old", str(old), "--new", str(tmp_path / "nope.json"))
    assert done.returncode == 2
    assert "could not read a manifest" in done.stderr