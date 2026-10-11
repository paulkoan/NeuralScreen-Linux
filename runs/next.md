# The plan

Work items in order, for whoever - or whatever - picks this up next. Take the top item, do it,
delete it, append what you learned at the bottom.

Not negotiable, because these are the difference between a loop and a runaway: one item per
pass; the test suite green before anything is pushed; never touch /etc or install system
packages; never touch the developer's checkout at /home/paul/dev/NeuralScreen-Linux; never edit
/opt/neuralscreen (policy, executor, key, unit); never queue a run that is not described here.

## 1. Measure the history change (ready - queue it)

runs/done/r2026-10-11-c is the baseline: network+composite 13.1ms at 2560x1440 with no history.
The commit before this one makes serve feed the previous frame back as lanes 7-9, so the same
run says what that costs. If the number moves much, the history buffer is being rebuilt when it
need not be; if it barely moves, the feature is nearly free and the next step is real motion
vectors rather than a zero field.

* id `r2026-10-11-g`, entry `minimal`, args `--source image --input-image
  fixtures/youtube-1440p.png --headless --frames 60 --worker-log --shm --no-motion
  --send-ahead 2`, artifacts none
* learned: (fill in)

## 2. Ask first - do not start these alone

* Decided (2026-10-11): the fixture keeps the whole frame. No crop.
* The container: it needs nvidia-container-toolkit, a system package. The developer's call.
* Anything touching /etc, system packages or the box's configuration. Every time.

## Learned

* Temporal history, step one (retired here, commit 4d3b7ec): serve now feeds the frame it published last back
  as lanes 7-9. It is `expandRgba8ToProxy` of `imageBuffer` into a `historyProxy` buffer at the
  top of the frame - one dispatch, no host bytes - and `preprocess.comp` gained a history
  binding plus a `historyValid` push field: with a history it samples lanes 7-9 from it, without
  one it repeats the current proxy, which is what it always did. The reprojection is the
  identity because this path is handed no motion; a reset and a bypass frame drop the history.
* Verified here: `uv run pytest tests/ -q` 305 passed / 14 skipped, the port's 15 shaders compile
  with glslang 16.6.0, a pristine clone of 9d08f41 + the new patch builds 78 PTX kernels and
  `dlss5vk` (stamp: port 9d08f41 (12 modified) patch c2c4279a9623), and the six native-serve
  tests pass against that binary with NS_ODL_NATIVE_BIN set.
* Parity is untouched by construction, not by argument: `main.cpp` passes no history, so its
  features are the first-frame ones it always compared. That is why this did not need handing back.
* The patch commit is c2c4279a9623; the composite still does not blend the history, so the
  temporal half of the loop (the blend, and motion) is the next step, and `r2026-10-11-f` is
  queued for this one's cost.
