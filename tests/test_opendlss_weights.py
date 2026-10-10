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

    `records` is [(name, payload), ...]. The layout is the (40 fields, 16 trailer)
    reading of the 56 bytes of per-record metadata: name, a/b/payloadLength and
    three more u64s, the payload, then the next record's 16 bytes of leading
    metadata (0, previous payload/2, next name length, 0).
    """
    out = bytearray()
    out += struct.pack("<IIII", magic, 0, len(records[0][0]), 0)
    for i, (name, payload) in enumerate(records):
        out += name.encode("latin1")
        out += struct.pack("<QQQQQ", len(payload) + 40, len(payload) + 40,
                           len(payload), 0, 0)
        out += payload
        # Exactly one 16-byte block of leading metadata separates two records, and
        # it belongs to the one that follows. Writing it here AND at the top of the
        # next iteration puts 32 bytes in the gap and breaks the very span the
        # parser is being tested on.
        if i + 1 < len(records):
            out += struct.pack("<IIII", 0, len(payload) // 2, len(records[i + 1][0]), 0)
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
    recs = extract.parse_records(blob, 40)
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

    names = [r["name"] for r in extract.parse_records(blob, 40)]
    assert names == ["block1.layer0.layer", "block2.layer0.layer"]
    assert not any(n.endswith("h") for n in names)


def test_each_record_states_where_its_payload_starts():
    """The four field splits all fit every offset, so offsets cannot choose.

    The records can. The u64 at +0 and the u64 at +8 both equal the payload length
    plus 40 — in all 153 of the real ones — which is what makes 40 bytes of fields
    the reading rather than the best fit. This is the test that would catch a
    container whose fields meant something else.
    """
    blob = build(SAMPLES)
    recs = extract.parse_records(blob, 40)
    assert recs
    for r in recs:
        a, b, c = struct.unpack_from("<QQQ", blob, r["payload_offset"] - 40)
        assert a == b == c + 40 == r["byteLength"] + 40, r["name"]

    src = (ROOT / "experiments" / "opendlss_weights" / "extract.py").read_text()
    assert '"--fields", type=int, default=40' in src, (
        "the default has to be the split the records state, not one of the four")


def test_every_split_fits_and_that_is_the_ambiguity():
    """All four field splits reproduce every offset, because they all total 56 and
    it is the payload's END that the next name pins."""
    blob = build(SAMPLES)
    info = extract.check(blob)
    assert info["splits_that_fit_every_record"] == {32: True, 40: True, 48: True, 56: True}
    assert info["field_split_ambiguous"] is True
    assert info["records"] == 3 and info["blocks"] == 3
    assert info["payload_total"] == sum(len(p) for _, p in SAMPLES)


def test_a_blob_that_is_not_this_table_is_refused():
    with pytest.raises(extract.ExtractionError):
        extract.parse_records(build(SAMPLES[:-1], magic=0xDEADBEEF), 40)
    recs = extract.parse_records(build(SAMPLES), 40)
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

    manifest = extract.emit(build(SAMPLES), extract.parse_records(build(SAMPLES), 40),
                            40, tmp_path, stages=2)
    on_disk = json.loads((tmp_path / "manifest.json").read_text())
    assert on_disk["totals"]["blockCount"] == 3      # its loader refuses any other count
    assert on_disk["totals"]["tensorCount"] == 3
    assert len(on_disk["stages"]) == 2
    assert len(on_disk["tensors"]) == 3

    for stage in on_disk["stages"]:
        data = (tmp_path / "model" / stage["file"]).read_bytes()
        assert len(data) == stage["packedByteLength"]
        assert hashlib.sha256(data).hexdigest() == stage["sha256"], (
            "a stage whose digest disagrees with its manifest entry would be "
            "refused on load, so the manifest has to be written from the bytes")

    total = sum(t["byteLength"] for t in on_disk["tensors"])
    assert total == sum(len(p) for _, p in SAMPLES), "no payload byte may be lost"
    for t in on_disk["tensors"]:
        stage = next(s for s in on_disk["stages"] if s["id"] == t["stage"])
        assert t["stageOffset"] + t["byteLength"] <= stage["packedByteLength"]
    assert manifest["totals"]["blockCount"] == 3
