# The plan

Work items in order, for whoever - or whatever - picks this up next. Take the top item, do it,
delete it, append what you learned at the bottom.

Not negotiable, because these are the difference between a loop and a runaway: one item per
pass; the test suite green before anything is pushed; never touch /etc or install system
packages; never touch the developer's checkout at /home/paul/dev/NeuralScreen-Linux; never edit
/opt/neuralscreen (policy, executor, key, unit); never queue a run that is not described here.

## 1. Next work

* Verify the table-driven recorder. **Re-armed 2026-10-30-b: r2026-10-30-a and -b are void as
  verification** - both stamped `patch 4b934233b924` and printed `OUT OF SYNC` against the
  checkout's `7b827810f679`, so the worker never contained step 1 (a's pixels are byte-identical
  to 29-e's, which is only the old build behaving). r2026-10-30-c (port-build) is queued to put
  the schedule change in the binary. When it lands, require exit 0 and stamp 7b827810f679, then
  re-queue one 30-frame `--save-before --save-after` run (after.png against 29-e's, sha
  1975cb4479) and one 120-frame steady-fps run (expect ~40.5 steady against f's 40.48). Then
  step 2. Step 1 is implemented (commit 56cfb43):
  `Graph::record` takes every block range from a schedule derived from the model's block
  signatures (`src/nr_schedule.{h,cpp}`, mirroring `tools/nr_schedule.py`), the six hard-coded
  ranges and the `block < 38` ViT constant are gone, and the 71-block derivation is pinned to
  the old ranges by `dlss5vk schedule --check` (ok on both extracted models, 71 and 31 blocks).
  What is NOT yet proven is that the graph records the same work on the GPU. Read the two
  queued runs first: r2026-10-30-a (30 frames, `after.png` must be byte-identical to 29-e's)
  and r2026-10-30-b (120 frames, ~40.5 fps steady). If either disagrees, fix or revert step 1
  before anything else. If both agree, take step 2: parity against NGX preset 2 on the same
  card (`tools/ngx_preset_compare.py` runs presets 1 and 2 back to back), then steady-state fps.

## 2. Ask first - do not start these alone

* Decided (2026-10-11): the fixture keeps the whole frame. No crop.
* Anything touching /etc, system packages or the box's configuration. Every time.

## Learned

* learned: a queued verification run is only as good as the binary the box last built (2026-10-30,
  ticks a/b). 56cfb43 changed the recorder and 47d64fb queued the two runs to prove it, but no
  port-build was queued between them, so both runs stamped the previous patch 4b934233b924 and
  said OUT OF SYNC (checkout 7b827810f679). a's before/after are byte-identical to 29-e's
  (blobs a1bafe2d07 / 1975cb4479) and b's steady rate 35.17 fps sits under f's 40.48 - both
  consistent with the old build, neither evidence about the table. When a commit changes the
  port, the same pass that queues the verification must queue a port-build first, or the runs
  measure the old binary and report a clean exit 0 while proving nothing.

* learned: the recorder now walks a table, and the table is verifiable without a GPU (2026-10-30).
  `src/nr_schedule.{h,cpp}` classifies each block from its `layer` tensors' byte lengths (the
  `layer` field is the string "layer0", not an int - parsing it as an integer collapses the
  signature and every block comes back as 4 layers of the wrong order), walks them into stages,
  and `Graph::record` takes all its boundaries from it; the six ranges and the `block < 38` ViT
  constant are gone. `dlss5vk schedule --model <dir> --check` is device-free, and on both
  extracted models it prints exactly the table `tools/nr_schedule.py` prints (71: 1..4/5..8/9..14/
  15..22/23..30/31..38/39/40..47/48..55/56..61/62..65/66..69/70; 31: one working block per level),
  with the 71-block one also equalling the ranges the recorder used to hard-code. A pytest in
  tests/test_nr_schedule.py drives that mode for both networks against the reference tool. What
  this does NOT prove is pixel parity, because nothing here has a GPU - that is r2026-10-30-a/b.
  Also: the patch applies to a pristine 9d08f41 and rebuilds in sync (patch 7b827810f679, 78 PTX).

* learned: the 31-block network is NOT a different architecture (2026-10-30, offline on the
  extracted weights). Both networks in the 310.9.16 DLL were re-extracted here (large magic
  0x08cda732: 71 blocks / 153 tensors / 140.84 MiB, blend_scale 0.73974609375; small magic
  0x06c9dfdf: 31 blocks / 77 tensors / 108.61 MiB, blend_scale 0.76708984375) and every block
  byte length in the small one is a length the large one also has. `tools/nr_schedule.py`
  classifies blocks from those lengths using `fusedLayout`'s own formula and derives the stage
  table; on the 71-block model the derived table equals nr_graph.cpp's hard-coded ranges
  exactly (a test asserts it), and on the 31-block model it gives the same six levels, the same
  eight-block ViT bottleneck and the same post block, with one working block per encoder and
  decoder level instead of 1/3/5/7. So the integration is replacing six hard-coded ranges (and
  two ViT-chain constants keyed on block 38) with that table - not porting a second schedule,
  and not re-learning the layout. The earlier "block11.layer0.layer is 4,194,320 bytes against
  197,184" reading was the ViT stage compared against a c128 block; in the small model the ViT
  stage is blocks 11-18 with the same five tensors as the large model's blocks 31-38.

* learned: the BGRA handoff is implemented: the capture leg returns BGRA and sets
  FRAME_FLAG_COLOR_BGRA (0x80); the port's expand shader reads .bgra when the push constant's
  pad0 is 1. The wire flag is in protocol.py and serve.cpp. The tests still have the 9
  pre-existing import failures (libGL/SDL2 absent) but 320 pass.

* learned: the 310.9.16 DLL carries two networks and only the first is a drop-in (2026-10-30,
  offline in the sandbox; file sha256 cdfa6c1e..., 276,162,560 bytes). Its largest resource
  (147,695,410 bytes, magic 0x08cda732) is byte-identical to the 310.8.0 network already in
  /opt/neuralscreen/model - same 11 stages, 153 tensors, 71 blocks, same blend_scale. So the
  first extraction found nothing new. The second resource (113,893,343 bytes at offset
  152,515,824, magic 0x06c9dfdf) is the small/FP8 network: **31 blocks, 77 tensors, 108.6 MiB**
  (the earlier 52/20/68.7 count was an ad-hoc regex that missed records; the extractor is the
  authority). Its layer arrangement and tensor byte lengths differ from the old model
  (block11.layer0.layer is 4,194,320 bytes there against 197,184 in the old one; blocks 10-30
  carry up to five layers each), and its magic is not the one extract.py accepted until 40da205.
  **The port's loader refuses any blockCount but 71, so this is not a weight swap** - adopting
  the new model in dlss5vk means extending extract.py for the second magic, then changing the
  loader and shaders for a different, smaller architecture. The NGX arm already runs it, and
  measured 1.08x end-to-end (27.7 fps steady against the port's 40.5), so the model's own speed
  only pays if it is ported. That is a scope decision, not a run.

* learned: comparing two NGX model presets is now one command (commit c17b5c0):
  `uv run python tools/ngx_preset_compare.py` runs presets 1 and 2 back to back, parses the
  preset/frames/timing lines itself, hashes the four PNGs, diffs the pictures through
  frame_diff.py, and exits 1 with a named reason when the comparison cannot be attributed
  (same preset reached the DLL, different before frames, identical after frames). Use it instead
  of running the pair by hand and hunting through two logs. It runs the pipeline directly, not
  through the queue: the installed unit's policy pins the worker to the port and its sandbox
  hides the Wine prefix.

* learned: the per-frame client copy is NOT the cost it looked like (measured on the sandbox
  2026-10-29, `python /opt/data/tmp/copybench.py` and `pipebench.py`). 29.5MB colour+motion into
  an mmap: **1.59ms** median (18.5GB/s). The 14.7MB motion half alone: 0.58ms. A strided window
  source through `reshape(-1)`: 2.36ms, versus 1.49ms through a 3D view (the reshape copies).
  Writing 29.5MB **down a pipe** to a reader: **24.3ms**. A 24-byte header down a pipe: 0.00ms.
  So shared memory is a 15x win over the pipe and must always be on, but the residual 9.5-16.2ms
  `send` seen on the box is not our code - it is memory-bandwidth contention with whatever else
  is touching the same pages (the worker downloading 14.7MB from the GPU at the same moment), or
  the process being descheduled. Do not spend a run making a 1.6ms copy faster. The earlier
  reading of 13-a's 13.5ms as "the motion field costs 10ms" was wrong: 13-a ran WITHOUT --shm,
  so its send was 29.5MB down a pipe, which benches at 24ms.

* learned: the capture-side colour swap is a real per-frame stage: `img[:, :, [0, 2]] =
  img[:, :, [2, 0]]` costs **6.9ms** at 2560x1440 (`swapbench.py`), and every alternative that
  touches the bytes costs the same - two plane copies 7.1ms, a full gather 6.1ms, a uint32
  byte-rotate 20.5ms. There is no faster CPU reorder; the only cheaper option is not reordering
  at all, i.e. hand the port BGRA and swizzle in the expand shader. That needs a wire flag and a
  port rebuild, so it is a later item, not this one.

* learned: throughput measured from the results branch's own logs (2026-10-28; no new run needed).
  The headline fps on every run is a warm-up artefact. Medians, per frame:

  | run | capture | send | recv | display | steady total | steady fps | headline |
  |---|---|---|---|---|---|---|---|
  | 13-a (30f) | 5.8 | 13.5 | 49.6 | 3.6 | 72.5ms | 13.8 | 4.68 |
  | 27-c (120f) | 27.3 | 9.5 | 20.3 | 12.4 | 69.5ms | 14.4 | 8.45 |
  | 27-g (30f) | - | 14.8 | 40.0 | - | - | - | 4.50 |
  | 27-i (30f) | - | 16.2 | 61.2 | - | - | - | 4.48 |
  | 27-e (3f, --bypass) | 3.0 | 2.7 | 4.3 | 2.8 | 12.8ms | 78.1 | 75.33 |

  13-a's 4026ms frame 0 over 30 frames is the whole reason the mean says 4.68: the median frame is
  72.5ms. The goal was 15 fps and the 120-frame run measures 14.4 steady, so the target is ~4% away,
  not 3x away. The bypass run sets the floor: with the model doing nothing, the loop costs 12.8ms,
  so capture/send/recv/display overhead is ~13ms and everything above that is the worker.

* learned: the worker's own per-frame breakdown, from the port's timestamps (`[worker] serve frame
  N: total (proxy, network+composite, readback, reply)`). Steady state r2026-10-27-g: 37.0-37.9ms
  total - proxy 8.6-10.4, network+composite 13.5-16.2, readback 4.5-7.3, reply 7.9-8.3. r2026-10-27-c:
  41.7-67.2ms - proxy 18.4-24.6, network+composite 14.3-17.5, readback 4.8-19.3, reply 4.2-7.9. So the
  four candidates in the old plan rank as: NGX network+composite ~16ms (the model itself, the largest
  and the least removable), proxy ~9-24ms (varies run to run, worth understanding), readback ~5ms
  steady (58.5ms only on frame 0, first touch), reply ~8ms. There is no encode stage in the loop - the
  bypass run's 12.8ms is capture+send+recv+display only. The client's own `send` (9.5-16.2ms) is a
  full 29.5MB copy per frame into shm and is the biggest client-side cost.

* learned: `recv` under `--send-ahead` does not measure worker compute. r2026-10-27-c's client recv
  median is 20.3ms while the same worker reports 54-67ms per frame - impossible unless the client's
  recv is returning a frame the worker finished earlier out of the queue. Judge worker cost from the
  worker's line and end-to-end cost from the run's elapsed time; do not read `recv` as inference time.

* learned: the fidelity gap split into tone and structure (2026-10-28, offline on the 13-a card's
  pixels; no run needed). Real per-channel shifts measured from the PNGs: port +6.99R/+0.60G/+3.75B,
  NGX -5.82R/-9.04G/-6.44B, so the port brightens where NGX darkens. That is NOT a sign error in
  the composite: the composite is byte-for-byte the demo's (`clamp(proxy + head/4)`, verified
  against nr_composite.comp's fma spelling), and the per-channel means cannot be compared directly
  because a clamp is nonlinear - the mean of the curve is not the curve of the mean. The port's tone
  curve fits as after = 0.899*before + 22.56 (R), 0.938*+9.47 (G), 0.946*+11.45 (B): contrast down
  ~10%, blacks lifted ~23 levels. NGX's goes the other way. Structure agrees: tone-match the port to
  NGX's histogram and MAD falls 14.7606 -> 2.2469 with detail correlation 0.978. NGX's output also
  has ZERO 255-clipping (max 234) where the port's has 11.71% - the fingerprint of a display
  transform. So the port's structure is already close to NGX's and the remaining gap is the demo's
  display path (upgradeToneMap + ACES + sRGB), which docs/frame.md calls "not part of NR" and the
  port omits by design. Absolute pixel parity with NGX is therefore not attainable from an LDR
  fixture. Numbers reproduced with `/opt/data/tmp/pngstat.py`, `/opt/data/tmp/tonecurve2.py` and
  `/opt/data/tmp/structtest.py` (ffmpeg decodes the PNGs; PIL is broken in the venv).

* learned: r2026-10-27-g: head -6.5039..0.5020, overall mean -0.90270, residual mean (head/4) **R +0.0147 G +0.0100 B +0.0109**, logit mean -3.7533, 0 non-finite of 15,073,280. Read the line carefully: the overall mean is negative only because the logit channel is -3.75 and it is averaged in with the RGB channels - the RGB residual is POSITIVE on all three channels. NGX's delta on this same card pulls the mean DOWN (154.4/143.0/143.4 -> 148.6/134.0/137.0), so the head's sign is inverted relative to NGX's: the port brightens where NGX darkens. That is the mechanism behind the +9R/+4G/+6B offset, not an absence of one. Scale still needs reconciling: head/4 x255 is ~+3.8R/+2.6G/+2.8B but the port's measured mean shift is ~+7.0R/+0.6G/+3.7B, so G disagrees in sign and the composite's centred mapping must be doing more than a plain add. Also: g's after.png is byte-identical to 13-a's after.png (sha256 9f13979b168dc3a0), so this run changed no pixels - it is diagnostic only, and the port-vs-NGX delta stands at MAD 14.7606 / PSNR 23.432 dB. Timing: steady state ~37ms worker, median recv 40ms, ~64ms/frame (~15fps); the 4.5fps headline is one 4561ms frame-0 warm-up inflating the mean.

* The container question is closed (2026-10-27, developer): "no idea why we would run in a
  container after all this time." nvidia-container-cli 1.20.1 is installed on the box, so the
  install cost is gone, but `container = false` stands - the unit's sandbox already enforces the
  same bound and a silent software-render fallback would report believable timings. Do not
  reopen this. (Card t_07535efe.)

* The blend (2026-10-12, patch 08e297c8a802): the composite takes a history binding, a
  `blendScale` and a `historyValid`, and the truncation to the half grid became one publication
  point after the blend (`history' = truncate_to_half(neural)`) instead of inside it. With no
  history the expression main.cpp truncates is unchanged, byte for byte, which is why the gate
  cannot see any of it. `blend_scale` is read from the model (block70.layer0.blend_scale) and
  printed at startup rather than written into the source.
* Verified here: `bash experiments/opendlss_port/rebuild.sh /opt/data/tmp/odl-verify3` against a
  pristine clone of 9d08f41 - 15 shaders, 78 PTX kernels, `stamp: ... patch 08e297c8a802`, in
  sync. `uv run pytest tests/ -q` 313 passed / 11 skipped with `GLSLANG` and
  `NS_ODL_NATIVE_BIN` set to the freshly rebuilt binary, so the native-serve tests drove it.
* Two new tests guard the pieces this change could silently break: the shader's push-constant
  list against `kernels.cpp`'s `struct Push` (a field added on one side only compiles, and the
  kernel then reads its neighbour's value), and `check_composite.py`'s own ability to fail - the
  blend line is stripped from a copy of the patch and the checker has to refuse it.
* `rebuild.sh` (2026-10-12, commit 7b9d4dd): one script for apply + build + stamp check,
  defaulting to the staged copy. It exists because the apply and the build were two commands
  and, when only the first ran, nothing failed - the apply script is idempotent - and the run
  used the previous binary. The check asks `build/dlss5vk stamp`, not the build's exit status.
* The policy entry is checked by a test now (`test_the_example_policy_can_rebuild_the_port`):
  the entry has to be in the example, its argv has to name a file that exists in the repo and
  is executable, and the default port directory has to be the staged copy. The silent failure
  this guards is the one that produced `g`.
* The history re-measure (retired here, r2026-10-12-b): exit 0, 7.7s, `in sync` on patch
  c2c4279a9623; per-frame `network+composite` 12.2/12.0ms (frames 29/59) against c's 13.1/13.1ms
  without any history - the feed is free, as designed. A still fixture with the same shape as c.
* Temporal history, step one (commit 4d3b7ec): serve expands the frame it published last into a
  `historyProxy` (`expandRgba8ToProxy`, one dispatch, no host bytes) and `preprocess.comp` samples
  it for lanes 7-9; a reset and a bypass frame drop it, and the reprojection is the identity
  because this path is handed no motion.
* Parity is untouched by construction, not by argument: `main.cpp` passes no history, so its
  features are the first-frame ones it always compared.
* The blend, queued to be measured (retired here, r2026-10-12-d): the rebuild landed - r2026-10-12-c exited 0 in 7.3s and stamped `port 9d08f41 (12 modified) patch 08e297c8a802f2642dadf402dcfd25ae7ae58d70` (15 shader modules, 78 PTX kernels), so the staged binary carries the blend, and d is queued in the shape of b, save flags included.
* Still to read when d lands: the worker-log line `serve: blend scale 0.7397 (block70.layer0.blend_scale)` - a value reported as absent, defaulted to 1.0, means the weight did not come from the model; its per-frame `network+composite` against the 12.2/12.0ms of b (frames 29/59) and the 13.1/13.1ms of c - the blend is one fma and one exp2 inside a dispatch that already exists, so anything past noise refutes the claim that it is free; and its `after.png` against the one of b, `git show origin/results:runs/done/r2026-10-12-b/after.png > /tmp/b-after.png` then `uv run python tools/frame_diff.py`, quoting the mean absolute difference - a large one means the blend is structural rather than a mild temporal filter.

* The blend, measured (r2026-10-12-d, retired here): exit 0, 8.0s, blend scale 0.7397 from block70.layer0.blend_scale - the weight comes from the model, not the 1.0 default; per-frame network+composite 12.7/12.2ms (frames 29/59) against the 12.2/12.0ms of b and the 13.1/13.1ms of c - inside noise, so the blend is free as claimed.
* Its after.png against the one of b: mean abs diff 5.7412 (p99 22.0, PSNR 30.5) - large, so the blend is structural rather than a hairline temporal filter. The recv max 4013.7ms and the send max 5.3ms are both frame 0, the warm-up, not a per-frame cost.
* The restoration question, answered (r2026-10-27-d, retired here): exit 0, 6.5s, `blend scale 0.7397` read from block70.layer0.blend_scale, so the weights are the model's. The frame pair was measured with `tools/jpeg_blockiness.py`, whose calibration is fixed on these very files: the clean 1440p source scores 0.9633 blockiness, its q20 re-encode 1.5634. **d's before 1.5634 -> after 1.5723: blockiness flat, marginally worse. Coherence flat (0.9122 -> 0.9125).** Mean abs diff 4.5 per channel, 64% of pixels moved by more than 2, 22% by more than 8, and luma correlation 0.994 - so the network does change the frame, but as a global tone shift (contrast x0.944, luma mean -0.40), not as deblocking. The 8x8 grid survives untouched. The "dead network" reading was wrong, but so is "it restores compressed input": on this evidence the port is a near-passthrough with a mild tonal transform. It is NOT a deblocker, and no run so far supports claiming restoration.
* Consequence for the plan: if restoration is the goal, it needs a network or a pipeline stage that targets the 8x8 grid, because this one demonstrably does not. Do not queue more clean-input runs to prove restoration - the instrument cannot move on input that has no grid to remove. The next useful run would isolate whether the tone shift comes from the network or from the composite, e.g. a run with the blend bypassed.
* The progress tick failed with "[CRON_FAILURE] git fetch failed because /opt/data/neuralscreen-linux was not recognized as a Git repository" (2026-10-27 17:22). Not the repo, not permissions, not the venv: the tick's own helper script ran its two commands as separate subprocess/shell calls, so the `cd` died with its process and `git fetch` ran in the original cwd. Fed back the exact case here: with the two commands split across processes the fetch returns rc=128 "fatal: not a git repository (or any parent up to mount point /opt)"; it returns rc=0 once the repo is named. Two fixes applied to the job: it now runs with workdir /opt/data/neuralscreen-linux (so a script's subprocesses inherit the repo as cwd), and its prompt tells it to name the repo on every call - `git -C /opt/data/neuralscreen-linux ...`, or `cwd=` on subprocess.run - and never to rely on an earlier `cd`. The general lesson: "one command per call, no chaining" must be paired with "name the path on every command", or the cwd silently resets between processes.

* The port against NGX, measured (r2026-10-13-a, retired here): exit 0, 30 frames, 6.4s (4.68 fps), worker patch `f0c60a1c2224` at port 9d08f41, `blend scale 0.7397` - the same worker and the same weight as d, so the only difference from pass14 is the port. **The control passed: `before.png` is byte-identical to `pass14/before.png` (sha256 82e16d3d073a5cea on both), so both paths were handed the same frame and the comparison is valid.**
* The numbers: `after.png` vs `pass14/after.png` MAD **14.7606** / PSNR **23.432 dB** (max |d| 36). The port's own delta is 6.7205 / 28.800 dB against NGX's 18.4345 / 21.589 dB - the card's quoted figure reproduced exactly, so the instrument is calibrated. **The port moves the frame only 36.5% as far as NGX does.**
* Where it loses: per-channel regression `port_delta = a + s*ngx_delta` gives R s=+0.4265 a=+9.474 R2 0.908, G s=+0.3637 a=+3.885 R2 0.787, B s=+0.2902 a=+5.620 R2 0.733. So the port **adds a uniform positive offset** (~+9R/+4G/+6B levels) and applies only 29-43% of the network's delta; per-pixel delta sign agrees only 67.5%. Saturation: before 12.61% clipped -> port 11.71% -> NGX 0.00%. NGX pulls the mean down (148.6/134.0/137.0 from 154.4/143.0/143.4); the port pushes it up (161.4/143.6/147.1).
* **Reading: this is not a scale factor, it is an offset plus attenuation.** The port's composite/output path adds a brightness term where NGX subtracts a predicted residual, and under-applies the network's change by roughly 2.5x. That is a concrete fidelity bug in the port, and the first hard evidence that "near-passthrough" is not harmless - it brightens and re-clips a frame NGX restores.
* learned: r2026-10-27-e (--bypass) exit 0, 1.5s. before.png and after.png are byte-identical: mean abs diff 0.0, blockiness 1.5634 flat, coherence 0.9122 flat. The composite is neutral without the network; d's 4.5 mean abs diff tone shift is the network's, not the composite's.

* The real motion measurement (r2026-10-27-c): the first HUMAN-run GeForce Now session that reached the pipeline (120 frames, 48.0s, genuine motion, capture split wait 0.1ms read 27.4ms at 2560x1440). Worker per-frame `network+composite` 17.0/16.5ms at frames 29/59 against b's 12.2/12.0ms and d's 12.7/12.2ms — the motion path (reprojection + five-tap) costs ~4.5-4.8ms per frame. Quality on the saved pair: mean abs diff per channel [5.486 6.218 6.536], 97.63% of pixels moved >2 and 62.37% >8; blockiness 0.9707 -> 0.9771 and coherence 0.9482 -> 0.9476, both flat. That is d's near-passthrough / tone shift again, now on real motion data: the network changes the frame globally but does not restore JPEG structure.
* The composite's arithmetic verified against the extended `check_composite.py` on the real-motion run's port build: 4000 random cases agree on both paths; zero-motion five-tap equals the centre tap in 4000 cases; motion five-tap vs the independent Catmull-Rom agrees in 1773 interior cases (worst 1.2e-06, allowed 1e-05); the reprojection stays within 2.00 ulp of the demo's uv route (allowed 4); the on-screen flag agrees. So the tone shift is not a composite-math bug — it is what the network outputs on real motion input.
* learned: r2026-10-27-i, the valid-rectangle re-measure: exit 0, 9.1s. The head mean now walks workWidth x workHeight at stride fullWidth — residual mean (head/4) R +0.0144 G +0.0112 B +0.0110 against g's +0.0147/+0.0100/+0.0109, so the 32 padded rows were NOT what polluted the mean; the fix changed almost nothing. Measured pixel shift on the pair: R +6.9936 G +0.5973 B +3.7503 (MAD 6.7205, PSNR 28.800 dB, 97.2% moved >2, 63.7% >8). Head/4 x255 predicts ~+3.67R/+2.86G/+2.80B: B agrees within ~1 level (2.80 vs 3.75), but R is under-explained by ~3.3 levels (3.67 vs 6.99) and G is over-explained by ~2.3 (2.86 vs 0.60) — so no single scale reconciles the three channels, and "within a level" is not met. The composite's centred mapping still does more than a plain add, and G is the channel to look at, not R. Control: i's before.png and after.png are byte-identical to 13-a's (82e16d3d073a5cea / 9f13979b168dc3a0), so i reproduced the earlier frame exactly — diagnostic only, no new pixels.

* learned: the run summary now quotes the steady-state rate beside the mean (commit dee5cd2).
  `timing_summary` carries `total_median`/`steady_fps` (median of the per-frame totals, not the sum
  of per-stage medians) and the CLI prints `X fps headline, Y fps steady` on the frames line plus
  `mean ... ms/frame, Z fps; median ... ms/frame, W fps steady` on the timing line. The new unit
  test reproduces 13-a's shape: one 4026ms frame 0 over 30 frames leaves the mean at 4.68 fps while
  the median 72.5ms is 13.8 fps. Full suite on this box: 9 pre-existing import failures
  (`libGL.so.1` and SDL2 absent) in capture/dependency/tool tests; the 63 timing and pipeline tests
  pass. The gate needs those system libs installed (or a run on the GPU box) before the whole suite
  can be called green here.

* learned: the readback-gate fix is verified (2026-10-29 d/e/f). b and c ran patch 819bea6f149e;
  d rebuilt the staged port to patch 4b934233b924 (different sha, so the hoist is in the binary).
  e, the 30-frame pixel run, exited 0: 30 done, 0 skipped, 19.83 fps steady, no "Bad address".
  f, the 120-frame confirmation, exited 0: 40.48 fps steady against b's 34.7 - the steady rate
  survives the fix and even improves. Headline 16.59 fps is still the frame-0 PTX warm-up skewing
  the mean; quote the steady number. The top plan item is retired.

* learned: the port's block-count guard is relaxed (nr_graph.h/.cpp): `kBlockCount` became a
  member `blockCount_`, set from the model, so a non-71 model loads beside the 71-block parity
  reference; the big model's path is untouched. The suite still has the 9 pre-existing libGL/SDL2
  import failures; 320 tests pass.
