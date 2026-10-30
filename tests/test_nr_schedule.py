"""nr_schedule.py: the stage table derived from the model, checked against the port.

The point of the tool is that the schedule is a property of the weights, not of a
hard-coded list in nr_graph.cpp. These tests pin the three things that would make a
wrong schedule look right:

* the layout formula here against the byte lengths the port itself asserts on;
* the derived 71-block table against the ranges nr_graph.cpp hard-codes (the only
  place the two can be compared without a GPU);
* the 31-block table: same architecture, fewer blocks per level - the claim the
  whole integration rests on.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.nr_schedule import (  # noqa: E402
    KINDS, REFERENCE_71, ScheduleError, check, classify, fused_layout_end,
    stage_table,
)

REAL_71 = Path("/opt/data/tmp/model-big/manifest.json")
REAL_31 = Path("/opt/data/tmp/model-fp8/manifest.json")


def manifest_from(kinds: list[tuple[str, int]]) -> dict:
    """A manifest whose blocks are named blockN.layer0.layer with a kind's byte lengths."""
    tensors = []
    for block, (kind, channels) in enumerate(kinds):
        lengths = KINDS[(kind, channels)]
        for layer, length in enumerate(lengths):
            # The layer field is "layer0" in the extractor's manifests, not an int; the port sorts on
            # that string, so the fixtures say the same thing the real manifest does.
            tensors.append({"name": f"block{block}.layer{layer}.layer", "block": block, "layer": f"layer{layer}",
                            "parameter": "layer", "stage": "stage00", "stageOffset": 0,
                            "byteLength": length})
    return {"totals": {"blockCount": len(kinds), "tensorCount": len(tensors), "stageCount": 1},
            "fieldSplit": 28, "stages": [], "tensors": tensors}


# The two networks, as kinds. 71 blocks: 1/3/5/7 blocks per encoder level, 7+8 split, 8 ViT,
# 8 split decoder, then 7/5/3/3 per decoder level. 31 blocks: one block per level.
KINDS_71 = ([("pre", 32)] + [("block", 32)] * 3 + [("encoder-transition", 32)]
            + [("block", 64)] * 3 + [("encoder-transition", 64)]
            + [("block", 128)] * 5 + [("encoder-transition", 128)]
            + [("block", 256)] * 7 + [("encoder-transition", 256)]
            + [("split", 512)] * 7 + [("split-512x1024", 512)]
            + [("vit", 1024)] * 8 + [("projection", 512)] + [("split", 512)] * 8
            + [("decoder-transition", 256)] + [("block", 256)] * 7
            + [("decoder-transition", 128)] + [("block", 128)] * 5
            + [("decoder-transition", 64)] + [("block", 64)] * 3
            + [("decoder-transition", 32)] + [("block", 32)] * 3
            + [("post", 32)])
KINDS_31 = ([("pre", 32), ("block", 32), ("encoder-transition", 32),
             ("block", 64), ("encoder-transition", 64),
             ("block", 128), ("encoder-transition", 128),
             ("block", 256), ("encoder-transition", 256),
             ("split", 512), ("split-512x1024", 512),
             ("vit", 1024)] + [("vit", 1024)] * 7
            + [("projection", 512), ("split", 512), ("split", 512),
               ("decoder-transition", 256), ("block", 256),
               ("decoder-transition", 128), ("block", 128),
               ("decoder-transition", 64), ("block", 64),
               ("decoder-transition", 32), ("block", 32), ("post", 32)])


def test_the_layout_formula_reproduces_the_ports_own_byte_lengths():
    # fused_layout_end(c) + 16 are the byte lengths of the single-layer blocks the port
    # reads through fusedLayout(c): 32 -> 20,672, 64 -> 61,760, 128 -> 197,184, 256 -> 689,232.
    assert [fused_layout_end(c) + 16 for c in (32, 64, 128, 256)] == [20672, 61760, 197184, 689232]


def test_the_71_block_table_is_the_ports_hard_coded_table():
    table = stage_table(manifest_from(KINDS_71))
    assert [(e["stage"], e["channels"], e["first"], e["last"]) for e in table] == REFERENCE_71
    assert check(manifest_from(KINDS_71)) == []


def test_the_31_block_network_is_the_same_architecture_fewer_blocks_per_level():
    table = stage_table(manifest_from(KINDS_31))
    assert [(e["stage"], e["channels"], e["first"], e["last"]) for e in table] == [
        ("pre", 32, 0, 0), ("encoder-32", 32, 1, 2), ("encoder-64", 64, 3, 4),
        ("encoder-128", 128, 5, 6), ("encoder-256", 256, 7, 8), ("encoder-512", 512, 9, 10),
        ("vit", 1024, 11, 18), ("transition-38-39", 512, 19, 19), ("decoder-512", 512, 20, 21),
        ("decoder-256", 256, 22, 23), ("decoder-128", 128, 24, 25), ("decoder-64", 64, 26, 27),
        ("decoder-32", 32, 28, 29), ("post", 32, 30, 30),
    ]
    # Same six levels, same eight-block ViT bottleneck, same encoder/decoder channel ladder:
    # the only difference is the number of blocks inside each level.
    levels_71 = [e["level"] for e in stage_table(manifest_from(KINDS_71))]
    levels_31 = [e["level"] for e in table]
    assert levels_71 == levels_31


def test_a_block_len_that_is_not_a_layout_is_refused_not_guessed():
    tensors = [{"name": "block0.layer0.layer", "block": 0, "layer": 0, "parameter": "layer",
                "stage": "stage00", "stageOffset": 0, "byteLength": 1234}]
    with pytest.raises(ScheduleError):
        classify(tensors)


def test_a_manifest_that_disagrees_with_its_own_block_count_is_refused():
    # The extractor's totals and the tensors it wrote have to agree: a schedule built from
    # one and validated against the other is how a half-written model reaches the graph.
    manifest = manifest_from(KINDS_31)
    manifest["tensors"] = [t for t in manifest["tensors"] if t["block"] != 2]
    problems = check(manifest)
    assert problems and "declares 31 blocks but carries 30" in problems[0]


@pytest.mark.skipif(not REAL_71.exists(), reason="needs the extracted 310.9.16 networks")
def test_the_extracted_71_block_network_matches_the_port():
    manifest = json.loads(REAL_71.read_text())
    assert manifest["totals"]["blockCount"] == 71
    assert check(manifest) == []


def port_binary() -> Path:
    return Path(os.environ.get("NS_ODL_NATIVE_BIN", "/opt/neuralscreen/port/build/dlss5vk"))


def port_table(binary: Path, manifest: dict, directory: Path) -> list[tuple[str, int, int, int]]:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(json.dumps(manifest))
    done = subprocess.run([str(binary), "schedule", "--model", str(directory), "--check"],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    rows = []
    for line in done.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) == 6 and fields[1].isdigit():   # skip the column header
            rows.append((fields[0], int(fields[1]), int(fields[2]), int(fields[3])))
    return rows


@pytest.mark.skipif(not port_binary().exists(), reason="needs a built dlss5vk (NS_ODL_NATIVE_BIN)")
def test_the_port_derives_the_same_table_the_reference_tool_does(tmp_path):
    # The recorder walks the port's own derivation of the table, so the thing that would quietly
    # diverge is that derivation. Both models, through the binary's device-free `schedule` mode,
    # against the reference tool's table - and `--check` also proves the 71-block one equals the
    # ranges the recorder used to hard-code.
    for name, kinds, expected in (("large", KINDS_71, REFERENCE_71), ("small", KINDS_31, None)):
        manifest = manifest_from(kinds)
        table = stage_table(manifest)
        want = expected if expected is not None else [
            (e["stage"], e["channels"], e["first"], e["last"]) for e in table]
        assert port_table(port_binary(), manifest, tmp_path / name) == want


@pytest.mark.skipif(not REAL_31.exists(), reason="needs the extracted 310.9.16 networks")
def test_the_extracted_31_block_network_derives_the_same_table():
    manifest = json.loads(REAL_31.read_text())
    assert manifest["totals"]["blockCount"] == 31
    assert check(manifest) == []
    table = stage_table(manifest)
    assert stage_table(manifest_from(KINDS_31)) == table
    # the small network's own blend weight, read from block30.layer0.blend_scale
    assert any(t["name"] == "block30.layer0.blend_scale" for t in manifest["tensors"])
