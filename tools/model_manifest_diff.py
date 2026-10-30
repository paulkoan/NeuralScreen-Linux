#!/usr/bin/env python3
"""Say whether an extracted model is the network already in use, or a different one.

The 310.9.16 DLL carries two networks. `extract.py` takes the largest resource in the file, so it
almost certainly cuts the old one - and "the check passed" does not distinguish the two: a
byte-identical copy of the old network passes every check the old one does. The discriminator is
the manifest: compare the stage hashes against the directory the port loads today. Identical
hashes mean nothing new was extracted; different hashes with the same stage/tensor structure mean
the new network is shader-compatible and porting is a weight swap; a different structure means
shader work.

    tools/model_manifest_diff.py --dll native/nvngx_dlssnr.dll \
        --old /opt/neuralscreen/model --new /tmp/model-310.9.16

Exit codes:
  0  the manifests describe the same bytes (the extraction found the network already in use)
  1  the manifests describe different bytes (a genuinely different network)
  2  a manifest or the DLL could not be read
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXTRACT = REPO / "experiments" / "opendlss_weights" / "extract.py"


def load_extract():
    spec = importlib.util.spec_from_file_location("opendlss_extract", EXTRACT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def describe(path: Path) -> dict:
    if path.is_dir():
        path = path / "manifest.json"
    manifest = json.loads(path.read_text())
    totals = manifest.get("totals", {})
    return {
        "dir": str(path.parent),
        "blockCount": totals.get("blockCount"),
        "tensorCount": totals.get("tensorCount", len(manifest.get("tensors", []))),
        "stageCount": totals.get("stageCount", len(manifest.get("stages", []))),
        "fieldSplit": manifest.get("fieldSplit"),
        "stages": manifest.get("stages", []),
        "tensors": manifest.get("tensors", []),
    }


def structure_matches(old: dict, new: dict) -> bool:
    """Same partition: same stage count and the same tensor names in the same order."""
    if old["stageCount"] != new["stageCount"]:
        return False
    if [t["name"] for t in old["tensors"]] != [t["name"] for t in new["tensors"]]:
        return False
    if [t.get("byteLength") for t in old["tensors"]] != [t.get("byteLength") for t in new["tensors"]]:
        return False
    return True


def hashes_match(old: dict, new: dict) -> bool:
    return [s.get("sha256") for s in old["stages"]] == [s.get("sha256") for s in new["stages"]]


def list_leaves(dll: Path, limit: int = 8) -> None:
    """The largest resources in the DLL, which is how extract.py chooses its blob."""
    module = load_extract()
    data = dll.read_bytes()
    leaves = sorted(module.resource_leaves(data), key=lambda leaf: -leaf[2])
    print(f"dll: {dll} ({len(data):,} bytes); weight-table magic {module.MAGIC:#010x}")
    print(f"{'size':>14}  {'offset':>14}  {'magic':>12}  path")
    for path, off, size, _ in leaves[:limit]:
        magic = struct.unpack_from("<I", data, off)[0]
        marker = "  <- weight table" if magic == module.MAGIC else ""
        print(f"{size:>14,}  {off:>14,}  {magic:#012x}  {'/'.join(map(str, path))}{marker}")
    total_magic = sum(1 for _, off, _, _ in leaves
                      if struct.unpack_from("<I", data, off)[0] == module.MAGIC)
    print(f"{total_magic} resource(s) carry the weight-table magic; extract.py takes the largest")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "compare model manifests").split("\n")[0])
    ap.add_argument("--old", required=True,
                    help="model directory or manifest.json of the model in use today")
    ap.add_argument("--new", required=True,
                    help="model directory or manifest.json of the freshly extracted model")
    ap.add_argument("--dll", help="also list this DLL's largest resources (optional)")
    args = ap.parse_args(argv)
    if args.dll:
        list_leaves(Path(args.dll))
        print()

    try:
        old = describe(Path(args.old))
        new = describe(Path(args.new))
    except (OSError, json.JSONDecodeError) as error:
        print(f"could not read a manifest: {error}", file=sys.stderr)
        return 2

    print(f"old  {old['dir']}")
    print(f"     blocks {old['blockCount']}, tensors {old['tensorCount']}, "
          f"stages {old['stageCount']}, fieldSplit {old['fieldSplit']}")
    print(f"new  {new['dir']}")
    print(f"     blocks {new['blockCount']}, tensors {new['tensorCount']}, "
          f"stages {new['stageCount']}, fieldSplit {new['fieldSplit']}")
    print()

    same_structure = structure_matches(old, new)
    same_bytes = hashes_match(old, new)

    if not same_structure:
        print("STRUCTURE DIFFERS - the port's shaders/loader would need work:")
        if old["stageCount"] != new["stageCount"]:
            print(f"  stage count {old['stageCount']} -> {new['stageCount']}")
        old_names = [t["name"] for t in old["tensors"]]
        new_names = [t["name"] for t in new["tensors"]]
        if old_names != new_names:
            first = next((i for i, (a, b) in enumerate(zip(old_names, new_names)) if a != b),
                         min(len(old_names), len(new_names)))
            print(f"  first tensor name difference at {first}: "
                  f"{old_names[first] if first < len(old_names) else '(none)'} -> "
                  f"{new_names[first] if first < len(new_names) else '(none)'}")
        if [t.get("byteLength") for t in old["tensors"]] != [t.get("byteLength") for t in new["tensors"]]:
            print("  tensor byte lengths differ")
        return 1

    if same_bytes:
        print("SAME BYTES: this extraction found the network already in use. "
              "Nothing new was cut; the second network is a separate resource.")
        return 0

    print("DIFFERENT BYTES, SAME STRUCTURE: this is a different network that the port's "
          "loader can accept as a drop-in weight swap.")
    changed = [i for i, (a, b) in enumerate(zip(old["stages"], new["stages"]))
               if a.get("sha256") != b.get("sha256")]
    print(f"  {len(changed)} of {len(old['stages'])} stages differ; first at stage{changed[0]:02d}"
          if changed else "  no stage differs")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))