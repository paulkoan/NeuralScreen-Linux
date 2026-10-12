# The plan

Work items in order, for whoever - or whatever - picks this up next. Take the top item, do it,
delete it, append what you learned at the bottom.

Not negotiable, because these are the difference between a loop and a runaway: one item per
pass; the test suite green before anything is pushed; never touch /etc or install system
packages; never touch the developer's checkout at /home/paul/dev/NeuralScreen-Linux; never edit
/opt/neuralscreen (policy, executor, key, unit); never queue a run that is not described here.

## 1. Re-measure the history, once the port has been rebuilt

The `port-build` entry is installed and the rebuild is queued as `r2026-10-12-a`. Read its
journal line first:

    stamp: port 9d08f41 (12 modified) patch c2c4279a9623

That is the binary's own answer; if it names the previous patch the build did not take, and
the measurement below would be another `g`.

r2026-10-11-g ran on the previous binary. Its own report says so:

    worker built from patch ea90414e2b00 at port 9d08f41 · OUT OF SYNC - the worker was
    built from patch ea90414e2b00, this checkout has c2c4279a9623

So the history change (4d3b7ec, patch c2c4279a9623) has never been measured, and g's
`network+composite 12.2ms` is the number for the code *before* it. The fix is in the tree:
`experiments/opendlss_port/rebuild.sh` applies the current patch to the staged copy and
rebuilds, and fails if the new binary does not report that patch (verified here: 78 PTX
kernels, stamp `patch c2c4279a9623`, `in sync`).

Then queue the measurement - the same shape as `r2026-10-11-g`, which is the same shape as
`c` - and read `network+composite` against c's 12.5ms:

    {"id": "r2026-10-12-b", "entry": "minimal",
     "args": ["--source", "image", "--input-image", "fixtures/youtube-1440p.png",
              "--headless", "--frames", "60", "--worker-log", "--shm", "--no-motion",
              "--send-ahead", "2"],
     "timeout_s": 300, "artifacts": ["before.png", "after.png"],
     "note": "the history feed's cost, against c's network+composite 12.5ms"}

How to know it worked: the report's `worker:` line carries no `OUT OF SYNC`, and the per-frame
`network+composite` is the number to compare. A large rise means the history buffer is being
rebuilt when it need not be; a small one means the feed is nearly free and the next step is
real motion vectors rather than a zero field.

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
