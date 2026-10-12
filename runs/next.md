# The plan

Work items in order, for whoever - or whatever - picks this up next. Take the top item, do it,
delete it, append what you learned at the bottom.

Not negotiable, because these are the difference between a loop and a runaway: one item per
pass; the test suite green before anything is pushed; never touch /etc or install system
packages; never touch the developer's checkout at /home/paul/dev/NeuralScreen-Linux; never edit
/opt/neuralscreen (policy, executor, key, unit); never queue a run that is not described here.

## 1. Rebuild the port, then measure the blend

The composite now blends the history - `weight = clamp(sigmoid(head.a) * blend_scale, 0, 1)`,
`neural = lerp(proxy + head.rgb / 4, history, weight)`, docs/frame.md's composition - and the
developer asked for it before any motion work. `r2026-10-12-c` (port-build) is queued. Read the
journal line first:

    stamp: port 9d08f41 (12 modified) patch 08e297c8a802f2642dadf402dcfd25ae7ae58d70

If it names `c2c4279a9623` instead, the rebuild did not take and the measurement below would be
of the blend-free binary. Then queue this - the same shape as `r2026-10-12-b`:

    {"id": "r2026-10-12-d", "entry": "minimal",
     "args": ["--source", "image", "--input-image", "fixtures/youtube-1440p.png",
              "--headless", "--frames", "60", "--worker-log", "--shm", "--no-motion",
              "--send-ahead", "2", "--save-before", "before.png", "--save-after", "after.png"],
     "timeout_s": 300, "artifacts": ["before.png", "after.png"],
     "note": "the blend's cost and what it does to a still picture, against b's 12.2/12.0ms"}

What to read, in order:

1. `serve: blend scale 0.7397 (block70.layer0.blend_scale)` in the worker log. If it says
   "absent - defaulted to 1.0" the weight is not the model's and the numbers mean something
   else.
2. The per-frame `network+composite` against b's 12.2/12.0ms and c's 13.1/13.1ms. The blend is
   one fma and one exp2 per pixel inside the dispatch that already exists, so anything beyond
   noise means something is wrong with the claim that it is free.
3. Whether a still picture drifts. Every frame of this fixture is the same image, so the
   history the blend reads is very nearly the frame it is blending into, and the result should
   land close to the unblended one. Compare its `after.png` with b's -
   `git show origin/results:runs/done/r2026-10-12-b/after.png > /tmp/b-after.png` and
   `uv run python tools/frame_diff.py` - and say the mean absolute difference in the report. A
   large difference means the blend is doing something structural rather than a mild temporal
   filter, which is worth knowing before any motion vectors exist.

Also on the record: the blend keeps parity by construction (`main.cpp` passes no history, so it
cannot see the blend) and the arithmetic is checked by
`uv run python experiments/opendlss_port/check_composite.py` - 4000 random cases, the shader
against `src/main.cpp`'s `composed()` with no history and against the demo's composite with one.

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
