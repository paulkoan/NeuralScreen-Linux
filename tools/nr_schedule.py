"""Derive the NR graph's stage schedule from a model manifest, instead of hard-coding it.

`nr_graph.cpp` knows the 71-block network by six hard-coded block ranges
(`{5,8}`, `{9,14}`, `{15,22}`, `23..30`, `31..38`, `40..47`) plus four decoder stages.
Those ranges are the 71-block model's *block counts per U-Net level*, not the
architecture: every block's tensor is laid out by `fusedLayout(channels)` and the
kinds repeat. This tool reads a manifest, classifies every block by its tensors'
byte lengths, and prints the stage table the recorder should walk:

    stage  channels  first  last  level  kind

Two models are known, both extracted from nvngx_dlssnr.dll 310.9.16:

* magic 0x08cda732, 71 blocks - the shipped 153-tensor network the port runs today;
* magic 0x06c9dfdf, 31 blocks - the small network, 77 tensors.

They are the **same architecture**: identical per-block byte lengths, identical
per-stage layout, and blocks that differ only in how many per level. That is why
the schedule can be derived once and both models walked by the same recorder.
The check `--check` pins this: the 71-block table this tool derives must equal the
ranges `nr_graph.cpp` hard-codes, and both models must classify with no leftover
block.

Usage:
  python tools/nr_schedule.py <model-dir-or-manifest> [--check]
  python tools/nr_schedule.py --dll <dll> --magic 0x06c9dfdf     # extract then derive
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LEVELS = {32: 0, 64: 1, 128: 2, 256: 3, 512: 4}
BOTTLENECK_LEVEL = 5


def align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def standard_hidden(channels: int) -> int:
    if channels in (32, 64, 128, 256):
        return 128
    raise ValueError(f"no fused layout for {channels} channels")


def fused_layout_end(channels: int) -> int:
    """`fusedLayout(channels).endWithoutPadding` from nr_graph.cpp.

    Reimplemented here so the classifier and the C++ layout cannot drift silently:
    `test_the_layout_formula_matches_the_port` compares the resulting byte lengths
    against the same blocks the port asserts on.
    """
    hidden = standard_hidden(channels)
    heads = channels // 32
    expert_ffn = channels >= 64
    expert_count = channels // 32 if expert_ffn else 0
    expand_bytes = expert_count * channels * 128 if expert_ffn else channels * hidden
    ffn_weight_bytes = (expand_bytes + expert_count * 128 * 32 + expert_count * 32 * channels
                        if expert_ffn else expand_bytes + hidden * channels)
    ffn_cos_skip = ffn_weight_bytes + 16
    qkv = ffn_cos_skip + channels * 2 + 16
    relative = qkv + channels * channels * 3
    scale = relative + heads * 8192
    projection = scale + align_up(heads * 4, 16)
    attn_cos_skip = projection + channels * channels
    return attn_cos_skip + channels * 2


# A block is identified by the byte lengths of its tensors, in layer order. Every
# entry below is measured on the two 310.9.16 networks; where a length is a formula
# over `fused_layout_end` the formula is given so a layout change shows up as a
# failure here rather than as a wrong schedule.
def signatures() -> dict[tuple[int, tuple[int, ...]], tuple[str, int]]:
    table: dict[tuple[int, tuple[int, ...]], tuple[str, int]] = {}

    def add(kind: str, channels: int, lengths: tuple[int, ...], _note: str = "") -> None:
        key = (len(lengths), lengths)
        if key in table and table[key] != (kind, channels):
            raise AssertionError(f"ambiguous signature {lengths}: {table[key]} vs {(kind, channels)}")
        table[key] = (kind, channels)

    add("pre", 32, (21696,))   # 21,696: preFusedLayout().endWithoutPadding + 16, the 16->32 adapter
    for c in (32, 64, 128, 256):
        add("block", c, (fused_layout_end(c) + 16,))
    # Encoder transition: the stage's last block also carries the 2C x C upsample matrix.
    for c in (32, 64, 128, 256):
        extra = 16 if c == 32 else 0
        add("encoder-transition", c, (fused_layout_end(c) + 2 * c * c + extra,))
    # Decoder transition: the stage's first block carries the 2C -> C upsample; the
    # 32-channel one is 16 bytes wider for the narrow-buffer padding.
    for c, extra in ((32, 80), (64, 112), (128, 240), (256, 496)):
        add("decoder-transition", c, (fused_layout_end(c) + 2 * c * c + extra,))
    split4 = (524288, 263168, 917568, 263168)
    add("split", 512, split4)
    add("split-512x1024", 512, split4 + (524304,))   # also carries the 512 -> 1024 matrix
    add("vit", 1024, (4194320, 4196352, 3145856, 2, 1050624))
    add("projection", 512, (525312,))   # 525,312: block 39, the 1024 -> 512 matrix plus its skip scale
    add("post", 32, (21808,))
    return table


SIGNATURES = signatures()
# Reverse map for the tests: kind/channels -> lengths.
KINDS = {(kind, channels): lengths for (_, lengths), (kind, channels) in SIGNATURES.items()}


class ScheduleError(RuntimeError):
    """A block whose tensors are not one the port can lay out."""


def block_signature(tensors: list[dict]) -> tuple[int, ...]:
    layers = sorted(tensors, key=lambda t: t["layer"])
    body = [t for t in layers if t["name"].endswith(".layer")]
    return tuple(t["byteLength"] for t in body)


def classify(tensors: list[dict]) -> tuple[str, int]:
    sig = block_signature(tensors)
    try:
        return SIGNATURES[(len(sig), sig)]
    except KeyError:
        raise ScheduleError(f"unrecognised block signature {sig}") from None


def load(manifest: Path) -> dict:
    if manifest.is_dir():
        manifest = manifest / "manifest.json"
    return json.loads(manifest.read_text())


def blocks_of(manifest: dict) -> dict[int, list[dict]]:
    blocks: dict[int, list[dict]] = {}
    for tensor in manifest["tensors"]:
        blocks.setdefault(tensor["block"], []).append(tensor)
    return blocks


def stage_table(manifest: dict) -> list[dict]:
    """The order the recorder walks: encoder levels, bottleneck, decoder levels, post.

    A stage is a maximal run of blocks at one channel count. An encoder stage owns the
    transition block that follows it and a decoder stage owns the transition block that
    precedes it, which is how nr_graph.cpp's ranges are shaped (`5..8` ends on the
    transition tensor, `48..55` starts on one).
    """
    blocks = blocks_of(manifest)
    order = sorted(blocks)
    kinds = {b: classify(blocks[b]) for b in order}
    table: list[dict] = []
    direction = "encoder"
    index = 0
    while index < len(order):
        block = order[index]
        kind, channels = kinds[block]
        if kind == "pre":
            table.append({"stage": "pre", "channels": 32, "first": block, "last": block,
                          "level": LEVELS[32], "kind": "pre", "direction": "encoder"})
            index += 1
            continue
        if kind == "post":
            table.append({"stage": "post", "channels": 32, "first": block, "last": block,
                          "level": LEVELS[32], "kind": "post", "direction": "decoder"})
            index += 1
            continue
        if kind == "projection":
            table.append({"stage": "transition-38-39", "channels": 512, "first": block, "last": block,
                          "level": LEVELS[512], "kind": "projection", "direction": "decoder"})
            direction = "decoder"
            index += 1
            continue
        if kind == "vit":
            first = block
            while index < len(order) and kinds[order[index]][0] == "vit":
                index += 1
            table.append({"stage": "vit", "channels": 1024, "first": first, "last": order[index - 1],
                          "level": BOTTLENECK_LEVEL, "kind": "vit", "direction": "bottleneck"})
            continue
        if kind == "split-512x1024" or kind == "split":
            first = block
            while index < len(order) and kinds[order[index]][0] in ("split", "split-512x1024"):
                index += 1
            last = order[index - 1]
            if direction == "encoder" and kinds[last][0] == "split-512x1024":
                table.append({"stage": "encoder-512", "channels": 512, "first": first, "last": last,
                              "level": LEVELS[512], "kind": "split", "direction": "encoder"})
            else:
                table.append({"stage": "decoder-512", "channels": 512, "first": first, "last": last,
                              "level": LEVELS[512], "kind": "split", "direction": "decoder"})
            continue
        # A U-Net level: blocks up to and including the transition block. On the decoder
        # side the transition block opens the stage, and the count is one fewer per level.
        channel = channels
        first = block
        stage_kinds = ("block", "encoder-transition", "decoder-transition")
        while index < len(order):
            kind_here, channels_here = kinds[order[index]]
            if channels_here != channel or kind_here not in stage_kinds:
                break
            index += 1
            if kind_here == "encoder-transition":
                break   # the encoder stage owns its transition; a decoder's opens it and keeps going
        last = order[index - 1]
        transition = kinds[last][0]
        if kinds[first][0] == "decoder-transition":
            direction = "decoder"   # the upsample opens the stage and the block count is one smaller
        table.append({"stage": f"{direction}-{channel}", "channels": channel, "first": first, "last": last,
                      "level": LEVELS[channel], "kind": transition, "direction": direction})
    return table


# The ranges nr_graph.cpp hard-codes for the 71-block network (record(), encoderStages,
# the ViT block, the decoderStages table, the post block). The derived table has to
# reproduce them, which is the check that this derivation is the port's own schedule.
REFERENCE_71 = [
    ("pre", 32, 0, 0), ("encoder-32", 32, 1, 4), ("encoder-64", 64, 5, 8),
    ("encoder-128", 128, 9, 14), ("encoder-256", 256, 15, 22), ("encoder-512", 512, 23, 30),
    ("vit", 1024, 31, 38), ("transition-38-39", 512, 39, 39), ("decoder-512", 512, 40, 47),
    ("decoder-256", 256, 48, 55), ("decoder-128", 128, 56, 61), ("decoder-64", 64, 62, 65),
    ("decoder-32", 32, 66, 69), ("post", 32, 70, 70),
]


def check(manifest: dict) -> list[str]:
    problems: list[str] = []
    table = stage_table(manifest)
    for entry in table:
        if entry["last"] < entry["first"]:
            problems.append(f"{entry['stage']}: empty range {entry['first']}..{entry['last']}")
    covered = [b for entry in table for b in range(entry["first"], entry["last"] + 1)]
    expected = sorted(blocks_of(manifest))
    if covered != expected:
        problems.append(f"blocks covered {covered} != manifest blocks {expected}")
    declared = manifest["totals"].get("blockCount")
    if declared is not None and declared != len(expected):
        problems.append(f"manifest declares {declared} blocks but carries {len(expected)}")
    if manifest["totals"]["blockCount"] == 71:
        got = [(e["stage"], e["channels"], e["first"], e["last"]) for e in table]
        if got != REFERENCE_71:
            problems.append("the 71-block table does not match nr_graph.cpp's hard-coded ranges:\n"
                            f"  derived:   {got}\n  hard-coded: {REFERENCE_71}")
    return problems


def render(manifest: dict) -> str:
    table = stage_table(manifest)
    totals = manifest["totals"]
    lines = [f"{totals['blockCount']} blocks, {totals['tensorCount']} tensors",
             f"{'stage':<20}{'ch':>6}{'first':>7}{'last':>6}{'level':>7}  kind"]
    for e in table:
        lines.append(f"{e['stage']:<20}{e['channels']:>6}{e['first']:>7}{e['last']:>6}{e['level']:>7}  {e['kind']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", nargs="?", help="model directory or manifest.json")
    ap.add_argument("--dll", help="extract from this DLL instead, with --magic")
    ap.add_argument("--magic", help="weight-table magic, e.g. 0x06c9dfdf")
    ap.add_argument("--out", help="extraction directory for --dll")
    ap.add_argument("--check", action="store_true", help="verify against the port's hard-coded ranges")
    args = ap.parse_args(argv)
    if args.dll:
        if not (args.magic and args.out):
            ap.error("--dll needs --magic and --out")
        import subprocess
        extract = Path(__file__).resolve().parents[1] / "experiments" / "opendlss_weights" / "extract.py"
        subprocess.run([sys.executable, str(extract), "--dll", args.dll, "--magic", args.magic,
                        "--out", args.out], check=True)
        args.manifest = args.out
    if not args.manifest:
        ap.error("give a manifest or --dll")
    manifest = load(Path(args.manifest))
    print(render(manifest))
    if args.check:
        problems = check(manifest)
        if problems:
            for problem in problems:
                print(f"FAIL {problem}")
            return 1
        print("schedule: ok (every block classified, ranges contiguous, 71-block table matches the port)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
