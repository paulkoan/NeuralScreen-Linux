"""Check a model directory the way the port's loader will, without a GPU.

    uv run python experiments/opendlss_weights/check_model.py /home/paul/dev/odl-model
    uv run python experiments/opendlss_weights/check_model.py /home/paul/dev/odl-model \
        --dll native/nvngx_dlssnr.dll

The model directory is the one input to this path nobody can look at: it comes out of
NVIDIA's DLL through `extract.py`, and the port reads `<dir>/model/<file>` and checks each
stage against the manifest's sha256. When that check fails on the box —

    serve: stage SHA-256 mismatch: stage00

— there are two possible culprits and only one of them is the loader. This decides which,
by recomputing the hashes the way `extract.py` wrote them, and by checking the structural
claims the manifest makes about itself: that every tensor lies inside its stage, and that
the tensors of a stage tile it exactly, with no gap and no overlap.

Those are all checks of shape, and shape cannot see a payload cut at the wrong offset: a
directory extracted that way still tiles its stages exactly and still hashes to its own
manifest. That is how a whole model ran on shifted weights and diverged on them. So the
directory's numbers are checked too, against content known independently of the manifest —
`block70.layer0.blend_scale`, which docs/frame.md documents as 0.7397 and which reads
0.73975 as f16. A payload 12 bytes late reads 0.0 there instead, the first two bytes of the
record's trailer. With `--dll` the comparison is made for all 153 tensors, byte for byte,
against the weight table in the DLL itself.

It needs no device, so it can be run before a pipeline run rather than after a puzzling
one. Exit status is 0 when the directory is sound.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# Values whose expected content is known independently of the directory being checked, so a
# check on them is a check on the weights and not on the manifest's agreement with its own
# files. A shifted payload satisfies every structural check — all of the candidate field
# splits tile the stage exactly — which is what made the 40-byte reading cost a model.
#
#   (tensor name, bytes wide, expected value, where the expectation comes from)
PINNED_VALUES = (
    ("block70.layer0.blend_scale", 2, 0.73975,
     "docs/frame.md documents block70.layer0.blend_scale as 0.7397 in the shipped model"),
)
# An f16 carries about three decimal digits, so a value check on one compares at 1e-3.
TOLERANCE = {2: 1e-3, 4: 1e-6}


def read_tensor(path: Path, tensor: dict) -> bytes:
    """The bytes a manifest record points at, straight out of its stage file."""
    with path.open("rb") as handle:
        handle.seek(tensor["stageOffset"])
        return handle.read(tensor["byteLength"])


def dll_payloads(dll: Path, fields: int) -> dict[str, bytes]:
    """Every record's payload, read from the DLL's own weight table.

    `extract.py`'s reader, loaded from beside this file, so the two tools cannot drift: what
    this calls a record's payload is what the extractor cut the directory with. The DLL is
    the expected content itself — the only copy of the weights that is independent of the
    manifest, which agrees with the directory whatever bytes the directory holds.
    """
    spec = importlib.util.spec_from_file_location(
        "opendlss_weights_extract", Path(__file__).resolve().with_name("extract.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = dll.read_bytes()
    offset, size = module.find_weight_blob(data)
    blob = data[offset:offset + size]
    return {record["name"]: blob[record["payload_offset"]:record["payload_offset"]
                                 + record["byteLength"]]
            for record in module.parse_records(blob, fields)}


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
    files: dict[str, str] = {}
    for stage in manifest["stages"]:
        sid, name = stage["id"], stage["file"]
        files[sid] = name
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

    # The values themselves. Everything above is a statement about shape, and a directory
    # whose payloads start 12 bytes into each record's trailer satisfies all of it. These are
    # the checks that read the weights and compare them with what they should be.
    for name, width, expected, source in PINNED_VALUES:
        tensor = next((t for t in manifest["tensors"] if t["name"] == name), None)
        if tensor is None:
            notes.append(f"pinned: the manifest has no {name!r} to compare against "
                         f"{source}")
            continue
        if tensor["stage"] not in files:
            continue                       # the stage is already reported as a problem
        path = directory / "model" / files[tensor["stage"]]
        if not path.is_file():
            continue                       # ditto
        if tensor["byteLength"] != width:
            problems.append(f"{name}: the record declares {tensor['byteLength']} bytes, and "
                            f"{source} — the value is {width} bytes wide, so this payload "
                            f"cannot be it")
            continue
        raw = read_tensor(path, tensor)
        if len(raw) != width:
            continue                       # a short file is reported by the size check
        value = struct.unpack("<e" if width == 2 else "<f", raw)[0]
        if abs(value - expected) > TOLERANCE[width]:
            problems.append(f"{name}: reads {value!r} ({raw.hex()}) at {tensor['stage']}"
                            f"+{tensor['stageOffset']}, where {source} — the payload should "
                            f"read {expected!r} ({struct.pack('<e' if width == 2 else '<f', expected).hex()}), "
                            f"so it does not start where the manifest says: a payload 12 "
                            f"bytes late reads 0.0, its trailer's first two bytes")
        else:
            notes.append(f"{name}: reads {value!r} ({raw.hex()}), the documented value — "
                         f"the value check OK")

    if dll is not None:
        if dll.is_file():
            notes.append(f"dll: {dll} is {dll.stat().st_size} bytes, sha256 "
                         f"{sha256_of(dll)[:16]}…")
            # The DLL's own bytes for every tensor: expected content read from the source
            # rather than from the manifest. This is the strongest form of the value check —
            # all 153 of them, byte for byte — and the only one that needs no known constant.
            try:
                payloads = dll_payloads(dll, manifest.get("fieldSplit", 28))
            except Exception as error:     # a bad PE, an unknown split, a short payload
                problems.append(f"dll: cannot read the weight table out of {dll}: {error}")
            else:
                compared = 0
                mismatched: list[str] = []
                absent: list[str] = []
                for tensor in manifest["tensors"]:
                    payload = payloads.get(tensor["name"])
                    if payload is None:
                        absent.append(tensor["name"])
                        continue
                    if tensor["stage"] not in files:
                        continue
                    path = directory / "model" / files[tensor["stage"]]
                    if not path.is_file():
                        continue
                    compared += 1
                    extracted = read_tensor(path, tensor)
                    if extracted == payload:
                        continue
                    at = next((i for i, (a, b) in enumerate(zip(extracted, payload))
                               if a != b), min(len(extracted), len(payload)))
                    mismatched.append(
                        f"dll: {tensor['name']!r} holds {extracted[at:at + 8].hex()} at "
                        f"{tensor['stage']}+{tensor['stageOffset'] + at} where the DLL's "
                        f"weight table holds {payload[at:at + 8].hex()} — these are not the "
                        f"DLL's bytes")
                if mismatched:
                    problems.append(mismatched[0])
                    if len(mismatched) > 1:
                        problems.append(f"dll: {len(mismatched)} of {compared} tensors differ "
                                        f"from the DLL's weight table, starting with "
                                        f"{mismatched[1].split('holds')[0].strip()}")
                elif compared:
                    notes.append(f"dll: all {compared} tensors match the DLL's own bytes, "
                                 f"byte for byte OK")
                if absent:
                    others = f", nor for {len(absent) - 1} other(s)" if len(absent) > 1 else ""
                    problems.append(f"dll: the DLL's weight table has no record for "
                                    f"{absent[0]!r}{others} — this directory and this DLL "
                                    f"are not the same build")
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
    parser.add_argument("--dll", help="also read this DLL's weight table and compare every "
                                      "tensor's bytes with the directory's — the expected "
                                      "content itself, rather than the manifest's word for "
                                      "it. Reports its size and hash too")
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
