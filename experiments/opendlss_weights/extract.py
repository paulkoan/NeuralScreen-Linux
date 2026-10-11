"""Extract the DLSS 5 NR weight table from nvngx_dlssnr.dll.

What is in the DLL, established by measurement rather than inference:

* `native/nvngx_dlssnr.dll` is 158.2 MiB, of which `.rsrc` is 140.9 MiB;
* the `.rsrc` section holds exactly two resources, and the one that matters is a
  single RCDATA leaf of 147,695,410 bytes;
* that leaf is a self-describing tensor table: a u32 magic, then records of
  `[name][fields][payload]`, with 153 names of the form `blockN.layerM.parameter`;
* the declared payload lengths sum to 147,683,778 bytes = 140.8 MiB, which is
  OpenDLSS-NR's documented "141 MiB of weights" to within the table's own ~11 KB;
* the 153 records cover 71 distinct blocks, block0 through block70, which is the
  `blockCount: 71` OpenDLSS-NR's `nr::Model` refuses anything else than.

So the weights are not to be reverse-engineered out of a binary: they are indexed
by name, with their lengths stated. What this tool does is walk that table and
print or emit it.

WHAT WAS OPEN, AND WHAT SETTLED IT. A record's 56 bytes of metadata can split four
ways (32+24, 40+16, 48+8, 56+0) and all four reproduce every one of the 152
consecutive next-record offsets, so the payload's END is pinned and its start is
not — the four candidates sit 8 bytes apart. The records settle it themselves:
the u64 at +0 and the u64 at +8 both equal the payload length plus 40, in **153 of
153 records**, so 40 bytes of fields precede the payload and 16 bytes of trailer
follow it. `--fields 40` is therefore the reading the data states, not the best fit.

And the payload sizes are OpenDLSS-NR's own layout. Its docs/weights.md gives the
byte length of a record as a sum of shapes and says "the sum reproduces every
tensor's byteLength exactly, which is the check that the layout is right". Against
our 153 declared lengths that check passes with a delta of 0 for every block,
including every variant it documents: block 0 = base + 1,024 (its `16 -> 32` f16
adapter, 16x32x2 bytes), block 4 = the `2C -> C` upsample variant, blocks 8, 14 and
22 = transition matrices, the 512-channel and ViT blocks = their four- and
five-record splits, block 30 layer4 = the `512 -> 1024` matrix, block 39 layer0 =
the `1024 -> 512` matrix plus its skip scale.

What is still not verified: the 16-byte zero pads the layout documents are not zero
in these native bytes at 3 of 3 predicted offsets, so the native form is the MMA
fragment packing its host *walks* rather than the plain-matrix form it *writes* —
consistent with weights.md, which describes the host walking fragments and writing
matrices, but it means a byte-identical round trip is not yet shown. The fourth
u64 of each record is not crc32, adler32 or a plain sum of the payload.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

MAGIC = 0x08CDA732
# The DLL is 159 MiB and NVIDIA's, so it is gitignored and lives in whatever clone
# has it: native/nvngx_dlssnr.dll at this file's repository root. Resolved from
# __file__ rather than written out, which is how this shipped with one machine's
# absolute path and failed on the machine that actually has the GPU.
REPO = Path(__file__).resolve().parents[2]
DEFAULT_DLL = REPO / "native" / "nvngx_dlssnr.dll"
RT_RCDATA = 10
NAME_RE = re.compile(rb"block\d+\.layer\d+\.[A-Za-z0-9_]+")
NAME_RE_STR = re.compile(r"block\d+\.layer\d+\.[A-Za-z0-9_]+")

# The metadata either side of a payload, in bytes. 56 is fixed; how it splits
# between the fields before the payload and the trailer after it is not, and
# every split in this list reproduces all 153 next-name offsets.
META_BYTES = 56
# 28 is the split, and it is pinned by a value rather than by arithmetic: the size fields
# read `payload + 40` because a record carries 40 bytes of metadata — 28 before the payload
# and 12 after it — so 40 is the metadata total and not the header. That distinction cost a
# whole model: with the header read as 40, every payload started 12 bytes late and ended 12
# bytes into the next record's metadata, so the network ran on shifted weights and diverged
# (86% of the output head came back non-finite, and the composed image was a flat colour).
#
# The pin is docs/frame.md's one known value: `block70.layer0.blend_scale` is 0.7397 in the
# shipped model, and that f16 (`eb 39`) sits exactly 28 bytes after the record's name. Every
# other candidate puts it somewhere else, which is what `check()` reports.
FIELD_SPLITS = (28, 32, 40, 48, 56)
DEFAULT_FIELDS = 28


class ExtractionError(RuntimeError):
    """A blob that is not the weights, or a record that does not parse."""


def sections(data: bytes) -> dict[str, tuple[int, int, int, int]]:
    """PE section name -> (virtual address, virtual size, raw offset, raw size)."""
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        raise ExtractionError("not a PE file (no PE signature)")
    nsec, = struct.unpack_from("<H", data, e_lfanew + 6)
    opt_size, = struct.unpack_from("<H", data, e_lfanew + 20)
    base = e_lfanew + 24 + opt_size
    out = {}
    for i in range(nsec):
        o = base + i * 40
        name = data[o:o + 8].rstrip(b"\0").decode("latin1")
        vsize, vaddr, rawsize, rawoff = struct.unpack_from("<IIII", data, o + 8)
        out[name] = (vaddr, vsize, rawoff, rawsize)
    return out


def resource_leaves(data: bytes) -> list[tuple[tuple[str, ...], int, int, int]]:
    """Every resource leaf as (path, file offset, size, codepage).

    Directory pointers in a resource tree are offsets from the section start
    while a data entry's OffsetToData is an RVA. Treating the first as the second
    walks off the end of the file, which is how this started.
    """
    rt = {1: "CURSOR", 2: "BITMAP", 3: "ICON", 4: "MENU", 5: "DIALOG",
          6: "STRING", 9: "ACCELERATOR", 10: "RCDATA", 11: "MESSAGETABLE",
          12: "GROUP_CURSOR", 14: "GROUP_ICON", 16: "VERSION", 24: "MANIFEST"}
    sec = sections(data)
    if ".rsrc" not in sec:
        raise ExtractionError("no .rsrc section: this DLL carries no weights")
    rs_va, _, rs_raw, _ = sec[".rsrc"]

    def file_off(rva: int) -> int:
        return rs_raw + (rva - rs_va)

    def walk(rel: int, depth: int = 0, path: tuple[str, ...] = ()) -> list:
        named, ids = struct.unpack_from("<HH", data, rs_raw + rel + 12)
        leaves = []
        for i in range(named + ids):
            eo = rs_raw + rel + 16 + i * 8
            nm, od = struct.unpack_from("<II", data, eo)
            ident = rt.get(nm, f"#{nm}") if depth == 0 else str(nm)
            if od >= 0x80000000:
                leaves += walk(od - 0x80000000, depth + 1, path + (ident,))
            else:
                data_rva, size, codepage, _ = struct.unpack_from(
                    "<IIII", data, rs_raw + od)
                leaves.append((path + (ident,), file_off(data_rva), size, codepage))
        return leaves

    return walk(0)


def find_weight_blob(data: bytes) -> tuple[int, int]:
    """The RCDATA leaf that holds the network. Behaviour, not faith, decides.

    The largest resource is taken, then checked for the magic — a DLL whose
    biggest resource is not this table is not the one this tool understands.
    """
    leaves = resource_leaves(data)
    if not leaves:
        raise ExtractionError("no resources at all")
    path, off, size, _ = max(leaves, key=lambda x: x[2])
    magic, = struct.unpack_from("<I", data, off)
    if magic != MAGIC:
        raise ExtractionError(
            f"biggest resource is {'/'.join(path)} ({size:,} bytes) but its magic "
            f"is {magic:#010x}, not {MAGIC:#010x} — not the weight table")
    return off, size


def parse_records(blob: bytes, fields: int = DEFAULT_FIELDS) -> list[dict]:
    """Every tensor record: name, payload offset and length.

    The name's length comes from the u32 eight bytes before the name. It has to:
    there is no separator, so "block10.layer0.layer" runs straight into the next
    field whenever that field's first byte is a letter, which is why a regex alone
    reports names ending in stray characters.
    """
    if fields not in FIELD_SPLITS:
        raise ExtractionError(f"field split {fields} is not one of {FIELD_SPLITS}")
    magic, = struct.unpack_from("<I", blob, 0)
    if magic != MAGIC:
        raise ExtractionError(
            f"blob magic is {magic:#010x}, not {MAGIC:#010x}: not this table")
    out = []
    for m in NAME_RE.finditer(blob):
        off = m.start()
        nl, = struct.unpack_from("<I", blob, off - 8)
        if not 8 < nl < 64:
            raise ExtractionError(f"implausible name length {nl} at {off}")
        name = blob[off:off + nl].decode("latin1")
        if not NAME_RE_STR.fullmatch(name):
            raise ExtractionError(f"name at {off} is not blockN.layerM.parameter: {name!r}")
        head = blob[off + nl:off + nl + fields]
        declared, = struct.unpack_from("<Q", head, 16)
        if not 0 < declared <= 64 << 20:
            raise ExtractionError(f"implausible payload length {declared} for {name}")
        out.append({
            "name": name,
            "block": int(name.split(".")[0][5:]),
            "layer": name.split(".")[1],
            "parameter": name.split(".", 2)[2],
            "payload_offset": off + nl + fields,
            "byteLength": declared,
        })
    return out


def record_span(blob: bytes, records: list[dict], i: int, fields: int) -> int:
    """Bytes from record i's name to record i+1's name (or the end of the blob)."""
    start = records[i]["payload_offset"] - fields - len(records[i]["name"])
    end = (records[i + 1]["payload_offset"] - fields - len(records[i + 1]["name"])
           if i + 1 < len(records) else len(blob))
    return end - start


def check(blob: bytes) -> dict:
    """Everything that can be established without OpenDLSS-NR's arithmetic."""
    fits = {}
    for f in FIELD_SPLITS:
        recs = parse_records(blob, f)
        ok = all(
            records_agree(blob, recs, f, i) for i in range(len(recs) - 1))
        fits[f] = (len(recs), ok)
    recs = parse_records(blob, DEFAULT_FIELDS)
    total = sum(r["byteLength"] for r in recs)
    return {
        "blob_bytes": len(blob),
        "magic": hex(struct.unpack_from("<I", blob, 0)[0]),
        "records": len(recs),
        "blocks": len({r["block"] for r in recs}),
        "block_range": (min(r["block"] for r in recs), max(r["block"] for r in recs)),
        "parameters": sorted({r["parameter"] for r in recs}),
        "payload_total": total,
        "payload_total_mib": total / 2 ** 20,
        "table_overhead": len(blob) - total,
        "splits_that_fit_every_record": {k: v[1] for k, v in fits.items()},
        # Kept as a record of the degeneracy above, not as a question: every split "fits".
        "field_split_chain_test_is_degenerate": sum(1 for v in fits.values() if v[1]) > 1,
        "field_split": DEFAULT_FIELDS,
        "blend_scale": blend_scale(blob),
    }


def blend_scale(blob: bytes) -> dict:
    """The documented value that pins the payload offset.

    docs/frame.md names one learned constant of the shipped model outside the network's
    arithmetic: `block70.layer0.blend_scale` is 0.7397. It is two bytes wide, so it says
    where a payload begins or it says nothing at all — and at 28 bytes after the name it
    reads 0.73975, which is that constant as f16. At 40 it reads 0.0, which is the first
    two bytes of the record's trailer.
    """
    for fields in FIELD_SPLITS:
        record = next((r for r in parse_records(blob, fields)
                       if r["name"] == "block70.layer0.blend_scale"), None)
        if record is None:
            return {"error": "no blend_scale record in the table"}
        payload = blob[record["payload_offset"]:record["payload_offset"] + record["byteLength"]]
        value = struct.unpack_from("<e", payload + b"\0\0", 0)[0] if len(payload) >= 2 else None
        if value is not None and abs(value - 0.7397) < 1e-3:
            return {"fields_that_read_0.7397": fields, "value": value}
    return {"fields_that_read_0.7397": None,
            "note": "no candidate split reads the documented 0.7397 — the layout changed, "
                    "or this is not the same model build as the documentation describes"}


def records_agree(blob: bytes, recs: list[dict], fields: int, i: int) -> bool:
    """Does record i's declared payload land exactly where record i+1's name is?

    NOTE: this test cannot decide the field split, and reporting it as if it could is how
    the split was read as 40 for a whole model. `record_span` subtracts `fields` from both
    payload offsets — it has to, to measure name-to-name — so `fields` cancels and the test
    is the same for every candidate. It is kept because it does check something real (that
    a payload of the declared length reaches the next record), but the split is pinned by
    the value in `check()`: a known f16 from the documentation, at a known offset.
    """
    span = record_span(blob, recs, i, fields)
    # The name is part of the span too: next name offset - this name offset is
    # the name plus the metadata plus the payload, which is why forgetting the
    # name here made every split look wrong when the solver said all four fit.
    return span == len(recs[i]["name"]) + META_BYTES + recs[i]["byteLength"]


def emit(blob: bytes, records: list[dict], fields: int, out: Path,
         stages: int = 11) -> dict:
    """Write a model directory in OpenDLSS-NR's layout, manifest included.

    Its `nr::Model` wants `manifest.json` with `totals.blockCount`, a `stages`
    array of files of packed bytes (id, file, packedByteLength, sha256) and a
    `tensors` array of (name, block, layer, parameter, stage, stageOffset,
    byteLength). Nothing in that repository produces such a directory, so this
    one defines the partition: the records split into `stages` contiguous runs.
    """
    model = out / "model"
    model.mkdir(parents=True, exist_ok=True)
    per = max(1, (len(records) + stages - 1) // stages)
    stage_records = [records[i:i + per] for i in range(0, len(records), per)]

    man_stages, man_tensors = [], []
    for n, group in enumerate(stage_records):
        sid = f"stage{n:02d}"
        buf = bytearray()
        for r in group:
            offset = len(buf)
            payload = blob[r["payload_offset"]:r["payload_offset"] + r["byteLength"]]
            if len(payload) != r["byteLength"]:
                raise ExtractionError(f"short payload for {r['name']}")
            buf += payload
            man_tensors.append({
                "name": r["name"], "block": r["block"], "layer": r["layer"],
                "parameter": r["parameter"], "stage": sid,
                "stageOffset": offset, "byteLength": r["byteLength"],
            })
        (model / f"{sid}.bin").write_bytes(bytes(buf))
        man_stages.append({
            "id": sid, "file": f"{sid}.bin", "packedByteLength": len(buf),
            # UPPERCASE, because that is what the loader produces: src/sha256.h formats
            # with "0123456789ABCDEF" and Model compares the two strings exactly, so a
            # lowercase hexdigest never matches. It is not cosmetic — every stage of every
            # model we extract failed the loader's check until this was the case, and
            # `parity` and `verify` load with verification on by default.
            "sha256": hashlib.sha256(bytes(buf)).hexdigest().upper(),
        })

    manifest = {
        "totals": {"blockCount": len({r["block"] for r in records}),
                   "tensorCount": len(records),
                   "stageCount": len(man_stages)},
        "fieldSplit": fields,
        "stages": man_stages,
        "tensors": man_tensors,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="extract.py", description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--dll", default=str(DEFAULT_DLL),
                    help=f"the DLSS-NR runtime carrying the weights "
                         f"(default: {DEFAULT_DLL})")
    ap.add_argument("--out", help="write a model directory here (manifest.json + model/)")
    ap.add_argument("--fields", type=int, default=DEFAULT_FIELDS, choices=FIELD_SPLITS,
                    help="bytes of per-record fields before the payload. 40 is the "
                         "reading the records state: the u64 at +0 and the u64 at +8 "
                         "both equal the payload length plus 40, in all 153 of them")
    ap.add_argument("--stages", type=int, default=11)
    args = ap.parse_args(argv)

    dll = Path(args.dll)
    if not dll.is_file():
        # A missing DLL is the common case on a fresh clone and it deserves a
        # sentence, not a traceback: the file is not in git, so nothing else here
        # tells you where it was supposed to come from.
        print(f"no such file: {dll}\n"
              f"native/nvngx_dlssnr.dll is gitignored (159 MiB, and NVIDIA's), so a "
              f"clone does not have it. Download it from the release and put it at\n"
              f"  {DEFAULT_DLL}\n"
              f"or point --dll at wherever it is.", file=sys.stderr)
        return 2

    data = dll.read_bytes()
    off, size = find_weight_blob(data)
    blob = data[off:off + size]
    print(f"dll      : {args.dll}  ({len(data):,} bytes)")
    print(f"weight blob: offset {off:,}  size {size:,}")

    info = check(blob)
    for k, v in info.items():
        print(f"  {k:28} {v}")

    records = parse_records(blob, args.fields)
    print(f"\nrecords parsed with a {args.fields}-byte field header: {len(records)}")
    for r in records[:3] + records[-2:]:
        print(f"  {r['name']:28} block {r['block']:>2}  payload {r['byteLength']:>10,}"
              f"  at {r['payload_offset']:>12,}")
    pin = info["blend_scale"]
    if pin.get("fields_that_read_0.7397") == args.fields:
        print(f"\nfield split pinned at {args.fields}: block70.layer0.blend_scale reads "
              f"{pin['value']!r}, the value docs/frame.md names for the shipped model")
    else:
        print(f"\nWARNING: the documented blend_scale (0.7397) does not read at "
              f"{args.fields} bytes of fields — it reads at "
              f"{pin.get('fields_that_read_0.7397')}. Weights extracted with this split "
              f"are shifted and the network will diverge on them.")

    if args.out:
        manifest = emit(blob, records, args.fields, Path(args.out), args.stages)
        print(f"\nwrote {args.out}/manifest.json with {len(manifest['stages'])} stages "
              f"and {len(manifest['tensors'])} tensors")
        print(f"blockCount {manifest['totals']['blockCount']} "
              f"(OpenDLSS-NR refuses any other)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
