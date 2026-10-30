# The 310.9.16 small network: extracted layout

Generated from `/tmp/model-fp8/manifest.json` (extract.py --magic 0x06c9dfdf).
This is the shape the port would have to execute; the existing graph is 71 blocks of one
197,184-byte layer each, so this is a different schedule, not a renumbering.

totals: 31 blocks, 77 tensors, 11 stages, fieldSplit 28

| block | tensors | names and byte lengths |
|---|---|---|
| 0 | 1 | block0.layer0.layer (21,696) |
| 1 | 1 | block1.layer0.layer (20,672) |
| 2 | 1 | block2.layer0.layer (22,720) |
| 3 | 1 | block3.layer0.layer (61,760) |
| 4 | 1 | block4.layer0.layer (69,936) |
| 5 | 1 | block5.layer0.layer (197,184) |
| 6 | 1 | block6.layer0.layer (229,936) |
| 7 | 1 | block7.layer0.layer (689,232) |
| 8 | 1 | block8.layer0.layer (820,288) |
| 9 | 4 | block9.layer0.layer (524,288)<br>block9.layer1.layer (263,168)<br>block9.layer2.layer (917,568)<br>block9.layer3.layer (263,168) |
| 10 | 5 | block10.layer0.layer (524,288)<br>block10.layer1.layer (263,168)<br>block10.layer2.layer (917,568)<br>block10.layer3.layer (263,168)<br>block10.layer4.layer (524,304) |
| 11 | 5 | block11.layer0.layer (4,194,320)<br>block11.layer1.layer (4,196,352)<br>block11.layer2.layer (3,145,856)<br>block11.layer3.layer (2)<br>block11.layer4.layer (1,050,624) |
| 12 | 5 | block12.layer0.layer (4,194,320)<br>block12.layer1.layer (4,196,352)<br>block12.layer2.layer (3,145,856)<br>block12.layer3.layer (2)<br>block12.layer4.layer (1,050,624) |
| 13 | 5 | block13.layer0.layer (4,194,320)<br>block13.layer1.layer (4,196,352)<br>block13.layer2.layer (3,145,856)<br>block13.layer3.layer (2)<br>block13.layer4.layer (1,050,624) |
| 14 | 5 | block14.layer0.layer (4,194,320)<br>block14.layer1.layer (4,196,352)<br>block14.layer2.layer (3,145,856)<br>block14.layer3.layer (2)<br>block14.layer4.layer (1,050,624) |
| 15 | 5 | block15.layer0.layer (4,194,320)<br>block15.layer1.layer (4,196,352)<br>block15.layer2.layer (3,145,856)<br>block15.layer3.layer (2)<br>block15.layer4.layer (1,050,624) |
| 16 | 5 | block16.layer0.layer (4,194,320)<br>block16.layer1.layer (4,196,352)<br>block16.layer2.layer (3,145,856)<br>block16.layer3.layer (2)<br>block16.layer4.layer (1,050,624) |
| 17 | 5 | block17.layer0.layer (4,194,320)<br>block17.layer1.layer (4,196,352)<br>block17.layer2.layer (3,145,856)<br>block17.layer3.layer (2)<br>block17.layer4.layer (1,050,624) |
| 18 | 5 | block18.layer0.layer (4,194,320)<br>block18.layer1.layer (4,196,352)<br>block18.layer2.layer (3,145,856)<br>block18.layer3.layer (2)<br>block18.layer4.layer (1,050,624) |
| 19 | 1 | block19.layer0.layer (525,312) |
| 20 | 4 | block20.layer0.layer (524,288)<br>block20.layer1.layer (263,168)<br>block20.layer2.layer (917,568)<br>block20.layer3.layer (263,168) |
| 21 | 4 | block21.layer0.layer (524,288)<br>block21.layer1.layer (263,168)<br>block21.layer2.layer (917,568)<br>block21.layer3.layer (263,168) |
| 22 | 1 | block22.layer0.layer (820,784) |
| 23 | 1 | block23.layer0.layer (689,232) |
| 24 | 1 | block24.layer0.layer (230,176) |
| 25 | 1 | block25.layer0.layer (197,184) |
| 26 | 1 | block26.layer0.layer (70,048) |
| 27 | 1 | block27.layer0.layer (61,760) |
| 28 | 1 | block28.layer0.layer (22,784) |
| 29 | 1 | block29.layer0.layer (20,672) |
| 30 | 2 | block30.layer0.blend_scale (2)<br>block30.layer0.layer (21,808) |
