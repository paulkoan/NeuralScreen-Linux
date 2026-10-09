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

**Resolved since the first pass.** The field split is **40 + 16**, and it is not a
choice: each record's u64 at +0 and its u64 at +8 both equal its payload length plus
40, in **153 of 153** records. `--fields` still takes any of the four, because all four
fit every offset; the data prefers one, and the tool now defaults to it.

**The lengths are OpenDLSS-NR's own layout.** `docs/weights.md` gives a record's byte
length as a sum of shapes and says reproducing every `byteLength` exactly "is the check
that the layout is right". Against our 153 lengths that check passes with **delta 0 for
every block**, variants included:

- **block 0** — `preFusedLayout`: base + the `16 -> 32` f16 adapter. Predicted 20,672 +
  16x32x2 = **21,696**, measured 21,696.
- **blocks 1, 2, 3** — base, 32 channels: 20,672. **4** — `2C -> C` upsample: 22,720.
- **5-7** — base, 64 channels: 61,760. **8** — transition: 69,936.
- **9-13** — base, 128 channels: 197,184. **14** — transition: 229,936.
- **15-21** — base, 256 channels: 689,232. **22** — transition: 820,288.
- **23-30** — four records: 524,288 / 263,168 / 917,568 / 263,168, and block 30's
  layer4 is the `512 -> 1024` matrix at 524,304.
- **31-38** — five records, the ViT: 4,194,320 / 4,196,352 / 3,145,856 / 2 / 1,050,624.
- **39 layer0** — the `1024 -> 512` matrix plus its skip scale: 525,312.
- **48, 56, 62, 66** — the decoder-stage-first blocks. Each measures 2C² + 2C − 32 over
  base for C ≥ 64 (48: 820,784; 56: 230,176; 62: 70,048) — exactly the `2C -> C` matrix
  plus the second skip scale, less two 16-byte pads. At C = 32 (block 66, 22,784) the
  same reading is 32 bytes short, which is not explained.

**Still open:**

- The documented 16-byte zero pads are not zero in these native bytes, at any of the
  three predicted offsets. So the native form is the MMA *fragment* packing the host
  walks, not the plain-matrix form it writes — which is what `weights.md` describes —
  but a byte-identical round trip is not shown.
- The fourth u64 of each record is not crc32, adler32, or a plain sum of its payload.
- **block 70** measures 21,808, which is 1,136 over base, where the two blend scales
  and the `32 -> 4` f16 head account for 384. It also carries a separate 2-byte
  `blend_scale` record. Unexplained.

## Running it

```
uv run python experiments/opendlss_weights/extract.py                 # report
uv run python experiments/opendlss_weights/extract.py --fields 40     # a different split
uv run python experiments/opendlss_weights/extract.py --out /tmp/odl  # emit a model dir
```

**The weights stay out of git.** They are NVIDIA's, the DLL they come from is already
gitignored, and 141 MiB has no business in a repository. Point `--out` at somewhere
outside the tree.
