# The 310.9.16 small network: the same architecture, fewer blocks per level

`tools/nr_schedule.py` derives the recorder's stage table from a model manifest instead of
reading it off six hard-coded ranges in `nr_graph.cpp`. Run against both networks extracted
from the 310.9.16 DLL, it settles the integration question the plan had been carrying:

| | large (magic 0x08cda732) | small (magic 0x06c9dfdf) |
|---|---|---|
| blocks | 71 | 31 |
| tensors | 153 | 77 |
| payload | 140.84 MiB | 108.61 MiB |
| blend_scale | 0.73974609375 | 0.76708984375 |

Every block in the small network has a byte length the large one also has, and the layout
formula that produces them (`fusedLayout(channels).endWithoutPadding + 16`, the transition
variants and the five-record 512/ViT blocks) is the same one `nr_graph.cpp` already
implements. So the small network is **not a second schedule**: it is the same six-level
U-Net with the same eight-block ViT bottleneck, the same encoder/decoder channel ladder
(32, 64, 128, 256, 512, ViT 1024) and the same post block, with fewer blocks inside each
level.

## Stage tables

Derived, both networks, `tools/nr_schedule.py --check`:

large:

| stage | ch | first | last | level |
|---|---|---|---|---|
| pre | 32 | 0 | 0 | 0 |
| encoder-32 | 32 | 1 | 4 | 0 |
| encoder-64 | 64 | 5 | 8 | 1 |
| encoder-128 | 128 | 9 | 14 | 2 |
| encoder-256 | 256 | 15 | 22 | 3 |
| encoder-512 | 512 | 23 | 30 | 4 |
| vit | 1024 | 31 | 38 | 5 |
| transition-38-39 | 512 | 39 | 39 | 4 |
| decoder-512 | 512 | 40 | 47 | 4 |
| decoder-256 | 256 | 48 | 55 | 3 |
| decoder-128 | 128 | 56 | 61 | 2 |
| decoder-64 | 64 | 62 | 65 | 1 |
| decoder-32 | 32 | 66 | 69 | 0 |
| post | 32 | 70 | 70 | 0 |

That table is byte-for-byte the ranges `nr_graph.cpp` hard-codes (a test asserts it), which
is what makes the derivation trustworthy.

small:

| stage | ch | first | last | level |
|---|---|---|---|---|
| pre | 32 | 0 | 0 | 0 |
| encoder-32 | 32 | 1 | 2 | 0 |
| encoder-64 | 64 | 3 | 4 | 1 |
| encoder-128 | 128 | 5 | 6 | 2 |
| encoder-256 | 256 | 7 | 8 | 3 |
| encoder-512 | 512 | 9 | 10 | 4 |
| vit | 1024 | 11 | 18 | 5 |
| transition-38-39 | 512 | 19 | 19 | 4 |
| decoder-512 | 512 | 20 | 21 | 4 |
| decoder-256 | 256 | 22 | 23 | 3 |
| decoder-128 | 128 | 24 | 25 | 2 |
| decoder-64 | 64 | 26 | 27 | 1 |
| decoder-32 | 32 | 28 | 29 | 0 |
| post | 32 | 30 | 30 | 0 |

## What this changes

* The loader's `blockCount` guard was the only hard blocker and is already a member
  variable. What is left is the six hard-coded ranges (and two ViT-chain constants keyed on
  block 38), which become this table.
* Nothing in the schedule depends on a block index being 71 or 31: window phases advance per
  block at a level, the encoder/decoder transition tensors are identified by their kinds, and
  the ViT bottleneck is eight blocks in both networks.
* `blend_scale` is 0.76708984375 in the small network, not 0.7397. It must keep being read
  from `block30.layer0.blend_scale` rather than written into the source.
* Byte lengths are the classifier's only input, so the same tool covers both networks and
  will reject a block it cannot lay out instead of guessing.

## Rebuilding the manifests

Neither DLL nor the extracted models belong in the repository. To reproduce:

```
python experiments/opendlss_weights/extract.py --dll <310.9.16 dll> --magic 0x08cda732 --out /tmp/model-big
python experiments/opendlss_weights/extract.py --dll <310.9.16 dll> --magic 0x06c9dfdf --out /tmp/model-fp8
python tools/nr_schedule.py /tmp/model-fp8 --check
```
