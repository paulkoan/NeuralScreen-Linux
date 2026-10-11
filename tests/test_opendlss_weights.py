"""The weight-table parser, against a container built the way the DLL's is.

The real blob is 140 MiB inside a 158 MiB DLL that is not in this repository, so
these tests build the container format instead and check the properties the real
one is claimed to have: names of a fixed declared length, a payload length that
says where the next record starts, and the four-way field-split ambiguity that
`extract.py --check` refuses to hide.
"""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "opendlss_weights"))

import extract  # noqa: E402


def build(records, magic=extract.MAGIC):
    """A container in the DLL's format.

    `records` is [(name, payload), ...]. The layout is the real one: 28 bytes of fields
    before the payload (`payloadLength + 40` twice — 40 being the record's total metadata,
    28 before and 12 after — then the length and a tag), the payload, then the record's
    12-byte tail and the next record's 8-byte preamble, whose last u32 is the name length
    the parser reads at `name_start - 8`.


    The header used to be written as 40 bytes because that is what the size fields say if
    they are read as "payload plus the header". They say payload plus the *metadata*, and a
    fake container built on the wrong reading cannot catch the parser being wrong in the
    same direction — which is exactly what happened.
    """
    out = bytearray()
    out += struct.pack("<IIII", magic, 0, len(records[0][0]), 0)
    for i, (name, payload) in enumerate(records):
        out += name.encode("latin1")
        out += struct.pack("<QQQI", len(payload) + 40, len(payload) + 40, len(payload), 1)
        out += payload
        if i + 1 < len(records):
            out += struct.pack("<IIIIIII", 0, 0, 0, 0, 0, len(records[i + 1][0]), 0)
    return bytes(out)


SAMPLES = [("block0.layer0.layer", b"\x1f\x17\x20\x81" * 64),
           ("block1.layer0.layer", b"\x02" * 128),
           ("block70.layer0.blend_scale", b"\x80" * 32)]


def test_the_dll_default_comes_from_the_script_not_a_machine():
    """It shipped with one box's absolute path, so it failed on the box that has the
    GPU — the only machine where it was ever going to be run.

    The path has to be derived from where this file is, so the test compares it to
    the derived path rather than to any literal: a literal would pass here and fail
    on any clone that is not this one.
    """
    derived = Path(extract.__file__).resolve().parents[2] / "native" / "nvngx_dlssnr.dll"
    assert extract.DEFAULT_DLL == derived
    assert extract.REPO == derived.parents[1]

    # The constant is half of it: the parser has to actually default to it, or the
    # fix lives only in a variable nobody reads.
    src = (ROOT / "experiments" / "opendlss_weights" / "extract.py").read_text()
    assert "default=str(DEFAULT_DLL)" in src


def test_a_missing_dll_is_a_sentence_not_a_traceback(capsys):
    """What the box saw was a FileNotFoundError and a stack trace, which says the
    file is missing and nothing about why a clone would not have it."""
    rc = extract.main(["--dll", "/definitely/not/here.dll"])
    assert rc == 2, "a missing DLL is a usage error, not a crash"
    err = capsys.readouterr().err
    assert "no such file" in err
    assert "gitignored" in err, "it has to say why a clone does not have the file"


def test_records_are_found_with_their_declared_lengths():
    blob = build(SAMPLES)
    recs = extract.parse_records(blob, extract.DEFAULT_FIELDS)
    assert [r["name"] for r in recs] == [n for n, _ in SAMPLES]
    assert [r["byteLength"] for r in recs] == [len(p) for _, p in SAMPLES]
    assert [r["block"] for r in recs] == [0, 1, 70]
    assert recs[2]["parameter"] == "blend_scale"


def test_a_name_is_ended_by_its_length_not_by_a_letter():
    """The bug this format hides.

    There is no separator after a name, so when the next byte of metadata happens
    to be a letter, a regex reads the name as `...layerh` and every length after it
    is wrong. The declared length is the only thing that ends a name.
    """
    blob = build([("block1.layer0.layer", b"\x02" * 64),
                  ("block2.layer0.layer", b"\x03" * 64)])
    records = [(m.start(), m.group()) for m in extract.NAME_RE.finditer(blob)]
    overrun = [g for _, g in records if g.endswith(b"h")]
    assert overrun, "the fixture must reproduce the overrun for this test to mean anything"

    names = [r["name"] for r in extract.parse_records(blob, extract.DEFAULT_FIELDS)]
    assert names == ["block1.layer0.layer", "block2.layer0.layer"]
    assert not any(n.endswith("h") for n in names)


def test_the_size_fields_state_the_metadata_total_not_the_header():
    """`payload + 40` twice over, in all 153 of the real records — and that 40 is a trap.

    It is the record's whole metadata: 28 bytes of fields before the payload and 12 after
    it. Read as the header size, it puts every payload twelve bytes late, and that is what
    this extractor did for a whole model: the network ran on shifted weights, diverged, and
    produced a flat picture. The split is pinned by the documented constant instead — see
    test_the_documented_blend_scale_pins_the_field_split.
    """
    blob = build(SAMPLES)
    recs = extract.parse_records(blob, extract.DEFAULT_FIELDS)
    assert recs
    for r in recs:
        a, b, c = struct.unpack_from("<QQQ", blob, r["payload_offset"] - extract.DEFAULT_FIELDS)
        assert a == b == c + 40 == r["byteLength"] + 40, r["name"]

    assert extract.DEFAULT_FIELDS == 28, (
        "the default has to be the split the payload is actually at")
    assert extract.DEFAULT_FIELDS in extract.FIELD_SPLITS
    src = (ROOT / "experiments" / "opendlss_weights" / "extract.py").read_text()
    assert '"--fields", type=int, default=DEFAULT_FIELDS' in src


def test_the_chain_test_fits_every_split_and_cannot_decide():
    """Every split reproduces every offset, because `fields` cancels out of the test.

    That is worth pinning: it is the property that made the extractor read the split as
    the best fit rather than as a question, and reporting it as an answer is how a
    twelve-byte shift in every weight survived a whole model.
    """
    blob = build(SAMPLES)
    info = extract.check(blob)
    assert all(info["splits_that_fit_every_record"].values()), (
        "the chain test fits every split — it cannot decide the split, and the test that "
        "says otherwise is the one that let a 12-byte shift through")
    assert info["field_split_chain_test_is_degenerate"] is True
    assert info["field_split"] == extract.DEFAULT_FIELDS
    assert info["records"] == 3 and info["blocks"] == 3
    assert info["payload_total"] == sum(len(p) for _, p in SAMPLES)


def test_a_blob_that_is_not_this_table_is_refused():
    with pytest.raises(extract.ExtractionError):
        extract.parse_records(build(SAMPLES[:-1], magic=0xDEADBEEF), extract.DEFAULT_FIELDS)
    recs = extract.parse_records(build(SAMPLES), extract.DEFAULT_FIELDS)
    assert recs, "the good container must still parse"


def test_an_implausible_length_is_refused_rather_than_obeyed():
    """A payload length that runs past the blob is a misread record, not a big
    tensor, and must not silently truncate."""
    blob = bytearray(build(SAMPLES))
    first = blob.find(b"block0.layer0.layer") + len(b"block0.layer0.layer")
    struct.pack_into("<Q", blob, first + 16, 1 << 40)
    with pytest.raises(extract.ExtractionError):
        extract.parse_records(bytes(blob), 40)


def test_emit_writes_a_manifest_open_dlss_nr_would_accept(tmp_path):
    import hashlib
    import json

    manifest = extract.emit(build(SAMPLES),
                            extract.parse_records(build(SAMPLES), extract.DEFAULT_FIELDS),
                            extract.DEFAULT_FIELDS, tmp_path, stages=2)
    on_disk = json.loads((tmp_path / "manifest.json").read_text())
    assert on_disk["totals"]["blockCount"] == 3      # its loader refuses any other count
    assert on_disk["totals"]["tensorCount"] == 3
    assert len(on_disk["stages"]) == 2
    assert len(on_disk["tensors"]) == 3

    for stage in on_disk["stages"]:
        data = (tmp_path / "model" / stage["file"]).read_bytes()
        assert len(data) == stage["packedByteLength"]
        # Uppercase, and compared exactly: the loader's sha256Hex formats with
        # "0123456789ABCDEF" (src/sha256.h), so hashlib's own hexdigest — lowercase —
        # never matches and every stage is refused with `stage SHA-256 mismatch`.
        assert hashlib.sha256(data).hexdigest().upper() == stage["sha256"], (
            "a stage whose digest disagrees with its manifest entry would be "
            "refused on load, so the manifest has to be written from the bytes")

    total = sum(t["byteLength"] for t in on_disk["tensors"])
    assert total == sum(len(p) for _, p in SAMPLES), "no payload byte may be lost"
    for t in on_disk["tensors"]:
        stage = next(s for s in on_disk["stages"] if s["id"] == t["stage"])
        assert t["stageOffset"] + t["byteLength"] <= stage["packedByteLength"]
    assert manifest["totals"]["blockCount"] == 3


def test_the_documented_blend_scale_pins_the_field_split():
    """The pin, and the test that would have caught the twelve-byte shift.

    docs/frame.md names one learned constant of the shipped model outside the network's
    arithmetic: `block70.layer0.blend_scale` is 0.7397. It is two bytes wide, so it either
    says where a payload begins or it says nothing at all. At 28 bytes of fields it reads
    0.73975; at 40 — the split this extractor used to ship — it reads 0.0, which is the
    first two bytes of the record's tail.

    Skipped where the DLL is not checked out: it is 158 MiB and deliberately not committed.
    """
    dll = extract.DEFAULT_DLL
    if not dll.is_file():
        pytest.skip("the DLSS-NR DLL is not in this checkout")
    data = dll.read_bytes()
    offset, size = extract.find_weight_blob(data)
    info = extract.check(data[offset:offset + size])
    assert info["field_split"] == 28
    assert info["blend_scale"]["fields_that_read_0.7397"] == 28, (
        "the documented value does not read at the default split: every weight would be "
        "shifted and the network would diverge on them")
    assert abs(info["blend_scale"]["value"] - 0.7397) < 1e-3
