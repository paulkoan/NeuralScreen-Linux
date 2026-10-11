"""Check a model directory the way the port's loader will, without a GPU.

    uv run python experiments/opendlss_weights/check_model.py /home/paul/dev/odl-model

The model directory is the one input to this path nobody can look at: it comes out of
NVIDIA's DLL through `extract.py`, and the port reads `<dir>/model/<file>` and checks each
stage against the manifest's sha256. When that check fails on the box —

    serve: stage SHA-256 mismatch: stage00

— there are two possible culprits and only one of them is the loader. This decides which,
by recomputing the hashes the way `extract.py` wrote them, and by checking the structural
claims the manifest makes about itself: that every tensor lies inside its stage, and that
the tensors of a stage tile it exactly, with no gap and no overlap.

It needs no device, so it can be run before a pipeline run rather than after a puzzling
one. Exit status is 0 when the directory is sound.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check(directory: Path, dll: Path | None = None) -> tuple[list[str], list[str]]:
    """(problems, notes): what is wrong, and what was checked and found right."""
    problems: list[str] = []
    notes: list[str] = []

    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        return [f"no manifest.json in {directory}"], notes
    try:
        manifest = json.loads(manifest_path.read_text())
    except ValueError as error:
        return [f"manifest.json is not JSON: {error}"], notes

    for key in ("totals", "stages", "tensors"):
        if key not in manifest:
            problems.append(f"manifest.json has no \"{key}\"")
    if problems:
        return problems, notes

    totals = manifest["totals"]
    notes.append(f"manifest: {totals.get('blockCount')} blocks, "
                 f"{totals.get('tensorCount')} tensors, {totals.get('stageCount')} stages")

    sizes: dict[str, int] = {}
    for stage in manifest["stages"]:
        sid, name = stage["id"], stage["file"]
        path = directory / "model" / name
        if not path.is_file():
            problems.append(f"{sid}: no {path}")
            continue
        size = path.stat().st_size
        sizes[sid] = size
        if size != stage["packedByteLength"]:
            problems.append(f"{sid}: {path} holds {size} bytes, the manifest says "
                            f"{stage['packedByteLength']}")
            continue
        digest = sha256_of(path)
        # The loader's sha256Hex formats with "0123456789ABCDEF" — uppercase — and Model
        # compares the two strings exactly. So an uppercase manifest is what it accepts, and
        # a lowercase one (hashlib's hexdigest, which is what extract.py used to write)
        # describes the bytes correctly and is still rejected with `stage SHA-256 mismatch`.
        # That message names a stage and no reason, so the checker gives the reason.
        if digest.upper() != stage["sha256"]:
            if digest.upper().lower() == stage["sha256"].lower():
                problems.append(f"{sid}: the manifest stores the hash in lowercase, and the "
                                f"loader's sha256Hex emits uppercase and compares exactly — "
                                f"it will reject this stage (re-run extract.py, which writes "
                                f"uppercase)")
            else:
                problems.append(f"{sid}: {path} does not match its manifest hash "
                                f"(file {digest[:16]}…, manifest {stage['sha256'][:16]}…)")
        else:
            notes.append(f"{sid}: {size:>10d} bytes, sha256 {digest[:16]}… OK")

    # Every tensor has to lie inside its stage, and the tensors of a stage have to tile it
    # exactly: the offsets are the only thing that says which bytes are which weight, so a
    # gap is as bad as an overlap.
    by_stage: dict[str, list[tuple[int, int, str]]] = {}
    for tensor in manifest["tensors"]:
        sid, offset, length = tensor["stage"], tensor["stageOffset"], tensor["byteLength"]
        if sid not in sizes:
            problems.append(f"tensor {tensor['name']!r} claims stage {sid}, which is not in "
                            f"the manifest or did not load")
            continue
        if offset < 0 or length <= 0 or offset + length > sizes[sid]:
            problems.append(f"tensor {tensor['name']!r} runs past {sid}: offset {offset} + "
                            f"{length} bytes against a stage of {sizes[sid]}")
        by_stage.setdefault(sid, []).append((offset, length, tensor["name"]))

    for sid, entries in sorted(by_stage.items()):
        entries.sort()
        cursor = 0
        for offset, length, name in entries:
            if offset != cursor:
                problems.append(f"{sid}: {name!r} starts at {offset}, the previous tensor "
                                f"ends at {cursor} ({'gap' if offset > cursor else 'overlap'})")
            cursor = max(cursor, offset + length)
        if sid in sizes and cursor != sizes[sid]:
            problems.append(f"{sid}: its tensors cover {cursor} of {sizes[sid]} bytes")

    if dll is not None:
        if dll.is_file():
            notes.append(f"dll: {dll} is {dll.stat().st_size} bytes, sha256 "
                         f"{sha256_of(dll)[:16]}…")
        else:
            problems.append(f"no DLL at {dll}")

    covered = len(by_stage)
    notes.append(f"tensors: {len(manifest['tensors'])} over {covered} stage(s), all inside "
                 f"their stage and tiling it exactly" if not problems else
                 f"tensors: {len(manifest['tensors'])} over {covered} stage(s)")
    return problems, notes


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="check_model.py", description=__doc__.split("\n")[0])
    parser.add_argument("directory", help="the model directory the port is pointed at")
    parser.add_argument("--dll", help="also report this DLL's size and hash, for comparing "
                                      "two extractions of different builds")
    args = parser.parse_args(argv)

    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"not a directory: {directory}", file=sys.stderr)
        return 2
    problems, notes = check(directory, Path(args.dll) if args.dll else None)
    for line in notes:
        print(f"  {line}")
    if not problems:
        print(f"{directory}: sound — the loader will accept it")
        return 0
    print(f"{directory}: {len(problems)} problem(s)", file=sys.stderr)
    for line in problems:
        print(f"  {line}", file=sys.stderr)
    print("A file that does not match its manifest means the directory holds a manifest "
          "and stage files from different runs. Re-extract into an empty directory rather "
          "than over the old one:\n"
          f"  rm -rf {directory} && uv run python experiments/opendlss_weights/extract.py "
          f"--out {directory}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))