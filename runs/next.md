# The plan

Work items in order, for whoever - or whatever - picks this up next. Take the top item, do it,
delete it, append what you learned at the bottom.

Not negotiable, because these are the difference between a loop and a runaway: one item per
pass; the test suite green before anything is pushed; never touch /etc or install system
packages; never touch the developer's checkout at /home/paul/dev/NeuralScreen-Linux; never edit
/opt/neuralscreen (policy, executor, key, unit); never queue a run that is not described here.

## 1. Next work

* The shm table is complete at both resolutions, and it says the transport was the pipe:
  `r2026-11-02-bh` (1440p, no pixels, `--shm`, 120 frames, same build) reads **18.5 ms / 54.1
  fps** steady against ax/ay's pipe 25.8/26.4 on the same shape - **7.5 ms off** - so the
  transport saving does not depend on a reply crossing. Against `be`'s 1440p-with-pixels 26.4 ms
  that puts the pixel channel at **7.9 ms** under shm, down from the 13.6 ms the bb-vs-ax pipe
  pair attributed to it (~6 ms of that was the pipe's own 14.7 MB reply read). 18.5 ms is 1.8 ms
  over the 16.7 ms 60 fps budget, so the shippable 1440p floor (pixels mandatory) is `be`'s
  26.4 ms and the 9.7 ms still to find is the pixel channel (7.9) plus the neural pass (12.7,
  overlapping). Earlier context: `bg` (1080p, pixels, `--shm`) 19.5 ms against `az`'s pipe 31.6
  on the same build and shape (`bg-1080p.png` byte-identical to `az-1080p.png`, `4d1e3152cb34`),
  12.1 ms off. Also settled: `--send-ahead 2` reproducibly changes the frame (bd/bf
  `1694ccd3a506` vs `28292742c88b`) and stays off; serial shm moves no pixel (`be == bb == bc`,
  `bg == az`).

* Next: **nothing queues**, and the motion field is now priced (2026-11-02 tick, bi/mg read).
  The remaining lever is unchanged: the worker's own frame at 1440p - the pixel channel (7.9 ms
  under shm) plus the neural pass (12.7) of `be`'s 26.4 ms - and any build there waits on the
  reply-format product decision in "Ask first" (FP8 vs changed-tiles vs accept <60 fps at
  1440p). The guides pair is in and it is not a cheap lever: a real field costs **+15 ms** on
  the frame (send +2.9, the worker's own `network+composite` +6, recv +11.7) to move 0.47% of
  the pixels, so frame generation / temporal upscaling now starts ~15 ms further back and that
  is the user's call, not a run. No open timing shape would add a number, and the 1080p shm
  no-pixel control is off-target now that the user has fixed 1440p, so this item stays here
  until that call is made; it is a build item, not a run.

* The shm numbers change the arithmetic, and the pixel channel is now the whole remaining gap
  (2026-11-02 tick, bg/bh read). Same build, same 120-frame shape, all with `--shm`:
  **1440p no pixels 18.5 ms / 54.1 fps** (bh); 1440p with pixels 26.4 ms / 37.9 fps (be);
  1080p with pixels 19.5 ms / 51.2 fps (bg). So the pixel channel costs **7.9 ms** at 1440p on
  shm (not 13.3 on the pipe) and the resolution step costs 6.9 ms. 60 fps needs 16.7 ms, so
  1440p-with-pixels needs 9.7 ms off and 7.9 of that is the pixel round trip. And even with the
  pixel channel gone, 1440p sits at 18.5 ms - **1.8 ms short**, against 23 ms short on the pipe
  numbers this plan was written with. The worker and the display are on the same GPU box, so a
  shared-surface path (dma-buf export, or the Spout pattern the Windows arm uses) would remove
  readback + reply instead of shrinking them. That is the largest remaining lever with no picture
  cost, and it needs code in the worker and the client.

* Next: **nothing queues.** The live pair closed the capture line (learned, top of the list):
  a 1 MiB pipe plus read-into-the-frame takes the live frame **46.6 -> 33.8 ms** and the capture
  read 13.1 -> 6.0 ms, and `--prefetch` stacked on top reads **35.2 ms** - no further gain, inside
  the run-to-run spread. So the client's capture+send+display is now ~11 ms of the 33.8 and the
  worker's own **20.5-22.3 ms** is the entire remaining lever. Every way into it (reply format,
  shared surface, frame generation) is a product call in "Ask first", so the only unblocked action
  left is the one-line policy entry for `port-profile` below; nothing is queued this tick.

* learned: queued `r2026-11-03-profile2` to repeat the per-dispatch profile on an idle card (GPU probed IDLE); the composite's ~2.5-3.7 ms share still needs its own instrument (2026-11-03 tick).

> Keep this section stocked: when the last item is finished, write the next one in the same
> tick. An empty section stops the pipeline - the tick only wakes on a result or a change here,
> so "no open item" means nothing queues and nothing runs, which is what happened overnight.

> A timing run is only evidence if the card was quiet: probe it with `tools/gpu_status.py
> --watch 20` (entry `gpu-status`) before any measurement run and after it. If either probe says
> BUSY or UNKNOWN, record that next to the number and do not compare it against earlier runs -
> two 1440p runs of the same config already read 29.1 and 35.3 ms an hour apart.

## 2. Ask first - do not start these alone

* Decided (2026-10-11): the fixture keeps the whole frame. No crop.
* Anything touching /etc, system packages or the box's configuration. Every time.
* **Frame generation / alternate frames** (raised 2026-11-02): if the pipeline computes 30 fps and
  presents 60, each processed frame gets 33.3 ms and 1440p-with-pixels (39.7 ms) needs only 6.4 ms
  off - a plausible target, where 60 processed fps needs 23 ms and is not. The port already has the
  machinery: `serve.cpp` keeps the last frame and its composite "samples that history where the
  client's motion field says this pixel was", i.e. temporal reprojection against a motion field.
  What is missing is the field: the client sends zeros (protocol.py `put(rgba, motion=None)` skips
  it), because a Wayland portal capture cannot supply per-pixel motion. So frame generation needs
  motion estimated client-side - optical flow or block match on downscaled frames - or vectors from
  the game/portal if it can expose them. Cost: new code in the capture/loop layer, one extra frame
  of latency, and ghosting risk on denoised content where the denoiser's output is not temporally
  consistent. Not a flag. Needs a user decision on whether to spend there.
* **DECIDED 2026-11-02 by the user: stay at 1440p and aim for max FPS**, accepting that 60 fps may
  not be reached. So "drop to 1080p" is off the table and the pixel channel / overhead work is the
  programme. Frame generation and alternate-frame interpolation were raised in the same message and
  are open questions below.
* **Resolution for the 1440p target** (raised 2026-11-01 tick, pair measured 2026-11-02): keep
  2560x1440 and pay for the pixel channel, or drop the stream to 1920x1080. The same-build 1080p pair
  is now in: az *with pixels* 31.6 ms / 31.6 fps vs ba *no pixels* 14.9 ms / 67.3 fps - so the pixel
  channel costs ~16.7 ms at 1080p and 1080p itself is not the slow part (the older 13.6 ms figure
  reproduced, at 14.9). Resolution costs ~11 ms (1440p no-pixel ~26 ms vs 1080p no-pixel ~15 ms).
  60 fps needs 16.7 ms: 1080p no-pixel clears it; 1080p with pixels and 1440p without pixels do not.
  So the next build targets the pixel channel either way, and "keep 1440p" is no longer obviously
  the expensive option. Still a product choice, not measurable here; nothing gets built until it
  is made.
* **Reply format / pixel channel** (raised 2026-11-02 tick, measured by bb): the client handoff is
  flat (~0.3 ms/MB), so the pixel channel's cost is the worker's readback+reply (~8.3 ms at 1440p)
  and the neural pass's area scaling. FP8 halves payload but buys only ~4-6 ms; changed-tiles would
  buy less on a full-screen stream. 1440p-with-pixels measures 39.7 ms, so 60 fps needs the neural
  pass cut as well. Product choice: accept FP8's quality loss, ship changed-tiles, or accept <60 fps
  at 1440p. Nothing gets built until this call is made. **Re-priced on the shm numbers (bg/be,
  2026-11-02): the part of the reply path that motivated FP8 was the pipe's ~13 ms, not the
  channel. Under shm the worker's readback+reply is 2.3 + 1.7 ms at 1440p (be) and 2.2 + 0.7 at
  1080p (bg), i.e. FP8's ~4-6 ms would now be the whole channel and more - so the reply format may
  not be worth any quality trade at all. Decide on the shm figures, not bb's pipe ones.**
* **`--shm` as the default for pixel runs** (raised 2026-11-02 tick): every pixel measurement
  before bd/be/bf/bg used the slower pipe path, so the port's numbers on the record under-report
  it by ~7.5-13 ms on the shapes measured (bh: 18.5 ms shm vs ax/ay 25.8/26.4 pipe at 1440p
  no-pixel). Making shared memory the default is a one-line change to the client's argv in
  `minimal/__main__.py`, but it changes the shape of every future run and the client is not this
  tick's to edit - a user call, not a measurement.

## Learned

* learned: the profile route is stable enough to be a baseline (2026-11-03, `r2026-11-03-profile-idle`
  against the profile run taken at 93% GPU). Idle total **9.751 ms** against 9.749 ms with six
  resident browsers - 0.002 ms apart, and the barrier probe 0.408 vs 0.411 ms. That is what the
  route's per-dispatch minimum over 7 frames is for: contention does not reach the numbers, so
  earlier runs taken on a busy GPU were not wasted and the baseline stands. Confirmed idle total:
  **9.751 ms**, FFN 0.974 / 0.909 / 0.517 ms, `block32_ptx 58880w f74` 0.619 ms.

* learned: `r2026-11-03-profile2` landed but is NOT a usable repeat (2026-11-03 tick). Exit 0 in
  6.9 s after waiting 297.5 s; gpu_before BUSY at 94% and gpu_after BUSY at 79%, with
  DyingLightGame_TheBeast running (6.2 GB) in both probes, so by this plan's own gate rule its
  numbers must not be compared. It reads **14.090 ms** total against `r2026-11-03-profile`'s
  9.749 ms, and the gap sits in a handful of stages (block 70 1.748 vs 0.571 ms, block 59 1.325
  vs 0.142, block 10 1.318 vs 0.142, block 3 1.311 vs 0.141) rather than across the table. The
  idle-card repeat stays unqueued: the game is running, a BUSY "before" invalidates the sample,
  so another run now would wait 300 s and land BUSY again. The composite's ~2.5-3.7 ms share
  still has no instrument.

* learned: the port's own arithmetic, measured - and the NGX gap is smaller than this plan said
  (2026-11-03, `r2026-11-03-profile` via the `port-profile` entry, exit 0 in 4.6 s). **Total 9.749
  ms** for the 2560x1440 pass (sum of per-dispatch spans), against NGX's 7.1 ms for the same
  weights - so the gap is **1.37x, not the 1.7x** the plan has been quoting. The barrier question
  is also settled by measurement rather than by reading the source: "400 trivial dispatches +
  barriers: 0.411 ms (1.03 us each)", so a full barrier costs ~1 us and the port's ~330 dispatches
  cannot be paying more than ~0.3 ms in barriers. The cost is the FFN: three dispatches are 25% of
  the total (ffn_ptx 14720x256 e8 r3 0.980 ms / 10.0%, ffn_ptx 58880x128 e4 r4 +proj 0.908 / 9.3%,
  ffn_ptx 235520x64 e2 r4 +proj 0.516 / 5.3%). Nothing else reaches 6.3%. Also note the profile
  total (9.749) is BELOW the live worker's "network+composite" (12.0-13.5), even though the profile
  runs with barriers on: so ~2.5-3.7 ms of the worker's figure is composite and/or the gaps between
  dispatches, not the network's spans. Careful with that subtraction though - a sum of per-dispatch
  spans is not a wall clock, so it cannot be subtracted from one and called "composite"; all it
  proves is that the pass's arithmetic is 9.75 ms and the worker's wall time for the same region is
  12-13.5. Chasing the network's 1.37x therefore recovers at most ~2.6 ms. The route disables chaining by
  design (per-dispatch spans need the barriers) so its total is not a frame time and must not be
  compared against one - the comparison that matters is kernel against kernel and against NGX's
  7.1 ms, both measured the same way. GPU was BUSY (93%) during the run, so the numbers carry a
  neighbour's load; a repeat when idle would firm them up.

* learned: both capture changes landed on the box and the live frame fell from 46.6 to **33.8 ms /
  29.6 fps**; `--prefetch` lost and stays off (2026-11-03, runs live-pipe1m and live-prefetch read
  against live-1440p). `r2026-11-03-live-pipe1m`: pipe buffer 64 -> 1024 KiB as asked, **capture
  13.4 -> 6.5 ms** (split: wait 0.5, **read 6.0** against 13.1 before - the prediction was ~9,
  the floor was lower), send 2.6 -> 1.5, recv median 26.7 -> 23.0, display 4.9 -> 3.2, so the
  frame is **33.8 ms steady / 29.6 fps**, and capture is no longer a problem worth a design.
  `r2026-11-03-live-prefetch` then added `--prefetch` on top and was **worse: 35.2 ms / 28.4 fps**
  - capture 0.0 ms as designed (387 drained, 386 dropped, frame age 15.6 ms mean) but send 2.7 and
  recv median 28.4 both rose, so the drain thread's CPU and the churn cost more than the 6.5 ms it
  hid. That is the whole story of the flag: it was written when a grab inside the loop measured
  ~238 ms, and against a 6.5 ms grab it is a regression. Do not queue it again without a reason
  that starts from 33.8 ms.

* learned: the live frame is now 33.8 ms and it is one leg (2026-11-03). Stage medians of
  live-pipe1m: capture 6.5, send 1.5, recv 23.0 (the worker's own frame), display 3.2 - serial, so
  they sum to the frame. The worker is 68% of it and the pass is 12-13.5 of the worker's ~20, with
  proxy ~3 and readback ~4 around it. Nothing client-side can move the number much now: even a
  free capture, free send and free display would leave the worker's 23 ms. So the programme is the
  port's arithmetic (tools/port_profile.sh) and then, if that road ends, the pixel channel's
  readback - which is a dma-buf change, not a knob.

* learned: the live capture line is closed, and the answer is the buffer, not the overlap (2026-11-03
  tick, read of `r2026-11-03-live-pipe1m` and `r2026-11-03-live-prefetch`). Both exit 0, 120/0, real
  portal capture of a live 2560x1440 window, `--shm`, same worker patch `0aabc30ec374` at port 9d08f41.
  pipe1m: the resize was **granted** (`pipe buffer 64 -> 1024 KiB`), capture split wait 0.5 / read 6.0,
  steady **33.8 ms / 29.59 fps** (headline 14.13) against live-1440p's 46.6 ms / 21.5 fps on the same
  build and shape - **12.8 ms off**, with the capture read 13.1 -> 6.0 exactly as the bench predicted.
  prefetch stacked on top: it drained 387 frames on its own thread, dropped 386, frame age mean 15.6
  max 39.0 - and still read **35.2 ms / 28.44 fps**, 1.4 ms *worse* than pipe1m's serial 33.8 (inside
  the 29.1-vs-35.3 ms spread, but nowhere near the ~30 ms the plan predicted). So handing the loop the
  newest frame on a thread buys nothing once the pipe already drains in 6 ms: the worker is idle for
  ~6.5 ms of capture, not 13, and the drop path costs what it saves. The serial loop stands; prefetch
  stays opt-in and unused, and its picture differs from the serial run by design (no byte comparison).
  Where the live frame now sits: worker 21.8/20.5/22.3/20.7 ms at frames 29/59/89/119 (pixel channel =
  readback ~4 + reply ~1.7, network+composite ~12.5) inside a 33.8 ms frame, so the worker is ~63% of
  it and capture+send+display is ~11 ms. 60 fps at 1440p needs ~17 ms off the worker's 21, i.e. the
  reply-format / shared-surface / frame-generation decision, not another run. Artifacts:
  `pipe1m-before.png` / `pipe1m-after.png`, `pf-before.png` / `pf-after.png`; gpu WARN before and after
  on both (resident, not contending), so they are usable samples.

* learned: the schedule is not the port's 1.7x gap - the arithmetic is (2026-11-03 tick, read of
  the port sources at /opt/data/tmp/odl-src). The port's pass is 12.0-13.5 ms at 1440p against
  NGX's 7.1 ms for the same weights, and the obvious suspect was barrier overhead: the port has
  counter chaining that drops the barrier between consecutive PTX launches, and it is gated in
  `nr_graph.cpp` (`routes_.chain = ... chainEnabled() && options_.fusedBlocks && ...`) with a
  resolution-dependent escape hatch - past `(fullHeight + 11) / 8 > kSyncCountersPerRegion`
  (= 2048/4 = 512) it warns "running with barriers" and drops chaining. At 2560x1440 that
  threshold is 181, and it is 271 at 4K, so **chaining is on at every resolution we ship** and
  the live run's stderr carries no such warning. Chaining also defaults on (`getenv("DLSS5VK_CHAIN"
  ) ? ... : true`) and only `profile` turns it off, deliberately, because per-dispatch timings
  need the barriers. So the gap is inside the kernels, and the port already has the instrument:
  `dlss5vk profile --model <dir> --width W --height H --frames N` prints every dispatch's span
  and totals by kernel and by stage, taking the per-dispatch minimum so other tenants cannot
  inflate it. That is `tools/port_profile.sh` now; it needs a runner entry (below) because it
  must profile the binary port-build last produced, not a fresh one.

* learned: `--send-ahead 2`'s picture change has a name, and it is not a mystery (2026-11-03 tick,
  reading protocol.py). `SharedFrameBuffer` says it outright: "there is one slot. Frame N+1 must
  not be placed until the worker has returned the result for frame N, otherwise we overwrite the
  pixels under its hands. The main loop is strictly paired (send -> recv), so the invariant holds.
  Add pipelining and a second slot will be needed." `--send-ahead 2` sends a second frame into
  that one slot while the worker is still reading the first, so bd/bf's `1694ccd3a506` is
  corrupted input, not a different picture from a different schedule. The output section has the
  same shape: one slot with a seqlock that detects a torn write, not a newer frame. So real
  pipelining needs the worker's protocol changed (a slot index in the frame header - FRAME_FMT
  already carries a reserved word - and per-slot output with the index in the header), which is a
  port change, not a client one.

* learned: the serial loop's capture cost is removable today, by a flag that already exists
  (2026-11-03 tick). The loop is capture -> send -> recv -> display with no overlap, so the 12.8 ms
  grab is dead time with the worker idle. `minimal/prefetch.py` (7 tests, opt-in `--prefetch`,
  never used in a live run) drains the source on its own thread and hands the loop the newest
  frame; its own docstring records why the flag exists: a screencast whose client stops consuming
  stops producing, so the capture leg otherwise absorbs a producer round trip every frame. This is
  safe against the single-slot invariant above, because the slot is still written at send time,
  on the main thread, after the previous reply. Expect ~13 ms off the live frame (46.6 -> ~33, and
  with the pipe/copy fixes ~30), paid for with dropped stale frames - so the picture differs from a
  serial run by design and a byte comparison against it is meaningless.

* learned: the capture leg's transport is a pipe, and its buffer was the kernel default
  (2026-11-03 tick). The live run's capture read is 13.1 ms/frame for a 14.7 MB RGBA frame =
  1.12 GB/s, which is the pipe ceiling, not the portal's - the same disease `--shm` cured on the
  frame channel, one layer out. Benchmarked both buffer sizes with the real shape (a producer
  streaming 1440p frames, a consumer draining one per grab): **64 KiB 12.70 ms/frame, 1 MiB 8.90
  ms**, and a shared-memory ring 4.93 ms. The resize is the free part and it is in: the client
  asks `F_SETPIPE_SZ` for 1 MiB (/proc/sys/fs/pipe-max-size on stock Linux) on the pipe it
  already owns, best-effort, and logs what was granted. `timing_summary` now reports
  `capture_pipe_bytes` and the report's capture-split line names the buffer, because `read` means
  different things at 64 KiB and 1 MiB - the "~19 ms means stocked" note was only true of the
  default. A test caught a real hole while writing this: `fcntl` raises ValueError on a bad
  descriptor, not OSError, so a refused resize would have taken the whole capture down.
  Then the drain loop itself: it built bytes and viewed them, a second copy of all 14.7 MB, so
  it now reads straight into the frame's own numpy buffer via `readinto1` (not `readinto`, which
  blocks for the whole request and would swallow the wait/read split). Measured at a 1 MiB pipe:
  **8.71 ms/frame through `b"".join` against 6.74 ms reading into the frame**, and 10.56 against
  12.49 at the 64 KiB default, so the loop is worth ~2 ms even if the resize is refused.
  Prediction for the next live run: capture read ~7 ms, frame ~40 ms (from 46.6). The bigger
  prize is the same one as on the frame channel - hand the frame over through shared memory or
  take the PipeWire buffer directly (4.93 ms), which needs the producer replaced, not resized.

* learned: the live end-to-end run landed and it rewrites the floor (2026-11-03 tick, read of
  `r2026-11-03-live-1440p`). Real portal capture of a live window at 2560x1440, `--shm`, pixels
  saved, 120/120 frames, exit 0, 28.0 s. Steady **46.6 ms / 21.5 fps**, headline 11.09 fps.
  Stage medians: capture 12.8 (split: wait 0.3, **read 13.1** - the portal pipe was stocked, so
  this is the honest portal cost, not a dribble), send 2.3, recv 26.7 (worker's own frame 21.2-24.7
  on frames 29/59/89/119), display 4.2. The stages are serial, so 12.8+2.3+26.7+4.2 ~= 46.0 against
  the reported 46.6. Two consequences. First, **every fps figure this plan has quoted for 1440p was
  measured on a synthetic card** whose capture+send+display cost 6.2 ms; live capture+send+display
  costs ~19.3 ms, so the real-input floor is ~20 ms above the shm figures - `be`'s 26.4 ms becomes
  **46.6 ms** end to end (its worker steady 18.1-20.2 ms against live 21.2-24.7 accounts for ~3 ms
  of the difference; the other ~17 ms is capture, send and display on a real source). Second, the
  worker's ~22 ms already exceeds the entire 16.7 ms budget before any client work, so 60 fps at
  1440p needs the worker cut by ~2.4x, not by 9.7 ms. The 9.7 ms gap this plan was written around
  was a synthetic-input figure and should not be quoted as the target any more. Artifacts:
  `live-before.png`, `live-after.png`. The capture spread's one-off at frame 29 (37.7 ms) and the
  display's at frame 27 (33.5 ms) are worth a look in the next run; both are outside the warm-up.
  Also: 39% of one core for the gst pipeline, so capture is CPU-costly as well as slow.

* learned: `r2026-11-02-motion-guides` and `r2026-11-02-bi` are the same run twice, and together
  they price the motion field (2026-11-02 tick). Both exit 0, 120/0, 1440p with pixels,
  `--shm --motion-guides --save-after`, worker patch `0aabc30ec374` at port 9d08f41;
  `bi-1440p.png` and `guides-1440p.png` are byte-identical (sha256
  `8e1f5affcd412998520ad815c2c0ccc5fa5aa2241e9209e9194dda5de85b8330`, 2,786,335 bytes), so the
  estimator is deterministic run to run and either number is the same measurement. Steady median
  **37.3 ms / 26.8 fps** (bi) and **41.8 ms / 23.9 fps** (mg) against `be`'s zero-field 26.4 ms /
  37.9 fps on the same build and shape: **the real field costs ~+15 ms, and the two identical runs
  are 4.5 ms apart**, so quote +11..+15, not a point (bi's `gpu_after` is BUSY at 35%, so mg -
  WARN before and after - is the clean sample). Where it goes: the client's send median 1.2 -> 4.1
  ms (a real field is 14.7 MB of bytes that must go out) and recv 20.4 -> 32.1, which is the
  worker's own frame - frames 29/59/89/119 read 35.4/30.6/24.7/27.4 against be's 20.2/18.1/18.1/
  19.4, i.e. `network+composite` 12.2 -> ~18 with real reprojection offsets plus the field upload.
  The estimator itself is NOT in the client's stage timers: `loop.py` calls `_guide_motion`
  between the timed capture and send blocks, so the reported stage sum (and the median fps) omits
  DIS optical flow's own cost and the 11.04 fps headline (120 frames in 10.874 s) is the only
  figure that contains it.

* learned: the motion field DOES reach the composite, and on this fixture it barely moves the
  picture (2026-11-02 tick). `guides-1440p.png` against `be`'s zero-field `be-1440p.png`
  (`28292742c88b8e01`): MAD **0.3925** per channel, max 19, **0.47%** of pixels moved >2, 0.01%
  >8 - a real but near-neutral field, the same order as bd's `--send-ahead` diff (0.41) and far
  below the blend's 5.74. So `put(rgba, motion=...)` is wired end to end (zero field is
  byte-identical, `be == bb`, MAD 0.0000; a real one is not), which is what the run was for - but
  the +15 ms it costs buys a 0.4-level change on the synthetic card, so the case for spending on
  frame generation / temporal upscaling is weaker than the plan assumed. That decision is still
  the user's ("Ask first"), and nothing was queued this tick.

* learned: the `--motion-guides` request could not run as written, so it was re-ided (2026-11-02
  22:13 tick). Commit 083de9c rewrote `runs/queue/r2026-11-02-bh.json` to the motion-guides run,
  but the box's runner had already consumed the old content - `runs/done/r2026-11-02-bh` landed at
  20:58:45, 30 s after the 20:58:17 queue push - and `tools/auto_runner.py` skips any id whose
  directory is on the results branch (`done_ids`, line 456: "done and published, skipping"). One
  run per id, so the rewritten file was inert; the same argv was queued as `r2026-11-02-bi`
  (artifact `bi-1440p.png`) and pushed as d19e1a5. The stale `runs/queue/r2026-11-02-bh.json` is
  left in the tree untouched (skipped every pass) rather than edited. Nothing else changed: the
  shm-table findings, the "nothing queues" build item and the reply-format call stand as recorded.

* learned: `r2026-11-02-bg` answers the 1080p half, and the answer is that the pipe was the cost,
  not the pixels (2026-11-02 tick). Exit 0, 120/0, 1080p with pixels, `--shm`, worker patch
  `0aabc30ec374` at port 9d08f41, gate released at WARN with no wait. Steady median **19.5 ms /
  51.2 fps** (the 55.3 ms / 18.1 fps headline is the 4.2 s frame-0 recv), against az's 31.6 ms /
  31.6 fps on the same build and shape - 12.1 ms off, at the low end of the 18-19 ms prediction.
  Same build, same n=119 input: `bg-1080p.png` is byte-identical to `az-1080p.png`
  (`4d1e3152cb345e90cdfc2b53345cb679cfa54c90`), so the serial shm path moved no 1080p pixel either.
  Split: capture 2.5, send 1.3 (min 1.0, max 3.1 at frame 0), recv 14.7 (min 13.5, max 4193.6 at
  frame 0), display 1.1; worker 12.9/13.3/14.1/13.2 ms at frames 29/59/89/119 =
  network+composite 7.9 + proxy 2.2 + readback 2.2 + reply 0.7. So at 1080p the pixel channel is
  ~2.9 ms of the worker, not the 16.7 ms the az-vs-ba pipe pair attributed to it - that delta was
  mostly the client's pipe read. 1080p-with-pixels is now 19.5 ms / 51.2 fps, 2.8 ms over the
  16.7 ms 60 fps budget; every no-pixel reference in the table is a pipe number, so
  `r2026-11-02-bh` (1440p, no pixels, `--shm`) is queued to size the channel at 1440p.

* learned: (2026-11-02 tick). Exit 0, 120/0, `gpu_before` = WARN after waiting the full 150s, `gpu_after` =
  BUSY at 59% utilisation, so all three gate fields are now populated and the require_idle flag is
  live in the policy. Steady median 26.4 ms / 37.9 fps against ax's 25.8 ms on the same 120-frame
  1440p no-pixel shape - a 0.6 ms difference, inside the 29.1-vs-35.3 ms spread already seen between
  identical 1440p runs. The gate held its full timeout and the card was still WARN when it let the
  run go, then BUSY when it finished, so this is a valid demonstration of the mechanism but not a
  quiet-card timing sample. A repeat run would just wait another 150s and start at WARN again: the
  resident set (chromium, msedge, Telegram, signal-desktop, shelly-ui, signon-ui) plus the game
  already noted means the box is chronically busy. But WARN is the bar the gate releases on - it
  means "resident, not contending" - so a WARN "before" IS an acceptable sample and only a BUSY
  "before" is not. ay released at WARN after its 150s timeout, so ay and ax are usable numbers;
  the pessimistic "nothing is honest" reading was wrong. The real finding is that the ~26 ms 1440p
  no-pixel figure is stable across both (25.8 / 26.4), and that the pixel channel costs ~18 ms at
  1080p (az 31.6 ms with pixels vs ao's 13.6 without) - which needs a same-build pair to trust.

* learned: cell is filled at 31.6 ms / 31.6 fps. ba completes the same-build pixel/no-pixel pair; the next
  tick reads its result to decide whether the ~18 ms gap is the pixel channel or the resolution.
  The resolution choice in "Ask first" remains open and still gates the next build.

* learned: steady median **14.9 ms / 67.3 fps** at 1080p no-pixel on az's checkout - near ao's older 13.6 ms
  and nowhere near 27 ms, so 1080p is not slower on this build and the ~16.7 ms gap against az's
  31.6 ms is the pixel channel, not the resolution. The "Ask first" resolution note now carries the
  verdict; the next build target still needs that product decision, so nothing was queued this tick.

* learned: `r2026-11-02-bb` answers the reply-path question, and the answer is "not the payload"
  (2026-11-02 tick). Exit 0, 120/0, 1440p with pixels on az's build: steady median **39.7 ms /
  25.2 fps**, recv median **29.4 ms** (spread 27.4 min / 3827 at frame 0 - warm-up only). Against
  the same build: az 1080p-with-pixels recv median 23.3 and ba 1080p-no-pixels 9.9. The client's
  recv above the worker's own frame is ~4 ms at BOTH 8.3 and 14.7 MB, i.e. ~0.3 ms/MB - flat, not
  payload-proportional. The 23.3 -> 29.4 rise is the worker, not the handoff: its
  network+composite goes 9.0 -> 14.4 ms with area while readback 3.5 + reply 4.8 stays 8.3 ms. So
  an FP8 reply would recover ~4-6 ms of 39.7, not 13. Also, bb's 39.7 sits above the 29.1-35.3 ms
  spread seen between identical 1440p runs (as/au read 35.7/35.8), so part of its 8 ms gap over az
  is sample noise. Verdict: the reply path is a minor lever; 60 fps needs the neural pass cut too.

* learned: * Blocked: the reply-format decision is now a product choice and sits in "Ask first" - FP8 output
  (quality loss, ~4-6 ms) vs changed-tiles vs accept <60 fps at 1440p. Nothing queued this tick:
  the next timing would repeat known numbers, and no build target can be chosen until that call is
  made. The resolution decision stays open and is now clearly secondary.

* learned: per-frame stages, not `stdout.log` - the client prints only run means plus send/recv spreads, so
  there is no per-frame capture/send/recv/display sample at 29/59/89/119 and the client row below is
  a mean, not a median. Steady values, ms, frames 29 / 59 / 89 / 119 (2026-11-01 tick):

* learned: | run | worker total | proxy | network+composite | readback | reply |
  |---|---|---|---|---|---|
  | as | 24.3 / 21.9 / 22.1 / 20.8 | 1.9 / 1.9 / 3.1 / 1.9 | 14.8 / 12.7 / 11.8 / 12.4 | 3.0 / 2.8 / 2.9 / 2.8 | 4.6 / 4.5 / 4.3 / 3.8 |
  | au | 22.5 / 22.5 / 24.1 / 21.9 | 2.4 / 1.9 / 2.2 / 2.1 | 12.3 / 13.1 / 12.5 / 12.9 | 2.9 / 2.8 / 3.6 / 2.7 | 4.9 / 4.7 / 5.7 / 4.2 |

* learned: The two runs agree within a millisecond on every stage; both workers' steady medians are ~22.3 ms.
  Client means: capture 2.9 (as) / 2.8 (au), send 4.8 / 4.6, display 2.1 / 2.2, recv median 26.2 /
  26.3 - so the 35.7 / 35.8 ms median frame is ~2.9 capture + 4.8 send + 26.2 recv + 2.1 display,
  and recv is the worker's 22.3 plus ~3.9 ms of shm handoff. as's send max 8.6 ms at frame 23 is a
  one-off (au's max is 6.9); frame 0 carries the warm-up in recv (3948 / 4389 ms) and nothing else.
  Worker split of the 22.3: network+composite 12.7, reply 4.4, readback 2.8, proxy 1.9.

* learned: (2026-11-01 tick). 60 fps needs 16.7 ms against 35.7 ms measured, i.e. 19.0 ms off. The neural
  pass is the largest identified stage at 12.7 ms - 36% of the client frame, 57% of the worker's -
  so it is the candidate; but deleting it outright still leaves 23.0 ms, and adding the pixel
  channel (readback 2.8 + reply 4.4 = 7.2 ms) only reaches 15.8 ms if model *and* pixels both go to
  zero. Client capture+send+display is another 9.8 ms and the handoff ~3.9 ms. So a 1440p build
  cannot be justified as one stage, and the only measured path under 16.7 ms remains 1080p
  (14.5 ms / 69 fps, no pixels). The resolution choice is the real lever and it is not this tick's
  to make - it is now the first item under "Ask first". Nothing queued this tick.

* learned: steady median 35.8 ms / 28.0 fps, reproducing as's 35.7 ms / 28.03 fps on the same 120-frame pixel
  shape - so au is the second clean sample and at's 43.8 ms / 22.8 fps was warm-up-bound, not a
  regression: au's worker frames 1-2 read 91.9/87.7 ms yet settle to 22.5/22.5/24.1/21.9 at frames
  29/59/89/119, matching ah's 22/22, and at's 30-frame window never left that warm-up. Quote 1440p
  against ~35.7 ms / 28.0 fps. Pixel neutrality holds: au's after.png is byte-identical to as's
  (sha256 28292742c88b..., MAD 0.0) at the same n=119 input, so the default path changes no pixels;
  the au-vs-ah `nomotion.png` diff is not a same-input pair (bar at x833 vs x203, n=119 vs n=29) and
  reads the same 38.90 fixture confound the as item already documented - it says nothing.

* learned: disagreeing samples taken on different checkouts — as 35.7 ms / 28.03 fps (client b44da39) vs at
  43.8 ms / 22.8 fps (client d666a51) — and at's 30-frame median is warm-up-bound (frames 1-2 at
  48.4/46.2 ms against ah's 22.1/22.7), so at is not the live-path figure. au repeats as's 120-frame
  pixel shape at the current checkout to give a second sample and a same-input after.png.

* learned: `r2026-10-31-ar` (`--work-scale 0.75`) exited 3 at frame 0: the worker refused "the client expects
  NGX upscaling (1920x1080 -> 2560x1440); this worker runs the network at one size", so work-scale
  cannot be measured on this port. `r2026-10-31-ap` (default, no motion flag) exited 0: 120/0,
  **24.6 ms median / 40.7 fps steady**, confirming the flipped no-motion default took effect (the
  21.8 ms prediction was 5 ms low; 24.6 is still under the 29.1 ms motion-on figure). `r2026-10-31-aq`
  (small model) exited 0 but was **slower**: 26.5 ms / 37.8 fps steady, so the small network is not
  the 1440p lever either. Per-stage scheduling cost wins by default. Picture half queued as
  `r2026-10-31-as` (default path + `--save-after`, 120 frames, 1440p) to diff its output against
  `r2026-10-30-ah`'s no-motion picture before quoting the 24.6 ms figure.

* learned: (2026-11-01 tick). The run exited 0, but the pair it was queued to diff is confounded: the
  synthetic fixture moves a 320px bar with the grab index (`minimal/capture.py`,
  `bar = (n*7) % (w - w//8)`), and both `--save-after` files hold the LAST frame — as ran 120 frames
  (n=119, bar at 833) where `r2026-10-30-ah` ran 30 (n=29, bar at 203). Offline this tick: those two
  input frames are byte-identical only outside the bar positions (MAD 37.35 with the bars in,
  0.0000 / max 0 with them excluded), so as-vs-ah's MAD 38.90 mostly measures the fixture. Cutting
  the bars out of the comparison does not rescue it (MAD 5.07, max 34, 99.46% of pixels moved) —
  the pass is a global network, so it reads the bar and the outputs legitimately differ everywhere.
  as's 35.7 ms median is the real new number, and it is the pixel-path shape, not ap's: `--save-after`
  makes `want_pixels` true, and the worker then pays a 14.7 MB readback plus a 14.7 MB reply per
  frame. ap's 24.6 ms / 40.7 fps is a no-pixels benchmark; as (35.7 ms / 28.03 fps) and ah
  (36.1 ms / 27.67 fps, same 30-frame pixel shape) agree. The live path must show or save its output,
  so quote 1440p against ~35.7 ms, not 24.6, until a same-input pair exists.

* learned: fixture's n=29 frame (MAD 0.0000, max 1, no pixels >2 — same input), and its `after.png` is
  byte-identical to `r2026-10-30-ah`'s `nomotion.png` (MAD 0.0, PSNR inf), so the default
  scheduling path changes no pixels. Steady median 43.8 ms/frame (22.8 fps) for the 30-frame
  pixel shape; quote that, not the 180.1 ms frame-0-inflated mean. The remaining 1440p levers
  are the pixel channel (readback+reply ~11 ms) and capture 3.0 + send 4.8 ms.

* learned: bb completes the same-build 1440p pixel cell and the 60 fps arithmetic at 1440p does
  not close (r2026-11-02-bb, 2026-11-01 22:21Z, exit 0, 120/0, gate waited 0.0 - card already WARN).
  **1440p with pixels: 39.7 ms median / 25.2 fps steady**, recv mean 61.6, send 5.4, capture 2.8,
  display 2.3. Same-build set, medians: 1440p no-pixel 25.8 (ax) / 26.4 (ay); 1440p pixel 39.7 (bb);
  1080p no-pixel 14.9 (ba); 1080p pixel 31.6 (az). So the pixel channel costs ~13.6 ms at 1440p and
  ~16.7 ms at 1080p - roughly a fixed ~14 ms, not proportional to payload, which is why 1080p's
  total looks worse than 1440p's delta. bb is also 4 ms slower than as/au's 35.7 on older clients;
  that is spread or a regression, not resolved here. **The arithmetic: 39.7 ms needs 23.0 ms off for
  60 fps. A zero-cost reply saves at most 13.6 ms and still leaves 26.1 ms - the no-pixel frame -
  which is itself 9.4 ms over budget. So 60 fps at 1440p is not reachable by the reply path alone,
  or by the neural pass alone (12.7 ms), or by resolution (8.1 ms). It needs the pixel channel AND
  the model AND the client's own 10.5 ms of capture+send+display. That is three levers, and the
  honest statement is that this port is not going to hit 60 fps at 1440p with the current design.**

* learned: `r2026-11-01-aw` establishes the GPU baseline but the card was BUSY (exit 0). `Dying Light The Beast` holds 5.6 GiB, plus browsers and desktop apps; the card idles at 210/3105 MHz. Timing runs are not evidence until a probe reads idle.
* learned: `r2026-11-02-ay` proves the idle gate works and also proves the card never reads idle
* learned: `r2026-11-02-ba` is queued (1080p no-pixel on az's checkout), and az's 1080p-with-pixels
* learned: `r2026-11-02-ba` answers the same-build pair question (2026-11-02 tick). Exit 0, 120/0,
* learned: the 1440p pixel path is itemized, and it is the worker's `stderr.log` that carries the
* learned: no single 1440p stage clears 60 fps; the one named candidate is `network+composite`
* learned: `r2026-11-02-ax` completed (exit 0, 120/0, steady 38.81 fps) but its result.json has gpu_before/gpu_after null and idle_waited_s 0.0 — the require_idle gate did not write the probes. The 1440p resolution decision in "Ask first" is still open and still gates the next build; ax does not answer it.
* learned: `r2026-10-31-au` settles the 1440p pixel-path number (2026-11-01 tick). Exit 0, 120/0,
* learned: `r2026-10-31-au` is queued (2026-11-01 tick). The 1440p pixel-path number rests on two
* learned: the 1440p lever decision is settled, and work-scale is dead (2026-11-01 tick, read ap/aq/ar).
* learned: `r2026-10-31-as` cannot answer the quality question, and it corrects the 24.6 ms figure
* learned: `r2026-10-31-at` is quality-neutral (2026-11-01 tick). Its `before.png` matches the

* learned: ba closes the same-build 1080p pair, and the pixel channel is confirmed as the lever
  (r2026-11-02-ba, 2026-11-01 21:28Z, exit 0, 6.4s, gate waited 0.0 - the card was already WARN).
  1080p no-pixel on az's checkout: **14.9 ms median / 67.3 fps steady** (120/0), against az's
  31.6 ms / 31.6 fps *with* pixels on the same build. So the pixel channel costs **16.7 ms at
  1080p** - more than the entire no-pixel frame - and it is not a cross-build artefact. The 1440p
  delta reads ~9.6 ms (35.7 pixel vs 26.1 no-pixel) but spans clients, so treat it as unconfirmed.
  Consequence for the resolution decision: in shippable terms (pixels mandatory, since the live
  path must show its output) 1440p is 35.7 ms / 28.0 fps and 1080p is 31.6 ms / 31.6 fps - **only
  4 ms apart, both under 60 fps**. Dropping to 1080p buys 4 ms and nothing else; the 14.9 ms
  no-pixel ceiling is not a product path. So the resolution choice is nearly moot and the build
  should target the pixel channel: readback 2.8 + reply 4.4 at 1440p, but the measured channel cost
  is 16.7 ms at 1080p, which means most of it is fixed overhead in the handoff, not per-pixel work.

* learned: the four-cell resolution set is NOT yet same-build, and the pixel channel looks like
  the real lever, not resolution (2026-11-01 21:25Z tick). Current-checkout runs: ax 1440p
  no-pixel 25.8 ms / 38.8 fps, ay 1440p no-pixel 26.4 ms / 37.9 fps, az 1080p **with pixels**
  31.6 ms / 31.6 fps. Older-checkout runs: ao 1080p no-pixel 13.6 ms / 73.6 fps (client from
  2026-10-30), as/au 1440p with pixels 35.7/35.8 ms / 28.0 fps (clients b44da39/d666a51). Read
  as-is the table says 1080p with pixels (31.6) is *slower* than 1440p without pixels (26.1) and
  only 4 ms faster than 1440p with pixels (35.7) - i.e. the ~18 ms pixel channel swamps the ~4 ms
  resolution step. But az and ao differ in client build, so the 18 ms figure is not safe. The one
  run that makes it safe is ba: 1080p no-pixel on az's checkout. If ba lands near 13.6 ms the
  pixel channel is the lever and resolution barely matters; if ba lands near 27 ms then 1080p
  itself is slower on this build and the older 13.6 was a different code path. Either way the
  next build targets the pixel channel, not the neural pass, and "keep 1440p" stops being the
  expensive option. az's gate held 285s (4.75 min) waiting out the game's BUSY - the policy is
  doing its job and the wait is the cost of honest numbers.

* learned: the gate works (r2026-11-02-ay, 2026-11-01 21:15Z, exit 0, 8.0s). With
  `require_idle = true` in the policy, `idle_waited_s` is **150.0** and `gpu_before` is WARN
  (chromium, signal-desktop, msedge, Telegram, shelly-ui, signon-ui resident, "not contending"),
  so it held 2.5 minutes for the card to leave BUSY and then ran. `gpu_after` reads BUSY at 59%
  utilisation - the worker's own pass fills that sample, so read the "before" line as the gate's
  decision and the "after" line as evidence the card was working. Steady median **26.4 ms / 37.9
  fps**, against ax's 25.8 ms on the same shape: the pair agrees to 0.6 ms and 1.0 fps, so the
  no-pixel 1440p figure is stable at ~26 ms. The gate costs 2.5 minutes when the card is busy and
  nothing when it is not.

* learned: the unit runs the gate code, but the policy does not switch it on (r2026-11-02-ax,
  2026-11-01 21:02Z, exit 0, 8.7s). The executor is refreshed - it wrote the new result fields - and
  yet `gpu_before`, `gpu_after` are both `null` and `idle_waited_s` is 0.0, which only happens when
  `require_idle` is false. So `/opt/neuralscreen/policy.toml` on the box still lacks the flag; the
  unit update installed the script, not the policy. Add `require_idle = true` there (top level, or
  on the `minimal*` entries) and the next run will hold on BUSY. Meanwhile ax is a usable 1440p
  no-pixel sample: **25.8 ms median / 38.8 fps steady**, 120/0 frames, reference model (`blend
  scale 0.7397`), against ap's 24.6 ms on the same shape - the pair agrees within 1.2 ms. Note the
  card was still BUSY when it ran, so quote it with that caveat.

* learned: the GPU box has a game resident, but that is weak evidence for the 29-36 ms spread
  (r2026-11-01-aw, 2026-11-01, exit 0, 21s). The probe reads BUSY: `DyingLightGame_TheBeast_x64_rwdi.exe`
  holds 5670 of 16376 MiB, with Chromium/Signal/Edge/Telegram gpu-processes and kwin_wayland
  beside it. But utilisation is 7%, power 14.2 W, P8, 47 C - nothing is taking compute time, so a
  resident idle app does not slow a frame and 6.6 GB of VRAM stays free. The likely variance
  source is the clock state at each run's start: the card sits at 210 of 3105 MHz between runs and
  ramps when work arrives. Verdict semantics now separate contention (BUSY) from presence (WARN);
  a low clock is a note, not a verdict. Close the game for a clean baseline because it removes a
  wake-up risk and the ambiguity, not because 5.6 GiB is scarce.

* learned: the zero motion field is no longer sent by default (2026-10-30 tick, commit b4bee54).
  `minimal/__main__.py` now defaults `no_motion=True` and `--motion` opts back in; `--no-motion`
  still parses so existing run requests work, and old requests that omit both now take the fast
  path instead of the 29.1 ms one. Not a quality trade: the field is all zeros and the pictures
  are byte-identical (r2026-10-30-ah vs -ad, MAD 0.0). The Wine/NGX arm needs `--motion` added to
  its argv, since it derives flow from the field. Tested in `tests/test_motion_flag.py` (default,
  opt-in, legacy flag); suite 344 pass / 32 skip, the 9 failures are the same libGL/SDL2 import
  errors this box always has. NOT verified: no queue run yet, so the expected ~5 ms send saving at
  1440p is still the measured motion-on/motion-off delta, not a run of the new default.

* learned: the motion field is all zeros - `loop.py` builds one and reuses it, because a stream
  cannot supply real vectors. So `--no-motion` is not a quality trade: `serve` zero-fills its
  motion buffer when none arrives and calls that the identity reprojection, and the pictures are
  byte-identical (r2026-10-30-ah vs -ad, MAD 0.0). At 1440p the field is 14.7 MB of zeroes per
  frame, 5 ms of send and 7.5 ms of frame. Send-ahead 2 hides only ~1.8 ms of it (1080p 19.9 ->
  18.1 ms), so stop sending it rather than overlap it. `--motion-small` matters only if real
  vectors ever arrive.

* learned: 60 fps is a resolution question, and 1080p already clears it (r2026-10-30-aj/-ak,
  2026-10-30, both exit 0, no pixels, `--no-motion`). 1080p **14.5 ms = 69.0 fps** (capture 1.9
  / send 2.9 / recv 10.0); 720p 7.3 ms = 137.8 fps. With motion on, 1080p was 19.9 ms (50 fps),
  so motion costs the 60 fps margin at 1080p and 1440p alike. 1440p no-motion is 21.8 ms
  (45.9 fps): 60 fps needs 16.7 ms, i.e. 5.1 ms (23%) off the GPU pass. The small network
  measured ~1.14x on that pass (~2 ms), so on its own it does not close 1440p; 1080p does not
  need it.

* learned: `--motion-small` hangs the port at init, reproducibly (r2026-10-30-ag and -ai,
  2026-10-30, both exit 3): serve prints 2560x1440/model/shaders/seed and the build stamp, then
  never reaches `serve: device`, and the client times out on frame 0 after 60 s. Two runs, same
  shape, so it is not a flake and not resource contention (ae/af/ah ran between them). Do not
  queue it again without fixing the init path.

* learned: `--motion-small` is dead in the pipe path, reproducibly (r2026-10-30-ai, 2026-10-30,
  exit 3 after 60.5s). It repeats ag exactly: the worker logs its two init lines and then its
  `serve: 2560x1440, model ...` banner, never reaches the device line, and the client times out
  on frame 0 after 60s, so no picture was saved and its median does not exist. Same patch
  0aabc30ec374 as af/z, so the two full-motion numbers stand (29.1 ms / 34.3 fps against
  21.8 ms / 45.9 fps with `--no-motion`); only the reduced path is unmeasurable. `minimal/__main__.py`
  already documents the flag as NOT USABLE in the pipe path, and ai ran without `--shm`, so the
  never-tested variant is `--shm --motion-small`, not a third repeat of this one.

* learned: the motion field is 5 ms of send and 7.5 ms of the frame (r2026-10-30-af/-ah,
  2026-10-30). 1440p no pixels: 29.1 ms with motion, 21.8 ms with `--no-motion` (45.9 fps),
  split capture 2.7 / send 5.1 / recv 14.0. The picture is byte-identical without it on the
  synthetic card (MAD 0.0 vs ad), so the fixture cannot judge quality. BGRA is implemented and
  measures nothing (29.3 vs 29.1): the CPU swap was already gone from the path, and the RGBA
  picture is still 9f13979b168dc3a0. The send is not the copy - 14.7 MB into shm is 1.6 ms, and
  even without motion send is 5.1 ms.

* learned: the BGRA handoff was only half wired. `0baa2fe` made the capture leg return BGRA
  (`minimal/capture.py`), added `FRAME_FLAG_COLOR_BGRA = 0x80` and the port's
  `expandRgba8ToProxy(..., bgra)` shader swizzle, and gave `Worker.send` a `bgra=` argument —
  but `minimal/loop.py` never passed it, so every real screen frame went out labelled RGBA and
  the port did no swizzle. Nothing caught it because every run so far used the synthetic card
  (`bgra = False`) or the mock. Fixed: `Pipeline.bgra` is read from the source, forwarded on
  both the serial and pipelined send paths, and `_save_rgba` converts at save time (a BGRA
  `--save-before` used to be written with red and blue swapped). Tests: 339 pass, 32 skip, and
  the 9 failures are the same libGL/SDL2 import errors this box always has; the new tests drive
  both loops with a recording worker (3 cases). NOT verified: the 1440p number — the standard
  card is RGBA and cannot exercise the path, and no device here, so the 6.9 ms claim is still
  the `swapbench.py` figure from the earlier tick, not a measured end-to-end gain.

* learned: the per-frame cost is linear in pixels with a tiny intercept, but the 1440p point is
  6.2 ms under its earlier twin (r2026-10-30-x/y/z, 2026-10-30, all exit 0, 120 done / 0 skipped,
  patch 0aabc30e in sync, reference model, fused, synthetic). Client median 9.4 / 19.9 / 29.1 ms
  at 720p / 1080p / 1440p = 3.80 ms fixed + 7.034 ms/Mpx (residuals -0.9 / +1.5 / -0.6 ms, so
  genuinely linear). The worker's own total fits 3.05 + 3.79 ms/Mpx and `network+composite`
  2.05 + 2.73 ms/Mpx, i.e. the model is ~39% of the client's per-pixel cost and the fixed part
  (upload+submit+composite) is only 2-3 ms - there is no fixed overhead worth hunting, the neural
  pass is what scales. Steady fps 106.6 / 50.3 / 34.3 tracks 1/area (4x pixels -> 3.1x slower).
  The finding is the spread: z's 29.1 ms at 1440p is 17.6% under r2026-10-30-w's 35.3 ms on the
  same patch, far outside the ±1.5 ms residuals, so run-to-run spread at 1440p is ~6 ms and the
  fit's slope is only good to a few percent - repeat the sweep before quoting either. Capture and
  send also scale with area (0.9/1.8 ms, 2.6/5.7/10.0 ms); the 3.7 s frame-0 warm-up is constant.

* learned: the small network runs in the port and is NOT the bottleneck (r2026-10-30-t/u/v/w,
  2026-10-30, all exit 0). t: 31 blocks / 77 tensors, blend_scale 0.7671. serve confirms
  `blend scale 0.7671 (block30...)`, so the path is real. 120-frame medians, same binary:
  no-pixel small 30.9 ms vs reference 35.3 ms (1.14x); pixel path small 56.4 ms vs reference
  50.4 ms (0.89x). The directions disagree, so the model difference is within noise. The old
  reference figure of 24.7 ms (r2026-10-29-f) did not reproduce (35.3 ms on 0aabc30e); never
  compare across builds - run the pair in one session.

* learned: fused and unfused are byte-identical on the port (r2026-10-30-r vs -s, 2026-10-30,
  both exit 0, three frames, 2560x1440, same card). `serve: graph unfused - reference kernels`
  produced exactly the bytes `serve: graph fused` did (MAD 0.0, 0 changed pixels, PSNR inf).
  So the generic schedule computes what the reference kernels compute, and fusion is safe to
  carry into the small network. Unfused median 234.6 ms vs fused 77.4 ms: the reference path is
  for parity only, never for speed.

* learned: the 310.9.16 small model is real and only ~9% faster end-to-end in NGX
  (r2026-10-30-o/p: preset 1 57.48 ms/frame, preset 2 52.65 ms/frame, 1.09x; pictures differ
  MAD 4.4661, p99 18; old mean [145.8,131.6,142.6], new [146.0,128.4,148.4]). Both entries run
  under xvfb-run. The gain is small because the model is ~11 ms of a ~57 ms Wine frame.

* learned: the 120-frame preset pair is queued as r2026-10-30-o (ngx-old, preset 1) and
  r2026-10-30-p (ngx-new, preset 2), 300s each; nothing measured yet. The next tick reads the
  medians and worker clocks and diffs ngx-old-120.png against ngx-new-120.png; identical
  pictures mean the hint did not switch networks.

* learned: the 310.9.16 small network RUNS on the live path (r2026-10-30-m, 2026-10-30, exit 0,
  7.2s, 3 frames, 0 skipped). Worker log: `direct feature 18 ready: 2560x1440 preset=2
  result=0x00000001`, two warm-up frames discarded, frames 1-3 delivered; worker clock 54.0
  ms/frame. `ngx-live.png` is a real picture (mean 140.8, std 65.4, max 234 - the same
  no-clipping signature as NGX's output). So the earlier six-row matrix said nothing about this
  DLL: its `--test` path creates through the DLL's `CreateFeature` and evaluates through
  `NGX_D3D12_EVALUATE_DLSS_EXT` (Core), which cannot know the DLL's handle. Do not use
  `m0_env_gate.sh`/`ngx_matrix.py` to judge a DLL until `Evaluate()` is changed to call
  `g_nr_evaluate` and the host is rebuilt. The launcher fix (1a28d42) is what made the live run
  possible: a relative `NS_WORKER_CMD` script now resolves against the repo root, because
  `xvfb-run` does not guarantee the repo as the worker's cwd (r2026-10-30-l).

* learned: r2026-10-30-l (`ngx-live`) never reached the network — exit 3 in 3.6s. The worker died
  at frame 0 with `bash: native/run_worker.sh: No such file or directory` (BrokenPipeError while
  sending frame 0), so this run says nothing about the 310.9.16 small model or EvaluateVideo, and
  the "run that decides whether 310.9.16 works" claim above is void. The worker line the policy
  supplies is relative (`bash native/run_worker.sh --prefix /opt/neuralscreen/wine`) and the box's
  staged checkout (`/opt/neuralscreen/state/repo`, per the traceback) evidently has no `native/`
  even though this repo does. Box-side staging or policy fix (absolute path, or ship `native/`):
  no worker run can reach frame 0 until it lands, so the step-1 parity comparison stays blocked.

* learned: the control matrix measured the GATE, not the DLL (r2026-10-30-k, 2026-10-30, exit 1
  in 14.3s). Every direct row failed evaluate 0xBAD00004 for both DLLs and both spoof settings;
  the core row failed earlier at create 0xBAD0000B. The cause is in
  `native/dlss5-feed-host64.cpp`: `CreateFeature` calls `g_nr_create` (the DLL's own
  `NVSDK_NGX_D3D12_CreateFeature`), while `Evaluate()` - the `--test` path - calls
  `SafeEvaluateDLSS`, i.e. `NGX_D3D12_EVALUATE_DLSS_EXT`, which ends in the NGX Core entry point.
  A handle created by the DLL is not known to Core, so it is FeatureNotFound for every preset,
  every DLL and with or without the arch spoof. `EvaluateVideo` (the live path) calls
  `g_nr_evaluate` directly and does not have the bug, which is why the earlier live runs worked.
  So the matrix is not a DLL instrument until the gate's evaluate is fixed; the earlier
  "harness/driver changed" reading of this run was wrong. `r2026-10-30-l` (entry `ngx-live`)
  tests the real path at preset 2 and is the run that decides whether 310.9.16 works.

* learned: the NGX control matrix is queued a second time as `r2026-10-30-k` (2026-10-30 tick,
  entry `ngx-matrix`, 300s, no args/artifacts, id `-j` spent on the argv[0] exec failure) because
  the plan says `xvfb-run` is installed on the box now and the old id cannot be reused. Nothing
  measured yet - the harness still has no SUMMARY row in this repo, so the next tick reads
  `runs/done/r2026-10-30-k/stdout.log` and acts on its verdict rather than queuing again.

* learned: r2026-10-30-j never ran, so the control matrix still says nothing (2026-10-30, read
  the result, no new run). Exit 125, `FileNotFoundError(2, 'No such file or directory')` for the
  entry `xvfb-run -a uv run python tools/ngx_matrix.py --baseline`; the run directory holds only
  command.txt, report.md, request.json and revision.txt - no stdout.log, stderr.log or
  result.json, therefore no SUMMARY row and no measurements. The failure is at exec of argv[0]
  (`xvfb-run` missing on the box's PATH, or the policy argv un-split), so it is not evidence
  about either DLL, the prefix or the driver; the harness never started. Box-side fix needed
  before anything can be read; do not re-queue j.

* learned: the NGX control matrix is queued as `r2026-10-30-j` (2026-10-30 tick, entry
  `ngx-matrix`, 300s, no args/artifacts) and nothing was measured yet. The item stays at the top
  of the plan so the next tick reads `runs/done/r2026-10-30-j/stdout.log` and acts on its
  `SUMMARY` line rather than queuing it a second time. The port-build `r2026-10-30-i` landed
  first, so the harness is being run on the current binary.

* learned: the unfused-parity build half is done and in sync (r2026-10-30-i, 2026-10-30 tick).
  Exit 0 in 8.8s, `port: /opt/neuralscreen/port (9d08f41)`, `patch ... 0aabc30ec374`, 17 files
  changed or added, 15 shader modules / 78 PTX kernels, and the binary's own line says
  "rebuilt: ... is patch 0aabc30ec374..., which is the patch applied - runs will be in sync". So
  the staged binary now carries `serve`'s `DLSS5VK_UNFUSED=1` handling; the only thing still
  missing for step 1 is the box-side policy entry that can set the flag. Nothing was queued this
  pass - step 1 needs `/opt/neuralscreen/policy.toml` to gain a `minimal-unfused` entry (same
  argv as `minimal`, env `NS_WORKER_CMD` + `DLSS5VK_UNFUSED=1`), and step 2 needs the box to hold
  the small model at the path the executor passes to `serve --model`. Both are box configuration
  and stay here rather than being guessed.

* learned: the unfused parity run is unreachable from a request as the box is configured (2026-10-30,
  no measurement; tick before i). `tools/auto_runner.py` builds the worker's env from the policy
  entry only - a request contributes `args`, `timeout_s`, `artifacts`, `manual`, `note` and nothing
  else - so `DLSS5VK_UNFUSED=1` can only arrive through `[entry.env]` in `/opt/neuralscreen/policy.toml`.
  The `minimal` entry there sets `NS_WORKER_CMD` and no unfused flag, and putting the flag on `minimal`
  would make every run unfused, so it needs a second entry (`minimal-unfused`, same argv, env
  `NS_WORKER_CMD` + `DLSS5VK_UNFUSED=1`) installed on the box - box configuration, not this repo.
  The build half is queued as `r2026-10-30-i` (port-build, must stamp `0aabc30ec374`), so the binary
  is current when that entry exists; step 1 stays here until the parity frame can actually be served.

* learned: serve can run the unfused graph now, so the parity comparison the plan asks for is
  actually possible (2026-10-30, patch `0aabc30ec374`, no run). `src/serve.cpp` pinned
  `nr::Graph::Options{.fusedBlocks = true}` while every other entry in `main.cpp` went through
  `fusedBlocksEnabled()` (`DLSS5VK_UNFUSED=1`), which meant a worker run could only ever measure
  the fused graph - the unfused-vs-reference comparison was unmeasurable from the pipeline no
  matter what a queue entry said. serve now has the same static helper, same variable name and
  spelling, so one env set in the policy's entry covers both binaries, and prints
  `serve: graph fused (DLSS5VK_UNFUSED not set)` or `serve: graph unfused - reference kernels
  (DLSS5VK_UNFUSED=1)` before the first frame, because a parity run is only evidence for the
  graph it names. A new test (`test_serve_can_run_the_unfused_graph_too`) reads the served
  source out of the patch and refuses a literal `true` there again. Verified here: the patch
  applies to a pristine 9d08f41 worktree, and `g++ -fsyntax-only -std=c++20
  -DVK_ENABLE_BETA_EXTENSIONS` (repo's volk + Vulkan-Headers) passes on the patched serve.cpp;
  `pytest tests/` 328 pass / 32 skip / 9 failures, the same libGL/SDL2 import errors this box
  always has. NOT verified: no device, so neither the unfused graph's output nor its dispatch
  count. Next: rebuild the staged port (the binary still stamps the previous patch), then the
  box-side comparison against `verify`/`parity` - do not fuse anything until it matches.

* learned: the small network's blend weight is read from the model's own post block now
  (2026-10-30, no run). Step 1 of the integration was half done in the patch: `blockCount_` is
  the model's and the stage table is derived (`schedule --check --model /opt/data/tmp/model-fp8`
  prints 13 stages / 31 blocks / every block in one stage), but serve.cpp still looked the blend
  scale up at a literal block 70. The small model carries it at block30.layer0.blend_scale
  (0.76708984375 against the big model's 0.73974609375 at block70), so the literal missed, the
  catch-all swallowed the throw, and the readout would have printed "absent - defaulted to 1.0"
  and served with a blend cap of 1.0 - a wrong weight that looks like a healthy run, which is
  exactly the failure `check_blend_scale.py` exists for. The read is now
  `model->tensor(blockCount() - 1, 0, "blend_scale")` and the log names the block it read
  ("block30..."/"block70..."), with the found/fallback strings on separate arms. The checker
  transliterates the derivation (refuses a literal index) and still pins the big model's value:
  0.73974609375 at the read's own coordinates, the three neighbouring reads not that value.
  Verified here: patch applies to a pristine 9d08f41 and /opt/data/tmp/odl-verify4 rebuilds in
  sync (17 files, 78 PTX, patch 03246c10b315); `pytest tests/` 327 pass, 32 skip, 9 failures are
  the same libGL/SDL2 import errors this box always has. NOT verified: a device, so neither the
  unfused parity nor any fps. Next is step 2 of the item: serve hardcodes fusedBlocks = true, so
  make it honour DLSS5VK_UNFUSED=1 before the parity run.

* learned: the one-copy upload holds and the creep is gone (2026-10-30, read g and h; tick h+1).
  g is the port-build: exit 0 in 9.6s, `stamp: port 9d08f41 (17 modified) patch 9e90de0d48d0...`,
  15 shader modules / 78 PTX, "runs will be in sync" - so h measured the new binary. h: exit 0,
  120 done / 0 skipped, **40.7 fps steady** (median 24.6ms) against f's 30.63 and 29-f's 40.48 -
  the drop is fully recovered. `proxy` is flat where it used to creep: 5.4 / 6.3 / 6.6 / 6.8 ms at
  frames 29/59/89/119 (f: 6.3 -> 21.3, e: 5.0 -> 10.2), i.e. +1.4ms over the run against +15.0,
  and the split puts it in both halves (copy 3.5 -> 4.2, submit 1.8 -> 2.6) - neither the host
  copy nor the submit carries the old per-frame cost. Strictly, "119 no higher than 29" misses by
  1.4ms on four samples; read that as flat, not as a new creep. network+composite 13.3/13.4
  (29/119) unaffected, as it should be. Headline 15.6 fps is still the frame-0 warm-up (recv max
  4396.7ms at frame 0 of 120).

* learned: the one-copy upload is queued as two entries, build then measure (2026-10-30, tick f+1;
  no run). r2026-10-30-g is the port-build (stamp must name 9e90de0d48d0) and r2026-10-30-h is the
  120-frame f-shaped run; the pair exists because a verification run queued without a build
  measures the previous binary (the a/b lesson). Nothing read yet - accept only on h's numbers,
  and read g's stamp first.

* learned: the creep is in the host copies, not in preprocess, and the upload path cannot hold
  state (2026-10-30, read d/e/f against 29-f; no run). `proxy` is `since(began, afterUpload)` -
  the two `Context::upload` calls only; the expand and preprocess dispatches are inside
  `network+composite`. That upload code is byte-identical between the fast build (4b934233b924,
  29-f, 40.48 fps) and the slow one (7b827810f679, d/e/f): the 0305d1a..56cfb43 diff adds
  nr_schedule/nr_graph/nr_model and leaves serve.cpp, vk_context.cpp and kernels.cpp's upload
  path untouched, and upload allocates nothing per frame (staging_ is created once; every command
  buffer is freed after its wait). What does move is every 29.5MB host copy around /dev/shm: the
  client's own send doubled (median 2.0 -> 3.9ms, min 1.7 -> 2.7) and the worker's proxy memory
  copy climbed (5.0 -> 10.2 in e, 6.3 -> 21.3 in f) while every GPU stage stayed flat
  (network+composite 12.7/12.7/12.8/12.9 in 29-f against 13.4/13.4/14.6 in f). "The loss is
  entirely in preprocess" was also wrong arithmetic: worker totals are 18.5 of 29-f's 24.7ms
  median frame and 19.6 of f's 32.6, so the +7.9ms/frame is capture +0.6, send +1.9, recv +5.5
  (worker only +1.1). And f's 21.3ms proxy is one sample at frame 89 on a frame that took 35.9ms
  overall - read it as one bad frame until a run prints more than four samples. Why the copies
  slow across a run is still unattributed (page pressure, CPU contention with the client, THP);
  the next item removes two of the three copies and splits the timer so a run can say which half.

* learned: the proxy creep reproduces, so it is not box contention (r2026-10-30-f, 2026-10-30).
  Exit 0 in 9.6s, 120 done / 0 skipped, stamp `patch 7b827810f679` in sync. Steady 30.63 fps
  against r2026-10-29-f's 40.48 and e's 34.51 - the third reading below 40, so the drop is real.
  Headline 13.37 fps is the frame-0 warm-up (recv max 4593.4ms at frame 0 of 120) and should be
  ignored. `network+composite` is flat at 13.4/13.4/14.6ms (frames 29/59/89) while `proxy` reads
  6.3/5.7/21.3ms - the growth is late (~frame 89) rather than linear, which points at something
  accumulating per frame in preprocess rather than a constant extra cost. Next item is the proxy
  stage itself; the recorder is not implicated.

* learned: the table-driven recorder publishes the same frame (2026-10-30, read d and e). d, on
  stamp `patch 7b827810f679`, wrote before.png/after.png whose blobs are byte-identical to 29-e's
  (a1bafe2d07 / 1975cb4479): the schedule change moved no pixel, so the recorded graph is the
  same work. e, same stamp, exit 0, 120 done / 0 skipped: 14.73 fps headline (frame-0 recv
  4260.5ms) and 34.51 fps steady against 29-f's 40.48. The worker's own lines locate the loss:
  network+composite is flat (12.9/13.4ms at frames 29/119 vs 12.7/12.9 in f) while `proxy` climbs
  5.0 -> 10.2ms across the run where f holds 3.7-5.8, and client recv median rises 19.9 -> 22.9.
  A 15% steady drop whose whole size sits in preprocess is not evidence against the recorder, so
  step 1 was not reverted; r2026-10-30-f repeats the shape to see whether it reproduces.

* learned: the port-build the schedule change needed has landed and is in sync (r2026-10-30-c,
  2026-10-30): exit 0 in 9.6s, `stamp: port 9d08f41 (17 modified) patch 7b827810f679...`, 15
  shader modules / 78 PTX kernels, and the binary's own stamp line says "runs will be in sync".
  So r2026-10-30-d/-e are the first runs that can say anything about the table; a/b still cannot.

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

* learned: the shm frame is copied once and both copies share one submit (2026-10-30, commit
  284b11d, patch `9e90de0d48d0`). `serve.cpp` no longer memcpys a mapped frame into `colour` (it
  only does when a bypass reply wants the client's own pixels back); `Context::uploadAll` fans the
  colour and motion jobs into ONE staging pass, ONE command buffer and ONE wait, and reports the
  two halves, so the worker line is now `proxy X [copy Y, submit Z]`. `colour`'s pipe path and the
  old `upload` are unchanged; >staging-window jobs fall back to the old per-buffer path. Verified
  here: the patch applies to a pristine 9d08f41 and `/opt/data/tmp/odl-verify4` rebuilds in sync
  (17 files, 78 PTX); `pytest tests/` 327 pass, 32 skip, and the 9 failures are the same libGL/SDL2
  import errors this box always has. NOT verified: the GPU path (no device here) and the shaders -
  glslang is not installed in this container, so the build reused the existing SPIR-V; no shader
  was touched. Two things for the next tick: `tests/test_native_serve_shm.py` now fails one case
  with `NS_ODL_NATIVE_BIN` set because it asserts inline pixels for a frame sent with
  `want_pixels=False` - that expectation predates c66c7e8 (2026-10-29) and is unrelated to this
  change, but it means "pytest green with the native binary" is not a claim anyone can make yet;
  and the box must rebuild the port before the measuring run, or it measures 7b827810f679 again.

* learned: the port's block-count guard is relaxed (nr_graph.h/.cpp): `kBlockCount` became a
  member `blockCount_`, set from the model, so a non-71 model loads beside the 71-block parity
  reference; the big model's path is untouched. The suite still has the 9 pre-existing libGL/SDL2
  import failures; 320 tests pass.

* learned: `r2026-11-02-bc` answers the pipelining question, and the answer is no (2026-11-02 tick).
  Exit 0, 120/0, 1440p with pixels, same worker patch as bb (`0aabc30ec374` at port 9d08f41) and a
  client tree that differs from bb's c44718c only by docs commits - so `--send-ahead 2` is the only
  variable. Steady median **44.7 ms / 22.4 fps** against bb's serial **39.7 ms / 25.2 fps**: 5 ms
  *worse*, not better. The mechanism is in the split, not the total - `send` median 5.2 -> **35.1 ms**
  (min 10.4) while `recv` median 29.4 -> **0.0 ms**, and the sum is unchanged (bb 34.6; bc 35.1). The
  wait did not go away, it moved into the send. A pipe with one reader cannot hold two frames in
  flight: writing frame N+1 blocks until the worker reads it, and the worker only reads after it
  finishes N - which is what `loop.py`'s own docstring already said ("pipelining would need a second
  frame slot"). The worker's own clock also reads higher under it (frames 29/59/89/119: 33.9/36.2/
  31.9/28.8 ms against bb's 25.9/25.3/29.1/24.8), 26 -> ~33 ms; whether that is two-in-flight memory
  traffic or noise is not settled. Two side readings: bc's send max 4411.9 ms lands at frame 1, which
  is exactly where a send-ahead pipeline puts the worker's JIT warm-up (the second send blocks while
  the worker warms), so the report's "a one-off at frame 1 - not the warm-up, so worth looking at" is
  wrong - the heuristic at `minimal/__main__.py:312-316` exempts frame 0 by index only; and
  **bc's `bc-1440p.png` is byte-identical to bb's (`4dc4d07bec92f58134ec01e8221e25e049557c4f`), so
  send-ahead moves no pixel** - the flag is a timing knob only, as claimed. Verdict: pipelining on the
  pipe path is a dead lever at 1440p; the serial loop stands and the only place the client can
  overlap a computing worker is shared memory, which is `r2026-11-02-bd`.

* learned: `r2026-11-02-bd` answers the transport question, and the answer is shared memory
  (2026-11-02 tick). Exit 0, 120/0, 1440p with pixels, `--shm --send-ahead 2`, worker patch
  `0aabc30ec374` at port 9d08f41. Steady median **26.5 ms / 37.7 fps**, against bb's pipe serial
  39.7 ms / 25.2 fps and bc's pipe+send-ahead 44.7 ms / 22.4 fps. The split shows why: send median
  **2.3 ms** (min 1.6, max 5.7 at frame 0) and recv median **16.8 ms** (max 4091.6 at frame 0),
  against bc's send 35.1 / recv 0.0. The send does not block on shm, and the client's steady frame
  sits *below* the worker's own per-frame time (frames 29/59/89/119 read 28.4/29.3/28.4/24.2 ms), so
  the second frame really does overlap - bc's serialisation was the pipe, not the worker's loop.
  bd changes two things at once (shm and send-ahead 2), so how much of the ~13 ms gain is transport
  and how much is concurrency is still open; `be` separates them. Also fixed the mislabel bc
  exposed: `spread_line` now treats a peak as the warm-up when its frame precedes the worker's
  first reply (`at <= send_ahead - 1`) instead of only at index 0, so a send-ahead run's 4.4s block
  at frame 1 is no longer called a stall. Suite 363 pass / 32 skip / 9 fail, the same libGL/SDL2
  import errors this box always has.

* learned: `r2026-11-02-be` is queued (2026-11-02 tick) - the shm-serial 1440p-with-pixels run,
  bd's shape (`--shm`) minus `--send-ahead 2` (`runs/queue/r2026-11-02-be.json`, artifact
  `be-1440p.png`). bd changed two variables at once (shared memory and the second frame in
  flight), so be changes one and separates transport from concurrency; nothing is measured yet.
  The next tick reads be's send/recv split against bd's 26.5 ms (send 2.3 / recv 16.8) and bb's
  39.7 ms - a steady median near 26 ms means transport alone is the win, near 40 ms means the
  overlap is. be's after.png should be byte-identical to bb's and bc's
  (sha 4dc4d07bec92f58134ec01e8221e25e049557c4f) - the flag is a timing knob only. After be the
  plan's last enumerated run is spent, and the remaining lever (the worker's own readback + reply
  + neural pass) waits on the reply-format product decision in "Ask first", so the pipeline pauses
  there rather than repeating known numbers.

* learned: `r2026-11-02-be` closes the transport-vs-concurrency question, and the answer is the
  transport (2026-11-02 tick). Exit 0, 120/0, 1440p with pixels, `--shm` serial (bd's shape minus
  `--send-ahead 2`), worker patch `0aabc30ec374` at port 9d08f41, gate released at WARN with no
  wait; `gpu_before` and `gpu_after` both WARN (resident, not contending). Steady median **26.4 ms
  / 37.9 fps** against bd's shared-memory-plus-overlap **26.5 ms / 37.7 fps** - identical to 0.1 ms
  - so the second frame in flight buys nothing once the frame is in shared memory, and the whole
  ~13 ms win over bb's pipe serial 39.7 ms is the transport. The split says it twice: be's send
  median **1.2 ms** (min 1.1, max 5.4 at frame 0) and recv median **20.4 ms** (max 3952.5 at frame
  0) against bb's send 5.4 / recv 29.4. Both ends get cheaper - the client's send stops blocking
  (~4 ms), and the worker's own frame drops from bb's 25.9/25.3/29.1/24.8 ms at frames 29/59/89/119
  to 20.2/18.1/18.1/19.4 (`network+composite` 14.4 -> 12.2, `reply` 4.8 -> 1.7) - because shared
  memory removes the worker's blocking 14.7 MB pixel write as well as the client's frame write.
  So `--send-ahead` is only ever a liability here: free where frames already overlap (bd 26.5 vs be
  26.4, inside noise) and actively harmful where they cannot (bc 44.7 vs bb 39.7, the pipe read
  serialising). be's `be-1440p.png` IS byte-identical to bb's and bc's (sha256
  `28292742c88b8e016245b5f00cadc1748b5e93...`), so on the serial path the wire moves no pixel -
  but bd's saved frame is not (mean abs diff 0.41 levels/channel, max 13), which is the loose end
  now first in section 1 and what `r2026-11-02-bf` is for.

* learned: `r2026-11-02-bf` is queued (2026-11-02 tick) - the determinism repeat in bd's exact shape
  (`--shm --send-ahead 2`, artifact `bf-1440p.png`, `runs/queue/r2026-11-02-bf.json`). Nothing
  measured yet, and there is no timing to read: it exists to arbitrate bd's non-identical frame
  (mean abs diff 0.41 levels/channel, max 13, 37% of bytes differ) against be's byte-identical one
  (`28292742c88b...`). `bf == bd` means shared memory plus the second frame in flight
  deterministically changes the output and every "moves no pixel" claim needs that caveat; `bf == be`
  means bd was a one-off and no image diff across runs can be quoted. The next tick reads
  `bf-1440p.png` against bd's and be's. With bf queued the last enumerated run is spent and
  section 1 has nothing left to queue - the next build waits on the reply-format product call in
  "Ask first", so the pipeline pauses there rather than repeating known numbers.

* learned: `r2026-11-02-bf` settles the determinism question, and bd was not a one-off (2026-11-02
  tick). Exit 0, 120/0, 1440p with pixels, bd's exact shape (`--shm --send-ahead 2`), worker patch
  `0aabc30ec374` at port 9d08f41. `bf-1440p.png` is **byte-identical to bd's** (both sha256
  `1694ccd3a5061be525512aab233df38d93bd3351803ddcc56c89ca6e0faa874f`, 2,818,146 bytes) and not to
  be's (`28292742c88b...`), so shared memory *plus* the second frame in flight reproducibly changes
  the saved frame - the diff is real, not a one-off, and "shared memory + send-ahead 2 moves no
  pixel" (bd's own note) is false as written. The safe claim is now: on the serial shm path
  (`be == bb == bc`) the wire moves no pixel; with `--send-ahead 2` it does, deterministically. So
  `--send-ahead` is not purely a timing knob - it is free where frames already overlap (bd 26.5 vs
  be 26.4 ms) but it changes the output, which matters for any pixel-identity gate. Cause still
  unattributed (the worker's temporal history under overlap, or the save path); the read was
  pixels-only, so no timing was re-measured. Nothing queued this tick: the last enumerated run is
  spent and the only remaining lever, the worker's pixel channel, waits on the reply-format product
  call in "Ask first".

* learned: `r2026-11-02-bh` completes the shm table, and the transport finding holds with no
  reply crossing (2026-11-02 tick). Exit 0, 120/0, 1440p **no pixels**, `--shm`, worker patch
  `0aabc30ec374` at port 9d08f41, same 120-frame shape as ax/ay, no `--save-after` so no byte
  comes back - that is the point. Steady median **18.5 ms / 54.1 fps** (the 50.4 ms / 19.9 fps
  headline is the 3787.1 ms frame-0 recv), against ax 25.8 / ay 26.4 on the pipe: **7.5 ms off**,
  so the shm win is not "no reply crosses", it is the transport. Split: capture 2.6, send 1.4
  (min 1.1, max 5.1 at frame 0), recv 14.7 (min 14.2, max 3787.1 at frame 0), display 0.0; worker
  14.8 / 14.8 / 14.3 / 14.5 ms at frames 29/59/89/119 = network+composite 12.1 + proxy 2.5 +
  readback 0 + reply 0. Against `be` (1440p, pixels, shm, 26.4 ms) the pixel channel is **7.9 ms**
  at 1440p under shm, not the 13.6 ms the bb-vs-ax pipe pair showed - so the pipe's own 14.7 MB
  reply read was ~6 ms of that, and the 2.3 + 1.7 ms the worker logs for readback+reply is not the
  whole channel (the rest is the client's shm read). 18.5 ms is 1.8 ms over the 16.7 ms 60 fps
  budget, so even a pixel-free 1440p frame does not clear 60 fps and the shippable floor is
  26.4 ms with pixels; the pixel channel (7.9) and the neural pass (12.7) are the only levers left,
  both waiting on the reply-format call. bh landed between the two branches the request named (14
  and 22-26 ms) and closer to neither, so quote 18.5, not an interpolation. Nothing queued this
  tick: no remaining timing shape adds a number, and the 1080p shm no-pixel control is off-target
  with 1440p fixed. The `--shm`-as-default question is now under "Ask first".

* learned: `r2026-11-03-live-1440p` ran the real product path and the input leg is NOT the
  bottleneck the plan feared (2026-11-03 tick). Exit 0, 120/0, portal capture of a live window at
  2560x1440, `--shm`, pixels saved; worker patch `0aabc30ec374` at port 9d08f41, in sync. Steady
  median **46.6 ms / 21.5 fps** (the 87.8 ms / 11.4 fps headline is the frame-0 warm-up: recv max
  4664.3 ms at frame 0). The capture split reads **read 13.1 ms** against the 19 ms "stocked pipe"
  reference - under it, so the compositor was not dribbling and the predicted ~45 ms pre-worker
  frame did not materialise. Client split: capture 13.4, send 2.6, recv 66.9, display 4.9 mean;
  worker steady 21.2/24.7/24.5/22.4 ms at frames 29/59/89/119 (proxy 3.6-4.5, network+composite
  ~13.2, readback 2.9-5.5, reply 1.1-2.0). So the live path lands within ~4 ms of the synthetic
  pixel runs' worker cost; the 46.6 ms frame is dominated by the ~40 ms recv+handoff, not by a
  slow input leg. Capture CPU 39% of one core (4.19 s over 10.82 s). gpu_before/after both WARN
  (resident, not contending), idle_waited_s 0.0. The "app case is unreal" hypothesis is refuted;
  the lever remains the worker's own frame, as recorded above.
