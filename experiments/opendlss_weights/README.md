# Where the weights are, and why this is a parsing job

The question this answers: OpenDLSS-NR (an MIT Vulkan reimplementation of the DLSS 5
Neural Rendering network, bit-exact against the original) ships the engine but not the
model — "you supply the weights", 141 MiB of packed E4M3 in a documented layout. Do we
have them?

**Yes, in `native/nvngx_dlssnr.dll`, indexed by name.** And the extraction is parsing,
not reverse-engineering.

## What was measured

| | |
|---|---|
| `nvngx_dlssnr.dll` | 165,840,496 bytes (158.2 MiB) |
| its `.rsrc` section | 147,697,152 bytes (140.9 MiB) |
| resources in it | two — a VERSION block and one **RCDATA** leaf |
| that leaf | **147,695,410 bytes**, magic `0x08CDA732` |
| tensor records in it | **153**, named `blockN.layerM.parameter` |
| distinct blocks | **71**, block0…block70 |
| parameters seen | `layer`, `blend_scale` |
| sum of declared payloads | 147,683,778 bytes = **140.84 MiB** |
| table overhead | 11,632 bytes |
| first record | `block0.layer0.layer`, payload 21,696 bytes |

Two numbers line up with OpenDLSS-NR's own documentation: its manifest requires
`totals.blockCount: 71` ("a model with a different block count is refused at load") and
it describes its weights as "141 MiB". We have 71 blocks and 140.84 MiB of payload.

`python experiments/opendlss_weights/extract.py` prints all of the above from the DLL,
and `--out DIR` writes a model directory in OpenDLSS-NR's layout: `manifest.json` plus
`model/stageNN.bin`, with per-stage SHA-256, `totals.blockCount`, and one record per
tensor carrying `name`, `block`, `layer`, `parameter`, `stage`, `stageOffset`,
`byteLength`.

## The record format

The blob is a u32 magic followed by records of

```
[16 bytes: 0 | <prev payload/2> | <name length> | 0]
[name: exactly <name length> bytes, no terminator]
[56 bytes of per-record metadata, of which the u64 at +16 is the payload length]
[payload]
```

The name length has to come from that field: there is no separator, so
`block10.layer0.layer` runs straight into the following metadata whenever the next
byte happens to be a letter — a regex alone reports names with stray trailing
characters like `block10.layer0.layerh`.

## Verified, and not

**Verified:**

- The DLL is the weight carrier: 140.9 MiB of `.rsrc`, one RCDATA leaf, 99.99% of it
  declared tensor payload.
- 153 records, 71 blocks, block0…block70, names in OpenDLSS-NR's own convention.
- Every record's declared payload length lands exactly where the next record's name
  begins — for all 152 consecutive pairs, not a sample.
- The payload total, 140.84 MiB, against the documented 141 MiB.

**Not verified, and it matters:**

- **The payload's start is ambiguous within 24 bytes.** The 56 bytes of per-record
  metadata can be split four ways (32+24, 40+16, 48+8, 56+0) and every one of them
  reproduces all 153 next-record offsets, because they all sum to 56 and the payload's
  *end* is what is pinned. The declared length is unambiguous; which 21,696 bytes of a
  21,752-byte region are the payload is not. `extract.py` reports this rather than
  picking one silently.
- Whether the payload's internal ordering is the fused layout OpenDLSS-NR documents
  (`docs/weights.md`: expand, contract, padding, ffnCosSkip, padding, qkv, relative,
  scale, projection, attnCosSkip, then 16 bytes or a transition matrix) and the MMA
  fragment packing `packedWeightIndex(k, n, N)`.

Both open questions are the same job: compute the documented layout's byte length for a
known block and compare it against the length this tool reads. Block 0 is the useful
case — 32 channels, dense, no experts, and OpenDLSS-NR documents its variant separately
(`preFusedLayout`, an extra `16 -> 32` f16 adapter). A length match there fixes the
field split *and* confirms the internal order in one step. The numbers to check against
are 21,696 (block 0), 20,672 (block 1), 197,184 (blocks 10-13 and 9) and 69,936 (block 8).

## Running it

```
uv run python experiments/opendlss_weights/extract.py                 # report
uv run python experiments/opendlss_weights/extract.py --fields 40     # a different split
uv run python experiments/opendlss_weights/extract.py --out /tmp/odl  # emit a model dir
```

**The weights stay out of git.** They are NVIDIA's, the DLL they come from is already
gitignored, and 141 MiB has no business in a repository. Point `--out` at somewhere
outside the tree.
