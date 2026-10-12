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

* `rebuild.sh` (2026-10-12, commit 7b9d4dd): one script for apply + build + stamp check,
  defaulting to the staged copy. It exists because the apply and the build were two commands and, when only the
  first ran, nothing failed - the apply script is idempotent - and the run used the previous
  binary. The check asks `build/dlss5vk stamp`, not the build's exit status, so a build that
  "succeeded" on a stale tree cannot pass it. Verified end to end here against a pristine
  clone of 9d08f41: 15 shaders, 78 PTX kernels, stamp `patch c2c4279a9623`, no GPU needed for
  the stamp itself.
* Verified: `uv run pytest tests/ -q` 306 passed / 15 skipped; with
  `NS_ODL_NATIVE_BIN=/opt/data/tmp/odl-verify3/build/dlss5vk` (the freshly rebuilt binary)
  and `GLSLANG` set, 311 passed / 11 skipped - the native-serve tests drive the new binary.
* The policy entry is checked by a test now (`test_the_example_policy_can_rebuild_the_port`):
  the entry has to be in the example, its argv has to name a file that exists in the repo and
  is executable, and the default port directory has to be the staged copy. The silent failure
  this guards is the one that produced `g`.
* Temporal history, step one (retired here, commit 4d3b7ec): serve now feeds the frame it published last back
  as lanes 7-9. It is `expandRgba8ToProxy` of `imageBuffer` into a `historyProxy` buffer at the
  top of the frame - one dispatch, no host bytes - and `preprocess.comp` gained a history
  binding plus a `historyValid` push field: with a history it samples lanes 7-9 from it, without
  one it repeats the current proxy, which is what it always did. The reprojection is the
  identity because this path is handed no motion; a reset and a bypass frame drop the history.
* Parity is untouched by construction, not by argument: `main.cpp` passes no history, so its
  features are the first-frame ones it always compared. That is why this did not need handing back.
* The patch commit is c2c4279a9623; the composite still does not blend the history, so the
  temporal half of the loop (the blend, and motion) is the next step after item 1.
* Re-measure the history (retired here, r2026-10-12-b): the port rebuild landed - r2026-10-12-a exited 0 in 7.2s and stamped `port 9d08f41 (12 modified) patch c2c4279a9623`, the binary answering for itself, so the staged port matches the checkout. b is queued, the same shape as c: read its per-frame `network+composite` against c at 13.1ms and check the `worker:` line carries no OUT OF SYNC.
  The plan block for b omitted the --save-before/--save-after flags that c learned are what make the declared before/after artifacts actually appear, so the queued args carry them; that does not touch the timing.
