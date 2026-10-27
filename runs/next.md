# The plan

Work items in order, for whoever - or whatever - picks this up next. Take the top item, do it,
delete it, append what you learned at the bottom.

Not negotiable, because these are the difference between a loop and a runaway: one item per
pass; the test suite green before anything is pushed; never touch /etc or install system
packages; never touch the developer's checkout at /home/paul/dev/NeuralScreen-Linux; never edit
/opt/neuralscreen (policy, executor, key, unit); never queue a run that is not described here.

## 2. Ask first - do not start these alone

* Decided (2026-10-11): the fixture keeps the whole frame. No crop.
* The container: it needs nvidia-container-toolkit, a system package. The developer's call.
* Anything touching /etc, system packages or the box's configuration. Every time.

## Learned

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
