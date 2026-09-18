# M0 findings — the gate runs on the RTX 4080 SUPER

Two runs so far. The error code is walking forward, which is the point of the
gate: each failure names the next missing piece.

| run | result | meaning |
|---|---|---|
| `20260916T044806Z` | `0xBAD00001` FAIL_FeatureNotSupported | NGX Core not found at all |
| `20260916T051433Z` | `0xBAD00002` FAIL_PlatformError | NGX Core now loads; NVAPI cannot report the GPU to it |
| `20260916T063248Z` | `0xBAD00002` still, but NVAPI now *explains itself* | DXVK's dxgi.dll was never installed — the setup had only been run with `--check` |
| `20260916T064324Z` | `0xBAD00002` unchanged | a dxgi.dll **was** present, so the install was skipped — but it was Wine's builtin, not DXVK's |
| `20260916T065756Z` | `0xBAD00004` FAIL_FeatureNotFound | **init and feature 18 create now succeed**; the failure has moved to evaluate |
| `20260916T074715Z` | direct unchanged; **via-core fails earlier, at create** (`0xBAD0000B`) | NGX Core cannot create feature 18 at all — and `--test` evaluates through the Core, so M0 was measuring a path the product does not use |
| `20260916T080456Z` | M1: both frames black | capture is X11/`mss` on a **Wayland** session → XWayland root is empty. Said nothing about the pass; M1 now separates the two questions |
| `20260916T105502Z` | M1 **pass PASS** (17.62, matched pair), capture FAIL | pass confirmed, deterministic run-to-run; capture still the only gap |
| — | Wayland backend built | portal + PipeWire capture (`--source auto`), plus `tools/wayland_probe.py` to test capture with no Wine. Not yet run on a compositor |
| `20260916T152209Z` | **M1 both variants PASS** | **the MVP runs end to end on a live desktop**: portal capture, 30/30 frames, no skips, 2560x1440, pass changes the screen by 4.55/255 (17.62 on the test card). 3.31 fps |
| `20260916T155332Z` | M1 three variants; **baseline is byte-identical** | the transport is **lossless**: effect off returns the same SHA256. So the pass's numbers are entirely the network, and `intensity=0 local_tone=0 local_structure=0` is a verified bypass |

**What the first run proved and the second confirmed** — the expensive half:

```
[host] adapter 0: NVIDIA GeForce RTX 4080 SUPER vendor=0x10DE
[pure] standalone D3D12 device ready; no swapchain or carrier modules
```

Wine runs the PE with all its static imports, DXGI enumerates the card at vendor
`0x10DE` (the worker rejects anything else), and `D3D12CreateDevice` succeeds.
D3D12 over Wine + VKD3D works on this machine. That was the risk that could have
killed the port outright; it is cleared.

---

# Round 25 — the capture chain is 33% of a core, and the ceiling this architecture has

`20260918T132847Z` produced the measurement the last three rounds were for:

```
capture    capture cpu: the pipeline used 1.25s over 3.81s = 33% of one core
capturens  (the same, before this round's change)
```

**33% of a core, both capture variants, at 2560x1440.** Over 30 frames that is
**~42ms of CPU per frame** spent in the capture chain — PipeWire delivery, a
format conversion, a scale and a 14.7MB write into the pipe. That is the same
order as the 18-47ms the worker's `send` pays extra when the source is the portal
rather than a synthetic card, so the contention reading is supported. Not proven:
two costs of the same size are not the same cost, and only a run with the chain
made cheaper will show whether `send` follows it down.

## The one lever in our own code

Everything else worth attacking lives in a binary we cannot rebuild, so this is
the only element available: **`--capture-no-scale`** drops `videoscale` from the
pipeline, one 14.7MB pass out of the chain. It stays off by default because the
element is deliberate — the portal's reported size and the stream's actual size
can disagree, fractional scaling on Plasma being the easy way, and then caps
negotiation fails instead of scaling. The failure is loud and names itself.

The gate swaps `capturebp` for `capturens` to measure it. `capturebp` had served
its purpose: the pass's price at 1440p is known from `pass14 - bypass14`, and the
real-screen version was the least reproducible row in the table.

## The ceiling, stated plainly

Four rounds of decomposition now agree on this:

| | no NGX at all | with the pass | pass's share |
|---|---|---|---|
| 1280x720 | 51.1ms (19.6 fps) | 78.6ms (12.7 fps) | 27.5ms |
| 2560x1440 | 85.5ms (11.7 fps) | 98.6ms (10.1 fps) | 5-13ms |

**With the network switched off entirely, a 2560x1440 frame still costs ~85ms and
a 1280x720 frame ~51ms.** That is the floor of this architecture, and it is the
frame's journey: read out of the capture pipe, written into the worker's stdin,
uploaded to a D3D12 texture, read back, written back down the pipe, uploaded to
the display. The pass is 5-13ms on top at 1440p and 25-30ms at 720p — visible
only at the smaller size, because at the larger one it hides behind four times
the copying.

So: **~12 fps at 2560x1440 and ~20 fps at 1280x720, with the pass costing almost
nothing at the top size.** Trimming the capture chain might move this by 10-20ms.
Nothing else on this side of the boundary will. Getting to usable rates means not
putting the frame on the CPU at all, which is a different piece of work — a host
of our own, with the frame arriving over a memory-mapped file that both a native
process and the Wine process can see — and that is a project rather than another
variant.

---

# Round 24 — the CPU reading failed because I sampled it after closing it

`20260918T131218Z` printed the line, and the line said why:

```
capture cpu: NOT measured — the source reports its own CPU but the reading
             failed — check /proc/<pid>/stat for the pid above (pid None)
```

`pid None` was the clue: `pipeline_pid` reads `self._proc`, and `_proc` is set to
`None` by `close()` — which `run()` calls in its `finally`, **before** the return
statement builds the summary. So the end sample was taken after the pipeline was
gone, which is why the pid was `None` and the reading failed. Both symptoms, one
cause, and it was in my code rather than in `/proc`.

The end sample now happens in the `finally` before the capture is closed. The
regression test uses a fake whose `close()` removes the reading exactly as
`PortalCapture` does, and it was verified by reintroducing the bug: the test
fails, and passes again with the fix.

Worth noting the shape of it, because it is the fourth time: a measurement whose
number was produced at the wrong moment. The age that was read when `stats()` was
called instead of when the frame was taken; the flaky test comparing a frame
against a count read afterwards; the split that a buffered read swallowed; and
now this. The lesson is not "be careful with timing" but that any derived number
should be recorded at the moment it happens, and read back later.

Also confirmed on the box: the prefetch flakiness is gone (164 passed, 0 failed,
against 1 failed the run before).

## And the 5ms figure did not hold this time

| network's price | `120102Z` | `122822Z` | `124926Z` | `131218Z` |
|---|---|---|---|---|
| 1440p synthetic | 5.4ms | 4.8ms | 5.7ms | **13.1ms** |
| 720p synthetic | 24.4ms | 39.8ms | 32.4ms | 27.5ms |
| 1440p real screen | 9.5ms | 44.3ms | 9.5ms | 9.5ms |

So the 1440p figure is **5-13ms**, not a stable 5. I called it "the one number
that keeps holding" one round too early. What survives is the conclusion rather
than the figure: 5-13ms against a 100-135ms frame means the pass is not where the
time goes at this size, whether the true value is 5 or 13. What does not survive
is quoting any particular millisecond value for it.

Everything else in the run was healthy: the capture legs were 11.0ms and 10.4ms
with no slow-mode stall, and the two capture variants agreed on `send` to within
0.4ms (90.3 against 90.7).

---

# Round 23 — a test of mine failed on the box, and the capture wait is bimodal

`20260918T124926Z`. Three things, one of them a bug I shipped.

## My prefetch test failed, and the test was wrong

```
assert latest == stats["drained"] % 251
AssertionError: got frame 0, newest drained was 44430
```

The frame was grabbed *now*; `drained` was read *after*. With a fake source that
produces flat out, three more frames land in between, so the assertion compared
two different moments — the same mistake as the age bug two rounds earlier,
where a value was read at the wrong time and looked like a measurement.

Fixed by recording the drain sequence number **when the frame is taken**
(`stats["seq_taken"]`) and comparing against that. Twenty-five consecutive runs
pass. Loosening the assertion would have hidden the thing it is for: that the
consumer gets the newest frame, not one that was queued.

## The `capture cpu:` line never printed

The code path is right — `_capture_cpu_summary` was called, the key was in the
summary — so on the box either the source had no reading or the reading failed.
My first version omitted the line in both cases, which is indistinguishable from
"the chain used no CPU" and is precisely the failure mode this whole area keeps
producing: a measurement that isn't there, looking like a measurement that says
zero.

It now distinguishes three outcomes:

```
capture cpu: the pipeline used 1.42s over 4.31s = 33% of one core
capture cpu: NOT measured — the source reports its own CPU but the reading
             failed — check /proc/<pid>/stat for the pid above (pid 3156709)
<no line>   the source cannot report its own CPU (a synthetic source has none)
```

So the next run says which it was, instead of costing another round trip to
guess.

## The third replication, and a bimodal grab

The 1440p synthetic figure came in at **5.7ms** (pass14 102.8 − bypass14 97.1),
so the network's price at 2560x1440 is now **5.4, 4.8, 5.7** across three runs.
That is the one number in this area that has held every time it was measured.

And the capture leg inflated again — on `capturebp` this run, 313.3ms against
`capture`'s 32.9ms. Every split recorded so far:

```
083240Z capture      wait 225.3ms  read 12.7ms   <- producer slow
100600Z capture      wait   0.1ms  read 14.8ms
102028Z capture      wait   0.1ms  read 15.3ms
113304Z capture      wait  14.6ms  read 13.6ms
120102Z capture      wait  21.1ms  read 11.7ms
124926Z capture      wait  21.1ms  read 11.7ms
124926Z capturebp    wait 303.3ms  read  9.9ms   <- producer slow
```

**`read` is 9.9-15.3ms in every one of the seven** — our copy, and it never
varies. `wait` is bimodal: 0-21ms, or 225-303ms. So the grab is never our end,
and when the total inflates it is the compositor being late by 200-300ms and
everything downstream inheriting it. Two of seven, on whichever capture variant
happens to hit it, which is why the real-screen totals are the least reliable
numbers in the gate.

The gate now says so itself, printing `PRODUCER IN SLOW MODE` against any variant
whose wait exceeds 100ms, rather than leaving a 400ms row to be read as the pass
being slow.

---

# Round 22 — what replicated, what didn't, and moving the CPU reading into the run

Two runs of the same nine variants, and one of round 21's numbers did not
survive:

| network's price | `120102Z` | `122822Z` |
|---|---|---|
| 720p synthetic | 24.4ms | 39.8ms |
| **1440p synthetic** | **5.4ms** | **4.8ms** |
| 1440p real screen | 9.5ms | 44.3ms |

**The 1440p synthetic figure replicated** (5.4, 4.8): the network costs ~5ms at
2560x1440, and that is now measured twice. **The real-screen figure did not**
(9.5 against 44.3), so `capture - capturebp` is too variable to carry the claim
on its own and should not be quoted without a repeat.

The portal gap replicated in direction but not magnitude: the same 2560x1440
frame cost `send` 47ms more through the portal than synthetically in one run and
18ms more in the other (+70% and +30%). Worth chasing, not worth quantifying
until the CPU reading explains it.

## The reading belongs in the run, not in a separate command

Twice now a report has come back without the probe output, and the CPU share is
the measurement that would explain the whole portal gap. Asking again would be
the third time, so the MVP now reports it itself: `PortalCapture.cpu_seconds()`
reads the pipeline's `/proc/<pid>/stat`, `Pipeline.run` samples it around the
loop, and every run prints

```
capture cpu: the pipeline used 1.42s over 4.31s = 33% of one core
```

with a warning when it exceeds half a core, since that work runs while the
worker waits rather than instead of waiting.

The reader lives in `minimal/cpu.py` and both the probe and the MVP use it.
Written twice it would drift — which is exactly what happened to the worker's
launch environment in an earlier round, and the reason that one is enforced by a
test. The reader is verified against a busy process (100% of a core), an
executable whose name contains a space (the comm-field trap, and the test asserts
the space is really there), an idle sleeper (0) and a missing pid (`None`, never a
fabricated zero — a zero would read as "the chain did nothing", which is the
opposite of the case worth knowing about).

---

# Round 21 — the network is not the cost at 1440p, and the capture chain steals from the worker

`20260918T120102Z`, all nine, and the first run where the 1440p matrix cost no
dialog:

```
720p   pass       93.6ms  send  77.5ms  recv  9.5ms
720p   bypass     69.2ms  send  51.4ms  recv  8.7ms
1440p  pass14    129.3ms  send  67.3ms  recv 29.8ms
1440p  scaled14  122.8ms  send  60.1ms  recv 26.1ms
1440p  bypass14  123.9ms  send  66.2ms  recv 23.9ms
1440p  capture   174.2ms  send 114.2ms  recv 41.0ms
1440p  capturebp 164.7ms  send 111.9ms  recv 32.7ms
```

## The fork resolved to "small"

```
pass14 - bypass14    = 5.4ms      the network's price at 1440p, no portal
capture - capturebp  = 9.5ms      the same on a real screen
```

**The network costs 5-10ms at 2560x1440.** So the 129-174ms is the frame's own
journey — upload, readback, copy across the Wine boundary — and round 19's
per-pixel model was not just wrong in magnitude but wrong about the sign of what
matters at this size. The thing to attack is what crosses the boundary, which is
what writing our own host addresses.

`capturebp` is byte-identical again (`mean abs diff 0.0000`), so the control
holds at 1440p as well as at 720p.

## The inversion worth noticing

| | no-NGX | network cost |
|---|---|---|
| 1280x720 | 69.2ms | **24.4ms** |
| 2560x1440 | 123.9ms | **5.4ms** |

The network costs four times as much at a quarter of the pixels. No arithmetic
model produces that. The readings consistent with it: at 720p there is not much
copying, so the network's GPU time is exposed; at 1440p the same GPU time hides
behind four times the copying, and only 5.4ms of it shows.

That also disposes of the work-scale question for good. `scaled14` is within 6ms
of `bypass14` — with the network hidden behind the copies, there is nothing for
`nr_small` to save, which is why `capturews` bought nothing either.

## The capture chain steals from the worker

The largest new number in the run is a comparison, not a variant: the same
2560x1440 frame at the same settings costs `send` **114.2ms** arriving through
the portal and **67.3ms** produced synthetically. **70% more, and none of it
appears in the capture leg** (14.4ms against 29.2ms — the capture leg is *cheaper*
in the portal case).

So the live capture chain — PipeWire delivery, `videoconvert`, `videoscale`, the
pipe — costs the frame ~47ms somewhere other than the grab. The obvious reading
is CPU and memory-bandwidth contention with the worker, since the chain copies
and converts 14.7MB per frame in software while the worker is doing its own
copies.

`wayland_probe.py` now reports the chain's own CPU share
(`/proc/<pid>/stat`, verified: 100% of a core for a busy process, correct for an
executable whose name contains a space, 0 for a sleeper, None for a missing pid).
If that line comes back near a full core at 2560x1440, the contention is real and
the next work is trimming the capture chain rather than anything to do with the
pass.

---

# Round 20 — the per-pixel model is falsified, and the 1440p matrix moves off the portal

`20260918T113304Z` tested the prediction directly:

```
capture    work 2560x1440  capture 14.3ms  send 82.0ms  recv 38.7ms  (139.7ms, 7.2 fps)
capturews  work 1280x720   capture 14.4ms  send 99.3ms  recv 30.0ms  (148.0ms, 6.8 fps)
```

The model said ~85-90ms. It came back at 148.0, against 139.7 for full work
resolution. **Halving the network's own resolution at 1440p bought nothing** —
the 8ms difference is inside the spread the NGX rows show between runs, so the
honest reading is "no win", not "worse".

So at 2560x1440 the cost is not the network's arithmetic, and round 19's model is
wrong. What was wrong with it: `scaled` at 720p shrinks **two** things (the
network's resolution and the motion field), and the +31ms I attributed to the
network came from `pass` against `bypass` — which is a *strength* effect, not a
resolution one. Turning one 0.92-megapixel data point into a per-pixel rate and
extrapolating it to 3.69 megapixels was not justified, and `nr_small` also adds
two scaling passes inside the worker (colour down into `nr_in`, `nr_out` back up
into `output`) which appear to cost more than the arithmetic they save.

One thing the run does establish: the effect's magnitude barely depends on the
work scale. `capture` 4.7460/255 at full work resolution, `capturews`
4.5626/255 at half (PSNR 28.5 against 30.7). So the work scale is close to free
in quality — it simply does not buy speed either, so there is no reason to use it.

## The method was the problem

Every 2560x1440 data point so far has cost a compositor dialog and a whole run
for two numbers, which is how the 1440p cost stayed unmodelled for four rounds
and why each guess about it was wrong.

`--size WxH` removes that: the synthetic source can now render any size, so the
full pass/scaled/baseline/bypass matrix runs at 2560x1440 with **no portal, no
dialog and no capture**. The gate gains `pass14`, `scaled14` and `bypass14` for
exactly that, plus `capturebp` — the same real screen as `capture` with NGX
skipped — so the pass's price at 1440p is measured on both paths.

`pass14 - bypass14` is the number. If it is small, the 139.7ms is the frame's
own journey (upload, readback, copy) rather than the network, and the thing to
attack is what crosses the boundary — which is the own-host pathway. If it is
large, the network is expensive at 1440p for some reason none of the current
variants explain, and the next step is to find it rather than to build around it.

---

# Round 19 — three runs, a stable floor, and a per-pixel cost model

Three consecutive runs of the same six variants, which is the first time there is
enough to separate signal from drift:

| variant | `083240Z` | `100600Z` | `102028Z` | spread |
|---|---|---|---|---|
| bypass | 60.5ms | 62.2ms | 60.7ms | **1.03x** |
| baseline | 74.5ms | 70.6ms | 71.2ms | 1.06x |
| scaled | 69.6ms | 71.3ms | 61.3ms | 1.16x |
| pass | 134.5ms | 98.3ms | 95.6ms | 1.41x |
| capture | 364.8ms | 148.9ms | 153.1ms | 2.45x |

The no-NGX floor is essentially exact across all three (60.5, 62.2, 60.7). What
varies is what runs the network: `pass` 1.41x and `capture` 2.45x. So the spread
lives in the **GPU path**, not the plumbing — `bypass` was unmoved while `pass`
and `capture` inflated together in the first run.

That also disposes of two of my readings. Round 16's 238ms capture leg came from
the anomalous run: the same variant measured 14.9ms and 15.5ms in the two runs
that agree with each other. So "the capture is the ceiling" (round 13) and "the
loop is throttling the producer" (round 17) were both readings of one bad run,
and round 18's "only within-run comparisons are safe" overcorrected — the plate
below is what actually holds:

* the CPU-side floor is reproducible to a few percent
* anything running NGX varies by up to 2.5x with GPU state, so *those* rows need
  repeats before being believed
* and the two runs that agree are consistent to within a few percent throughout,
  so cross-run comparison is fine when the runs agree and useless when they don't

## The cost model, from the two runs that agree

Isolating on `send`, which is the dominant leg and the one that carries the
worker's intake:

| variant | network | `send` | over no-NGX |
|---|---|---|---|
| bypass | — | 48.4ms | — |
| scaled | 640x360, full strength | 49.8ms | +1.4ms |
| baseline | 1280x720, zero strength | 51.6ms | +3.2ms |
| pass | 1280x720, full strength | 79.6ms | **+31.2ms** |

Zeroed strengths are nearly free and a quarter-size network is nearly free, but
full strength at 1280x720 costs 31ms on 0.92 megapixel. The upstream figure on a
5070 Ti is `1.5ms + 1.51ms/Mpixel` = 2.9ms at the same size, so this stack costs
**~11x per pixel**. Extrapolated to 3.69 megapixel that is ~125ms of the ~150ms
frame — which is what `capture` measures at 1440p.

So at 2560x1440 **the pass is the cost, not the plumbing** — the opposite of the
conclusion the 720p rows supported, and the reason `send` looked
resolution-independent: at 720p the plumbing and the pass are comparable in size,
and at 1440p one of them triples.

## Which makes the network's own resolution the lever

`capturews` runs 2560x1440 output with the network working at 1280x720. The model
predicts ~85-90ms against `capture`'s ~150ms. If it lands there, 1440p fullscreen
roughly doubles — not to 60 fps, but from 6.5 to something in the low teens — and
the trade is the effect's own resolution, which for a subtle effect on a
compressed stream may be no trade at all.

If it does *not* land there, the per-pixel model above is wrong and the 31ms is
something other than the network's arithmetic, which is worth knowing either way.

---

# Round 18 — prefetch did not help, and the capture leg is not stable

`20260918T100600Z`, six variants:

```
pass       capture   5.9ms  send  81.7ms  recv 10.2ms  display 0.6ms  ( 98.3ms, 10.2 fps)
scaled     capture   7.7ms  send  52.4ms  recv 10.4ms  display 0.9ms  ( 71.3ms, 14.0 fps)
baseline   capture   6.3ms  send  53.4ms  recv 10.2ms  display 0.7ms  ( 70.6ms, 14.2 fps)
bypass     capture   5.9ms  send  48.9ms  recv  6.8ms  display 0.6ms  ( 62.2ms, 16.1 fps)
capture    capture  14.9ms  send  87.8ms  recv 41.6ms  display 4.6ms  (148.9ms,  6.7 fps)
capturepf  capture   0.0ms  send 132.5ms  recv 49.7ms  display 6.1ms  (188.3ms,  5.3 fps)
```

## `--prefetch` made it worse

Same capture, same run: **148.9ms without, 188.3ms with.** The capture leg
collapsed to 0.0ms as designed, and `send` rose from 87.8ms to 132.5ms — the
drain thread and the worker are both moving 14.7MB frames and compete for memory
bandwidth. 14.7MB at 75fps is ~1.1 GB/s sustained, and the worker needs that same
bandwidth for its own copies.

So the drain costs more than the producer round trip it saves, at least when the
round trip is small. It stays opt-in and should not be the default.

The line it printed — "newest was 1064.8ms old when used" — was **my
instrumentation being wrong**: it reported the age of the newest frame when
`stats()` was *called*, i.e. at the end of the run, about a frame used a second
earlier. Ages are now recorded when a frame is taken, and report mean/max
(`frame age mean 6.0ms max 15.5ms`), with a regression test that takes a frame,
waits 300ms without taking another, and requires the number not to grow. That is
the same class of mistake as round 14's split: a number that looks like a
measurement and is not one.

## Round 17's mechanism does not survive this run

`capture` measured a **14.9ms** capture leg here, with the `wait 0.1ms / read
14.8ms` split saying we are draining a stocked pipe. In round 16 the same
variant, same code, measured **238.1ms** with `wait 225.3ms`.

So the capture leg varies by ~15x between runs and I do not know why. Round 17's
explanation — that the loop was throttling the producer — is not supported by
this run, and the probe pair that suggested it had a changing screen in both
runs, so it never isolated the variable either. What can be said honestly: on
this box the capture leg has been anywhere from 14.9ms to 238ms, and the probe
puts the portal's own rate at ~13ms per 2560x1440 frame. Retracting the
mechanism, keeping the measurement.

## What this run does establish: `send` is resolution-independent

| variant | resolution | send | recv | total |
|---|---|---|---|---|
| pass | 1280x720 | 81.7ms | 10.2ms | 98.3ms |
| capture | 2560x1440 | 87.8ms | 41.6ms | 148.9ms |

**`send` is ~82-88ms at either resolution** — 11.1MB against 44.2MB of traffic,
for the same time. So the worker's intake is not bytes-bound; it is per-frame
work that happens whether the frame is large or small. `recv` does scale (10.2ms
to 41.6ms, roughly the 4x pixel count), which is the readback and the pixels
coming home.

Two consequences, and they change the roadmap:

* **The pipe-bytes arithmetic is not the binding constraint.** 44.2MB at the
  measured 1.1 GB/s predicted a 40ms floor for the pipes alone at 1440p; the
  whole 1440p frame is 148.9ms and its `send` is 87.8ms. The worker is the wall,
  not the wire.
* **Reducing resolution buys much less than it looked like.** 1440p is 1.5x the
  720p cost (148.9ms against 98.3ms), not 4x. The "1440p is catastrophic"
  impression came from the capture leg's variance, which is now gone from this
  run.

The floor to attack is the worker's per-frame cost: **~49ms of `send` with NGX
skipped** (the `bypass` row at 720p), ~82ms with it running. That is inside a
binary we cannot rebuild, which is why the pathway that remains is writing our
own host.

---

# Round 17 — the portal does 75 fps; the loop was throttling it

The probe, twice, 2560x1440, same pipeline, screen verifiably changing:

```
still desktop   grab: first 81.1ms (pipeline start), then 12.8ms/frame = 78.3 fps
video fullscreen grab: first 98.1ms (pipeline start), then 13.4ms/frame = 74.6 fps
```

**The portal hands over 2560x1440 frames every ~13ms — 75-78 fps.** Round 13's
"the capture is the ceiling" was wrong, and wrong by a factor of twenty. The
same pipeline and the same portal measured **238ms per grab inside the M1 loop**
and **13ms per grab with nothing else running**.

Round 16's rate-limited finding was also wrong in its cause. The 225ms `wait`
was not the compositor withholding frames; it was the loop. A screencast whose
client stops consuming stops producing — the queue leaks, buffers are not
recycled, and the pipe is 64KB against a 14.7MB frame — so the producer and the
consumer ping-pong with a full pipeline latency per cycle and the capture leg
absorbs the whole round trip as "waiting for the compositor".

The still-screen suspicion from round 16 is also settled, in the other
direction: both runs reported the screen changing (2.10 and 2.59/255), and the
second one is visibly the video (frame mean 81.6 on the desktop, 20.6 with the
video up). The portal was not idle because the desktop was; it was idle because
we were.

## The fix: keep the producer unthrottled

`minimal/prefetch.py` drains the source on its own thread and leaves the newest
frame waiting, so a frame costs the worker's time instead of the worker's time
plus a producer round trip. Opt-in (`--prefetch`) because the drain itself is a
busy core: 14.7MB at 75fps is memcpy-bound.

Verified against the mock worker, and the capture leg is the evidence:

```
without   timing: capture 12.9ms  send 12.1ms  recv 480.2ms  display 0.5ms
with      timing: capture  2.1ms  send 12.3ms  recv 484.6ms  display 0.6ms
          prefetch: drained 245 frames on its own thread, 244 dropped,
                    newest was 0.5ms old when used
```

245 frames drained while 5 were processed, and the frame actually used was
**0.5ms old**. The capture leg collapses to a lock and a reference, and the
staleness that dropping frames would otherwise cause is reported rather than
hidden — that age is the honest latency the capture adds.

The gate gains `capturepf`, the same capture with the producer kept unthrottled
against `capture`, so the size of the round trip is in one run rather than
across two.

## What this leaves

The capture is not a limit, so the roadmap is now only two things:

* **the ~50ms plumbing floor** with NGX skipped (round 16), and
* **the pass itself**, somewhere between 25ms and 74ms over that floor.

Both are inside the worker, and the 1440p pipe arithmetic still stands — 44.2MB
per frame against a measured 1.1 GB/s is a 40ms floor, so the pipes remain the
structural problem at 1440p whatever the capture does.

---

# Round 16 — the floor with NGX skipped, and the capture is rate-limited

`20260918T083240Z`, all five variants, 1280x720 synthetic except `capture`:

```
pass      capture   9.8ms  send 108.4ms  recv 15.0ms  display 1.3ms  (134.5ms,  6.6 fps)
scaled    capture   7.2ms  send  53.0ms  recv  8.8ms  display 0.7ms  ( 69.6ms, 12.6 fps)
baseline  capture   6.2ms  send  57.5ms  recv 10.1ms  display 0.7ms  ( 74.5ms, 11.9 fps)
bypass    capture   6.1ms  send  47.5ms  recv  6.4ms  display 0.6ms  ( 60.5ms, 14.6 fps)
capture   capture 238.1ms  send  68.2ms  recv 54.4ms  display 4.1ms  (364.8ms,  2.7 fps)
          capture split: wait 225.3ms  read 12.7ms
```

`bypass` and `baseline` both report `mean abs diff 0.0000` — byte-identical,
`the pass returned the input unchanged` — so the worker's NGX-skip does exactly
what the protocol says, and those two rows are honest controls.

## The floor with NGX skipped is 60.5ms

**That is the number worth staring at.** With the network not running at all, a
1280x720 frame still costs 60.5ms. Its pipe traffic is 11.1MB, which at the
measured 1.1 GB/s is ~10ms. Capture is 6.1ms and display 0.6ms.

So roughly **50ms per frame is spent in the worker's plumbing** — the texture
upload, readback and copies — with no network involved. That is the largest
single unexplained cost in the project, and it is roughly half the frame at full
strength.

## Which corrects something I said earlier

I claimed the network was cheap and the bytes were the story. `baseline` and
`bypass` disagree: zeroing the strengths costs 14ms over skipping NGX, so simply
*running* the network costs ~10-14ms per frame at 720p, against the upstream's
`1.5ms + 1.51ms/Mpixel` arithmetic of ~2.9ms on a 5070 Ti. And the effect at
full strength costs 74ms over `bypass` in this run — though `pass` came in at
134.5ms here against 82-85ms in three earlier runs, so this run is ~1.6x slow
across the board and that 74ms should not be trusted on its own. What is
consistent is the ordering: bypass < baseline ≈ scaled < pass.

**Run-to-run variance is now large enough to matter.** Only comparisons within
one run are safe, and the gate prints the whole table for that reason.

Also consistent with earlier runs: `scaled` (network at 640x360) sits within
5ms of `baseline` (network at 1280x720, zero strength), so the network's own
resolution barely matters — the cost is fixed, not per-pixel. That is the
upstream's point about `work_scale` restated from the other side.

## The capture is rate-limited, not bandwidth-limited

```
capture split: wait 225.3ms  read 12.7ms
```

Read is 12.7ms, near the ~19ms it costs to drain a stocked 14.7MB pipe, so our
copy is efficient and is **5% of the grab**. The other 225ms is the producer:
frames arrive about every 238ms, i.e. ~4 fps. This is a cadence problem, not a
throughput one — which is a different repair from the one I was expecting.

## But it is probably an artefact of a still screen

A compositor renders on damage. On a desktop where nothing is changing, it may
produce almost no new frames, and a screencast fed from the compositor inherits
that: few damage events, few frames. These runs capture a static desktop — the
MVP is headless, so the test itself changes nothing on screen.

If that is what is happening, the ~4 fps says nothing about the case that
matters. A game is constant damage, and the portal would be delivering far more.
It would also mean the "the capture is the ceiling" conclusion is wrong for a
moving picture, and the whole roadmap changes: the capture stops being the
blocker and the ~50ms plumbing floor becomes the thing to attack.

That is testable in a minute and needs no code: run the same probe with
something moving on screen. If `wait` collapses to tens of milliseconds, the
portal was never the problem; if it stays at 225ms with a video playing
fullscreen, the capture really is capped and everything above stands.

---

# Round 15 — two controls added, and the arithmetic they test

No results yet (the box is unavailable), so this is only what the next run will
say and why it is worth a run.

## `--bypass`, and a `bypass` gate variant

`FRAME_FLAG_BYPASS` already existed in the protocol — *"NR OFF: skip NGX, show
the raw capture"* — and the MVP never sent it. It now does, with a variant in the
gate to pair it against `baseline`.

That pairing is the point. `baseline` zeroes the strengths, and zeroed strengths
may still run the network end to end; `bypass` skips NGX outright. So:

```
baseline - bypass   what the network actually costs
bypass              the texture upload, readback and copies, which no strength
                    setting touches
```

At 1280x720 that matters because the numbers do not add up yet. The frame is
57.7ms with the effect off; the pipe traffic is 11.1MB against a measured
1.1 GB/s, so ~10ms; the product's own figure for the network is ~2.9ms. Roughly
**48ms of 57.7ms is unaccounted for**, and it is either the network costing far
more than its arithmetic or the texture path — which are completely different
repairs. One extra row settles which.

## `--source window`

The portal's `SelectSources` gets `SOURCE_WINDOW` instead of `SOURCE_MONITOR`,
so the compositor hands over one window rather than a whole screen. Two reasons
it is the interesting path:

* **The capture is priced per pixel**, and the capture is the ceiling at
  2560x1440 (125-325ms per grab). Fewer pixels is the one lever that acts on the
  leg actually limiting the pipeline — not because the pass upscales, which the
  upstream source says plainly it does not, but because the compositor bills by
  area.
* **It is the GeForce Now case.** A game stream needs the game window; the
  desktop around it is never watched.

Two limits are documented on the class rather than hidden: a window resized
after it is picked is scaled back to the picked dimensions, because our pipeline
forces those exact caps; and on a fractionally-scaled display the portal may
report logical dimensions while streaming pixels, in which case `grab` says the
sizes disagree instead of returning a mangled frame.

## The ceiling to keep in mind while reading the next run

Per frame the pipe path moves colour + motion + result. At 1440p that is 44.2MB
against a measured 1.1 GB/s pipe:

| resolution | per frame | floor | ceiling if everything else were free |
|---|---|---|---|
| 2560x1440 | 44.2 MB | 40ms | ~25 fps |
| 1280x720  | 11.1 MB | 10ms | ~100 fps |

So 1440p cannot be served by this architecture whatever the network costs, and
720p's problem is not the pipes. That is the shape of the work: keep the frame
out of the pipes at 1440p, and find the ~48ms at 720p.

---

# Round 14 — the split was measuring nothing, the copy is 11% of the grab

`20260916T204919Z` reported:

```
capture   capture 125.1ms  send 71.6ms  recv 43.5ms  display 4.0ms  (244.3ms/frame, 4.1 fps)
capture split: wait 125.1ms  read 0.0ms
```

**`read 0.0ms` is the tell, and it means the split was worthless.** A buffered
`read(n)` blocks until it has all n bytes, so one call swallows the entire
transfer and everything lands in `wait` regardless of who is slow. The number
looked like a measurement and was not one.

Fixed by reading with `read1`, which returns as soon as data is available, and
verified by driving the real read path from two real producers:

```
pipe stocked (producer ahead of us)    wait 0.1ms   read  18.9ms
producer dribbling, ~120ms per frame   wait 0.1ms   read 159.1ms
```

So the discriminator is **`read`**: ~19ms at 2560x1440 means we are draining a
stocked pipe at memory speed, and far above that means the bytes arrived slowly.
A test pins both cases, because without one the broken version passed for a
measurement.

## Which says the compositor is the limit

The split was fixed after the run, so it has not yet been reported from the box.
But the answer is already available from a benchmark that does not need the box:
copying a 14.7MB frame out of a stocked pipe costs **13-19ms** here (1108 MB/s),
which is ~11% of the 125ms grab.

The rest of the argument is backpressure, and it is the part that settles it. If
the portal were producing at 60fps while we consumed at 4, the leaky queue would
keep the pipe stocked and the grab would cost about what a stocked pipe costs —
15-20ms. It costs 125ms. For that to be our copy, our copy would have to be
running at 118 MB/s, which is a tenth of what the same code does on the same box
with a stocked pipe.

So the portal path delivers roughly **3-8 fps at 2560x1440** — 325ms per frame in
the run before, 125ms in this one, with no code change between them, so the rate
varies too. The pass cannot run faster than frames arrive, and neither can
anything else.

That makes the capture the blocker for the GeForce Now target, outranking
everything established about the pass so far. It also gives the user's original
instinct — capture a smaller window — a reason to be right that neither of us
had: the compositor's cost scales with the frame size, so capturing only the game
window instead of a 2560x1440 desktop would raise the ceiling roughly in
proportion to the pixels removed. Not because the pass upscales, which it does
not, but because the capture is the bottleneck and it is priced per pixel.

## And the push failure was the terminal, not GitHub

`--push` runs `git push` from a script, which has no TTY. A credential helper
that prompts works from the shell and cannot work there, which surfaces as
"wrong credentials". `run_tests.sh` now honours `NS_GIT_ASKPASS` (defaulting to
`~/.neuralscreen/github-askpass.sh`) and says so when the script is missing,
instead of leaving the failure looking like GitHub's fault.

---

# Round 13 — work scale pays, MOTS does not, and the capture is the ceiling

`20260916T190758Z`. The first run with both new variants:

```
pass      capture   5.2ms  send 67.6ms  recv  8.7ms  display 0.5ms  ( 82.0ms/frame, 12.2 fps)
scaled    capture   5.0ms  send 45.1ms  recv  7.0ms  display 0.5ms  ( 57.6ms/frame, 17.4 fps)
baseline  capture   5.1ms  send 43.8ms  recv  8.4ms  display 0.5ms  ( 57.9ms/frame, 17.3 fps)
capture   capture 375.0ms  send 86.3ms  recv 56.1ms  display 2.7ms  (520.0ms/frame,  1.9 fps)
mots      did not run — the worker went silent for 60s on frame 0
```

## work scale does pay — and my prediction was wrong

I expected `scaled` to be flat, on the grounds that the network is cheap and the
bytes dominate. It is 30% faster: 82.0ms → 57.6ms, 12.2 → 17.4 fps.

But it does not isolate what I wanted, because `--work-scale 0.5` changes **two**
things at once. The network works at 640x360 instead of 1280x720, and the motion
field travels at the work resolution, so it shrinks from 3.7 MB to 0.92 MB.
The frame's inbound bytes drop from 7.4 MB to 4.6 MB, and its `send` drops from
67.6ms to 45.1ms — in proportion, 62% of the bytes for 67% of the time. So the
result is consistent with the bytes being the cost, and does not separate them
from the network.

The cleanest evidence for the split is `baseline`: the effect dialled to zero
with the *same bytes* as `pass`, and it lands at 57.9ms — within 0.3ms of
`scaled`. Turning the effect off and quartering the network's work are worth the
same ~24ms. That is what a cost spread across the worker's per-frame work *and*
the bytes looks like, and it is why neither lever alone is dramatic.

## MOTS is closed, not pending

```
TimeoutError: the worker has been silent for 60s on frame 0
```

The worker never answered frame 0 with a 320x180 motion field. The protocol
documents MOTS as part of the upstream's guides path, which takes its flow size
and its luminance from the worker's own capture (DDA and the gray reverse
channel). A bare small field arriving through the pipe path is not something the
worker accepts — it waits for bytes that never come. The flag stays for the wire
format and its tests, and the gate no longer runs it: a variant that hangs for
60s and then reports FAIL is worse than no variant.

So the bytes lever is unavailable in this mode. Which leaves the one the
measurement actually points at.

## The capture is now the ceiling at 2560x1440

`capture` runs at 1.9 fps and **375ms of its 520ms frame is the portal grab
itself** — before the worker sees anything. The four synthetic variants grab in
~5ms, so this is not a per-pixel cost: it is the portal and GStreamer path.

That matters more than anything else here, because it is exactly the leg the
GeForce Now target depends on. The pass cannot run faster than frames arrive,
and at 1.9 fps the enhancement is moot.

`tools/wayland_probe.py` now reads 12 frames by default and reports the rate the
compositor actually delivers, with no Wine and no worker in the way. That is the
next measurement: if the probe says ~2 fps at 2560x1440, the compositor's
screencast is the ceiling and everything downstream is wasted effort until it is
understood; if it says 60 fps, then our pipeline in front of the grab is the
problem and the reader is where to look.

The probe was not in the `20260916T194046Z` report, so rather than ask for a
second run the MVP now answers the same question inside the ordinary one. Each
grab is timed in two halves — `last_wait`, until the frame's first bytes arrive
from the compositor, and `last_read`, the rest of the copy — and every run
prints:

```
capture split: wait 312.0ms  read 13.5ms   (wait = the frame arriving, read = our copy)
```

Three readings, three different fixes: a large **wait** is the compositor's rate
and the fix is not in this repo; a large **read** is our copy out of the pipe and
is squarely ours; and a **wait near zero** means the producer is ahead of us, so
the capture leg was measuring our loop's pace all along and the 325ms is really
the worker's. Both halves are excluded from the frame total, since they are the
same milliseconds as the capture stage.

---

# Round 12 — the network is not the bottleneck; the bytes are

`20260916T175431Z`, the first run with the per-stage breakdown, and it contradicts
what the fps alone suggested:

```
pass      capture 5.2ms  send 66.9ms  recv  8.7ms  display 0.5ms   (81.3ms/frame, 12.3 fps)
baseline  capture 5.2ms  send 42.8ms  recv  8.6ms  display 0.5ms   (57.1ms/frame, 17.5 fps)
scaled    not implemented at the time (--work-scale lands in the next commit)
```

**`recv` is 8.7ms.** That leg is the worker: it receives the frame, runs the
network, reads the result back and sends it. The upstream host's own measured
figure for the network is `1.50 ms fixed + 1.51 ms per megapixel` on a 5070 Ti,
which at 1280x720 (0.92 MP) is **~2.9ms**. So the worker and the pass together cost
about 9ms, and the neural pass is a small part of that.

Nothing else in the row accounts for the other 72ms either: capture is 5.2ms and
the display upload is 0.5ms.

What is left is **7.4 MB of frame going one way and 3.7 MB coming back**, every
frame, through two pipes — 11.1 MB per frame, which at 81ms/frame is 137 MB/s.

One honest caveat on the split. `send` is our own write, but a pipe write blocks
while the worker is not draining, so `send` also absorbs any of the worker's work
that does not overlap with it. Its 67ms is therefore not purely our bytes. What
the split does establish is the negative result, which is the useful part: the
capture, the display and the network together are 14.4ms of an 81ms frame. The
remaining ~67ms is the frame's bytes and the worker's per-frame overhead, and
neither shrinks when the network's resolution shrinks.

That is what round 10's plan assumed it would. `--work-scale` existed on the
grounds that a smaller work resolution means a faster pass; the product's own
source says the opposite of what "upscaling" mode implies, so the gate now
carries a `scaled` variant to test it rather than argue it.

It also gives the one lever that does attack the bytes, and it was hiding in
plain sight: the motion field. `pass` sends it at the work resolution —
1280x720x2x2 bytes = **3.7 MB, half of everything sent** — and ours is entirely
zeros, because the MVP has no real motion vectors and a video stream cannot
supply them. `FRAME_FLAG_MOTION_SMALL` (MOTS) sends the field at the optical-flow
size (320x180) and the worker upscales it on the GPU, which takes the same zeros
down to 0.23 MB and the frame's inbound bytes from 7.4 MB to 3.9 MB — 47% less,
with nothing changed about what the network is handed.

`--motion-small` and a `mots` gate variant implement and test that.

## Also this round

The `capture` variant failed, and not for an interesting reason:

```
startup failed: the portal handshake failed (TimeoutError):
  CreateSession / SelectSources / Start  (the compositor will ask you to choose a screen)
```

The handshake waits 120s at `Start` for the user to pick a screen and press
Share. It timed out, so either the dialog went unanswered or a stale ScreenCast
session was still open (KDE allows one at a time). Not a code fault this round —
but the timeout is a human's speed, not a machine's, so it wants raising before
it becomes one.

---

# Round 11 — the control answers it: the floor is exactly zero

`20260916T155332Z`. Round 10 could not say whether the 4.55/255 was the network
or the trip through Wine. It is the network, and the control proves it:

```
variant: baseline   --param intensity=0 --param local_tone=0 --param local_structure=0
  ✓ before.png written (92K)   ✓ after.png written (92K)
  VERDICT the pass returned the input unchanged (mean abs diff 0.0000/255, PSNR inf)
```

Not "small" — **byte-identical**:

```
33184b06882216bde54b58c54702828bdca6ebdcf0c1689edecd7244b31eb99e  before.png
33184b06882216bde54b58c54702828bdca6ebdcf0c1689edecd7244b31eb99e  after.png
  max abs difference 0.0    pixels differing at all: 0
```

So a frame can go out to Wine, through vkd3d-proton and NGX, and back with
nothing altered. The transport contributes nothing, there is no floor to
subtract, and every number in round 10 is attributable to the network:

| variant | mean abs diff | attributable to |
|---|---|---|
| `pass` (synthetic card) | 17.6189 | the network, entirely |
| `capture` (real screen) | 4.4313 | the network, entirely |
| `baseline` (effect off) | **0.0000** | — |

On the real screen the pass touches **100% of pixels**, mean 4.43/255, max 75.

## Two things this buys

**A verified bypass.** `intensity=0 local_tone=0 local_structure=0` is a
byte-exact passthrough, not an approximation of one. That is a usable product
feature — a way to switch the effect off without restarting or unloading
anything — and M1 now re-proves passthrough integrity on every run, so a future
regression in the transport would surface as the baseline ceasing to be zero.

**The effect is content-dependent, so the number is not a constant.** 4.55 in
round 10, 4.43 here: the same pass on a different desktop frame. Read the figure
as "how much this screen was changed", not as a property of the pass.

## Still open

- **3.31 fps** (22s for 30 frames on this run). Correct loop, not yet fast.
- Whether 38/255 on text is the right strength now that it is tunable.
- Everything else in the MVP: the pass is the only thing wired up so far.

---

# Round 10 — the MVP runs end to end on the real screen (kept)

`20260916T152209Z`. Both variants passed, and this is the first run where the
whole loop worked on a live desktop:

```
variant: capture   (--source auto)
  pipeline: gst-launch-1.0 -q pipewiresrc fd=5 path=188 ! videoconvert
            ! videoscale ! video/x-raw,format=RGBA,width=2560,height=1440
            ! queue max-size-buffers=1 leaky=downstream ! fdsink fd=1
  ✓ before.png written (1.3M)   ✓ after.png written (2.5M)
  VERDICT the pass changed the frame (mean abs diff 4.5459/255)
frames: 30 done, 0 skipped, 9.073s (3.31 fps), worker exit 0
RESULT: PASS — capture -> DLSS5 NR pass -> display works.
```

Capture through the portal, 30 frames, **no skips**, at 2560x1440.

## What the pass does to a real desktop

| variant | source | mean abs diff | p99 | PSNR |
|---|---|---|---|---|
| `pass` | synthetic test card | **17.6189** | 44.00 | 21.98 dB |
| `capture` | the real screen | **4.5459** | 39.00 | 30.68 dB |

The same pass, ten times more visible on the test card than on the desktop. That
is not a contradiction: the card is nothing but structure and gradients, while
the captured screen is 95% near-black background and flat UI. An effect that
scales with content shows up where the content is.

Broken down by how bright the input pixel was:

| input luminance | share of pixels | mean change |
|---|---|---|
| dark (background, terminal) | 95.0% | 3.62 |
| mid (window chrome, panels) | 3.5% | 14.79 |
| bright (text, whites) | 1.6% | **38.35** |

So it works hardest on text. Visually it survives that: read at 1:1 the glyphs in
`after.png` are as crisp as in `before.png`, and a 12x-amplified difference map
is a smooth wash across the whole frame — brightest over the wallpaper's detail
and the window chrome — rather than a halo around letterforms. Only 1.1% of
pixels are byte-identical, 25.7% move by more than 4/255, and the maximum
anywhere is 63/255.

Both PNGs are opaque RGBA (alpha 255 throughout), so nothing was flattened on
the way out this time — `_save_rgba` was always correct; it was the probe's
writer that was not.

## What this does *not* establish: the control

4.5459/255 is a real, structured change, but a diff cannot say who made it.
Every frame travels to Wine as a texture and back, so some of it could be the
round trip rather than the network — and the synthetic variant cannot separate
them either, because it goes through the same transport.

So the effect can now be dialled to zero without editing code:

```
--param intensity=0 --param local_tone=0 --param local_structure=0
```

and `m1_pipeline_gate.sh` runs that as a third variant, `baseline`: same source,
same worker, effect off. Whatever still changes is the floor, and the report
treats it as a measurement rather than a pass/fail. Subtract it before reading
the effect variants as the network's work.

`--param` is also the tuning dial for the text result above. It validates names
against the defaults, so a typo fails at the CLI with the real names rather than
being silently dropped by a worker that never sees it.

## Also worth recording

**3.31 fps.** 30 frames at 2560x1440 in 9.07s. The loop is correct; it is not yet
fast. That is the practical gap between this and "the DLSS5 pass on your whole
desktop", and it is now measurable rather than theoretical.

---

# Round 9 — the Wayland capture backend (portal + PipeWire) (kept)

Target: KDE Plasma on Wayland. Approach chosen deliberately over shelling out to
a screenshot tool per frame — the portal is one implementation for every
compositor, and it prompts the user once rather than once per frame.

## The spec detail that would have cost a round

The PipeWire file descriptor **does not come from `Start`**. It is its own call:

```xml
<method name="OpenPipeWireRemote">
  <arg type="o" name="session_handle" direction="in"/>
  <arg type="a{sv}" name="options" direction="in"/>
  <arg type="h" name="fd" direction="out"/>
</method>
```

A client that waits for the fd on the Start response waits forever. Read from
`data/org.freedesktop.portal.ScreenCast.xml` rather than inferred, because both
arrangements look equally plausible from the outside.

Second detail: since interface **version 6**, the node id in the `streams` tuple
is deprecated for targeting — node ids are reused after destruction, so a
hotplug or a resolution change can make a stale id point at another stream.
`pipewire-serial` with `target-object` is the supported way, and the node id is
only a fallback for older backends. `ScreenCast.pipewire_target` prefers the
serial and the probe reports the interface version so the choice is visible.

## Choices worth naming

| | chose | over | why |
|---|---|---|---|
| D-Bus | `jeepney` | `dbus-python` | pure Python; `dbus-python` needs libdbus headers to build |
| PipeWire | `gst-launch-1.0` subprocess | PyGObject + `pipewiresrc` | avoids needing gobject-introspection built; the pipeline is visible in `ps` while it runs |

The protocol needs to *receive* a file descriptor, which rules out most
lightweight D-Bus clients. jeepney decodes an `h` out-argument into a
`FileDescriptor` with `to_raw_fd()`, and `open_dbus_connection(enable_fds=True)`
is required to get it at all. Also worth recording: jeepney's `filter()` only
registers locally and does **not** send `AddMatch` — without sending it
explicitly, no signal is ever delivered.

## `tools/wayland_probe.py` — the iteration device

The lesson from rounds 7 and 8 is that capture and the pass must be separable.
The probe needs no Wine, no GPU and no worker: it walks the session,
dependencies, GStreamer, the portal, the handshake and then reads real frames,
reporting per-channel standard deviation and optionally writing one out.

Each step prints before it acts, so a failure names itself — and the same
standard-deviation check that caught two black frames in round 7 is the last
thing it does. Verified here against a machine with no bus and no GStreamer: it
reports all three problems with the correct package names rather than raising.

## One bug found while testing

`PortalCapture.close()` closes the fd it was handed. The first version of the
test helper passed a made-up number, and the close took out an unrelated
descriptor owned by pytest — a real failure, not a flake. The helper now opens a
devnull descriptor, so the test closes something it actually owns.

## Confidence

- The handshake, the fd source and the targeting rule: **verified against the
  portal's own interface definition**, not from memory.
- The pipeline string, the options encoding, the response parsing and the fd
  ownership: **verified** — 25 new tests, no display needed.
- That the screen appears, and that frames arrive non-black: **not established.**
  No session bus and no compositor exist on the analysis box. That is what
  `tools/wayland_probe.py` is for; it is the first thing to run.

---

# Round 8 — the pass works. Verified, and the first number was 3x too big. (kept)

`20260916T101147Z` ran M1 with both variants. The gate said:

```
 variant: pass   (--source synthetic)     exit code: 0
  ✓ before.png written (88K)   ✓ after.png written (560K)
  VERDICT the pass changed the frame (mean abs diff 48.6669/255)
 variant: capture (--source screen)       exit code: 0
  VERDICT the output is blank
  ✗ the INPUT frame was blank — the pass had nothing to act on
 M1 summary
  pass     PASS
  capture  FAIL
```

So the `pass` variant passes and the `capture` variant still fails for the
Wayland reason from round 7 — which is now a clean separation rather than one
ambiguous result. 30 frames, 0 skipped, 14.71 fps, worker exit 0.

## But 48.67/255 was not the pass

That is far too large for a neural pass, so the frames were checked directly
rather than trusted. `before.png` is the test card exactly. `after.png` is the
same card with its white bar at a **different column**: 0-159 versus 203-362.

203 is `29 * 7` — the test card's bar advances 7px per grab, and the pair being
compared was frame 0's input against frame 29's output. **The comparison was
measuring the bar moving, not the pass.** The pipeline kept `first_before` and
`last_after`; nothing said those had to be the same frame.

The gradient is time-independent, so comparing each frame against the *known*
card isolates the pass with no reliance on the pipeline at all (both bar regions
excluded, 1120 of 1280 columns):

| frame | vs the known test card |
|---|---|
| `before` | mean **0.50**, max 1.0 — it is the card (1/255 is G's 127.5 rounding) |
| `after` | mean **15.89**, p99 41.65, max 51.6 |

`before` vs `after` on those columns: mean 15.78, PSNR 22.72 dB. The G channel,
which is constant along every row in the input, comes back varying by up to 42.9.
The bar, pure 255 in the input, returns at 233.9.

**The pass is genuinely transforming the frame.** Mean 15.8/255 is a real render,
not a rounding artefact — but it is 6.2% of full scale, which is a strong look,
and the params (intensity, local tone, structure, style) are worth revisiting
once this loop is doing it live on a real screen.

## Fixed

`minimal/loop.py` now keeps `pair_before` from the same iteration as
`last_after`. `tests/test_pipeline_mock.py::test_saved_pair_comes_from_the_same_iteration`
pins it: with the old logic it fails, with the fix it passes (checked by
reverting `loop.py` alone and re-running).

## Confidence

- The NR pass runs through the live path under Wine and changes the frame:
  **verified.** The measurement does not depend on the pipeline's own bookkeeping
  — it compares the output against a test card that is known by construction.
- It was previously reported as 3x larger than it is: **was wrong, now corrected.**
- The capture variant failing on Wayland: unchanged from round 7.
- M0's `--test` evaluate failure (`0xBAD00004`): still a proxy artefact
  (round 6), and now demonstrably not a blocker — the live path it predicted
  would behave differently does.

---

# Round 7 — the frame was empty, and M1 was measuring capture, not the pass (kept)

`20260916T080456Z` ran the M1 gate for the first time. It reported:

```
✓ the MVP exited 0
✓ before.png written (16K)     ✓ after.png written (284K)
size              2560x1440
mean abs diff     0.0095
after == before   False
after is blank    True
✗ the output is blank — the pass ran and produced nothing
```

The user's own read was better than the gate's: *"the before and after are
different, but empty in different ways."* Looking at both frames confirms it —
both are black.

The environment block explains it:

```
DISPLAY:            :0
WAYLAND_DISPLAY:    wayland-0
XDG_SESSION_TYPE:   wayland
```

**`minimal/capture.py` is X11-only.** Its own docstring says so: *"Deliberately
one backend. PipeWire/Wayland is a later milestone; mss on X11..."*. On a Wayland
desktop the XWayland root window is black by definition — applications draw on
the compositor, not there — so `mss` returns an empty frame every time.

So this run said **nothing about the neural pass**. The pass had nothing to act
on. "NGX is broken" and "we are feeding it black" produce identical evidence, and
M1 ran only the screen variant, so it could not tell them apart. That is a design
bug in the gate, not just an unlucky run.

## The fix: separate the two questions

**`--source synthetic` and `--source image`** (`minimal/capture.py`). Both
implement the same interface as `Capture` (`resolution`, `grab()`, `close()`), so
nothing downstream changed. `synthetic` is a test card with a red ramp, a green
ramp, interference stripes and a bar that moves each grab — structural content in
all three channels, so a pass has something to have an opinion about.
`image` replays a real screenshot, which is the practical way to get real pixels
into the pipeline on Wayland today:

```
grim /tmp/shot.png
python -m minimal --source image --input-image /tmp/shot.png
```

**M1 now runs two variants and reports both:**

| variant | source | question |
|---|---|---|
| `pass` | `--source synthetic` | does the NR pass change a known frame? |
| `capture` | `--source screen` | does a real screen frame come through? |

The verdict is driven by `tools/frame_diff.py`, which is separately runnable and
returns 0/1/3 so the judgement lives in one place. It now reports `before is
blank` as well as `after is blank` — the gate could previously only see the
output, which is precisely why an empty input was invisible.

Verified against the real failing pair before landing, and it reproduces the same
numbers (`mean abs diff 0.0095`, `PSNR 68.34`) while flagging both frames blank.

## Two smaller corrections

- **The worker writes no log in `--live` mode.** Line 130 of
  `dlss5-feed-host64.cpp` is `if (!g_video_mode && fopen_s(...))` — logging is
  deliberately off in video mode. M1's *"no dlss5-feed-host.log"* warning was
  noise, and is now a note.
- **11 new tests** (`tests/test_capture_sources.py`) covering the new sources.
  They deliberately do **not** use the `xvfb_display` fixture: the point of these
  sources is that they need no display at all, so a test that gave them one would
  hide the property being bought.

## Confidence

- Capture returns black because the session is Wayland and the backend is X11:
  **verified** — both frames are black, the environment says Wayland, and the
  capture docstring states the single-backend decision.
- Whether the neural pass works: **still unknown, and this round did not change
  that.** The `pass` variant is what answers it.

---

# Round 6 — the two paths are not the same path (kept)

Both variants ran in one report (`20260916T074715Z`). The result refutes the
easy form of the round-5 hypothesis and confirms the important part of it:

| variant | create | evaluate |
|---|---|---|
| direct | ✓ `[pure] direct feature 18 ready ... result=0x00000001` | ✗ `0xBAD00004` |
| via-core | ✗ `0xBAD0000B UnableToInitializeFeature` | never reached |

`NS_NGX_VIA_CORE=1` is **not a fix** — it fails one step earlier. And that is the
informative part:

- **NGX Core cannot create feature 18 under Wine at all** (`0xBAD0000B`), while
  the NR runtime can.
- So `FAIL_FeatureNotFound` from the Core is exactly what you would expect. The
  Core is the piece that does not know the handle, and it does not know it
  because it never had it. Nothing here says the pass itself is broken.

## The finding that matters: `--test` is not the product path

Reading `dlss5-feed-host64.cpp` against the two call sites shows the M0 gate has
been measuring a path the product does not use:

| | create | evaluate |
|---|---|---|
| `--test` (`RunTest` → `Evaluate`) | `g_nr_create` — NR runtime | SDK macro `NGX_D3D12_EVALUATE_DLSS_EXT` → `NVSDK_NGX_D3D12_EvaluateFeature_C` — **NGX Core**, with the DLSS-SR `NVSDK_NGX_D3D12_DLSS_Eval_Params` |
| `EvaluateVideo` (`--live`, what the MVP drives) | `g_nr_create` — NR runtime | `g_nr_evaluate` — **NR runtime**, with the `DLSSNR.*` parameter set and `nullptr` eval params |

`--test` registers a feature with one runtime and evaluates it through another.
The live path uses one runtime for both. The MVP launches
`wine nvngx.dll --live`, so `python -m minimal` exercises `EvaluateVideo`.

That makes the M0 `--test` evaluate failure a **proxy artifact**. It does not
follow that the live path works — only that M0 cannot settle it. The gate's
"PASS = 250/300 evaluates" criterion was testing a harness, not the deliverable.

## Why not just fix `--test`

Because the worker cannot be rebuilt from this repo:
`native/dlss5-feed-host64.cpp` includes `spout_bridge.h` and `../src/feed_ipc.h`,
and **neither is present**. There is no Makefile, CMakeLists or project file, and
no cross-compiler on the analysis box. `native/nvngx.dll` is a prebuilt binary
(156K, "built Sep 11 2026 17:26:14"). Chasing the `--test` path would mean
reconstructing a Windows build for a synthetic harness that is not the product.

## So: M1

`tools/m1_pipeline_gate.sh` runs the actual MVP end to end and asks the only
question that matters — **did the frame come out changed?**

```
python -m minimal --frames 30 --headless --save-before before.png --save-after after.png
```

then measures the pair. A no-op pass exits 0 and looks perfectly healthy, so the
gate fails on: output byte-identical to input, output blank, or mean absolute
difference below 0.05/255. Verified against four synthetic pairs (identical,
blank, sub-threshold, real change) before landing — the identical and blank cases
must FAIL, and do.

`run_tests.sh --report --m0 --m1 --push` runs everything in one round-trip.

## Confidence

- NGX Core cannot create feature 18 under Wine: **verified** — `0xBAD0000B` from
  the via-core variant, reproducible.
- `--test` and the live path use different evaluate APIs: **verified** by
  reading both call sites in the source.
- That the live path therefore works: **not established.** It is the next thing
  measured, and it may well fail the same way. The difference is that its
  failure would be a real answer about the port rather than about a probe.

## Also fixed

The consistency test parametrised on whole script bodies, so pytest built each
test ID out of an entire shell script and every report's summary line contained
the contents of every script. Given a readable `ids=`, the summary line is a
summary again.

---

# Round 5 — M0 answers YES, and the failure moves to evaluate (kept)

The DXVK fix landed and it was the unlock. From `20260916T065756Z`:

```
✓ wine: wine-11.17 (Staging)          ✓ GPU: RTX 4080 SUPER, 615.71.09, cc 8.9
✓ installed DXVK dxgi.dll (5.2M)      ✓ installed vkd3d-proton d3d12core.dll (5.7M)
     after: DXVK v3.1.1 / vkd3d-proton 3.0.1 / dxvk-nvapi v0.9.2

info:nvapi64:DXVK-NVAPI v0.9.2 NVAPI gcc 16.1.0 x86_64 release (nvngx.dll)
info:nvapi64:NvAPI Device: NVIDIA GeForce RTX 4080 SUPER (615.71.9)
info:nvapi64:<-NvAPI_Initialize: OK
[host] NVSDK_NGX_D3D12_Init -> 0x00000001 (Success)
[pure] direct DLSSNR Init_Ext -> 0x00000001 (Success)
[pure] direct feature 18 ready: 640x360 preset=0 result=0x00000001
[host] evaluate failed 0xBAD00004 (?)
[host] --test finished: 0/300 evaluates succeeded
```

**The make-or-break question is answered: NGX initialises under Wine, and feature
18 is created.** Every previous round failed at or before init. This is the first
run that got past it, and `0xBAD00002` is gone.

## The new failure: 0xBAD00004 FAIL_FeatureNotFound

The host's own `NgxResultName` table has no case for it, hence the `(?)`. NVIDIA's
header settles it (`NVIDIA/DLSS`, `include/nvsdk_ngx_defs.h`):

```
NVSDK_NGX_Result_FAIL_FeatureNotFound = NVSDK_NGX_Result_Fail | 4,   // 0xBAD00004
```

"Feature not found" for a feature that was created successfully two lines earlier
is worth reading closely, because **create and evaluate do not go to the same
place**:

| step | symbol | comes from |
|---|---|---|
| create | `g_nr_create` | `GetProcAddress(nvngx_dlssnr.dll, "NVSDK_NGX_D3D12_CreateFeature")` |
| evaluate | `NVSDK_NGX_D3D12_EvaluateFeature_C` | the SDK helper's Core entry point |

`NGX_D3D12_EVALUATE_DLSS_EXT` is a `static inline` in the SDK's
`nvsdk_ngx_helpers_d3d.h`: it packs the eval params into the parameter block and
its last line is a call to `NVSDK_NGX_D3D12_EvaluateFeature_C` — the **Core**
entry, not the NR runtime's. So the handle is registered with one runtime and
evaluated by the other, and the Core does not know it.

This also explains the one loose end from round 1: the host's import table has
**no NGX symbols at all** (`objdump -p native/nvngx.dll` — 25 DLLs, none of them
NGX). Every NGX entry point is resolved by name at runtime, which is why
`NVSDK_NGX_D3D12_*` shows up as string literals in the binary.

## The experiment

`NS_NGX_VIA_CORE=1` is upstream's own switch (see the comment above the
`NS_NGX_VIA_CORE` block in `dlss5-feed-host64.cpp`): it routes create *and*
evaluate through NGX Core. If the mismatch above is the whole story, via-core
should get past evaluate — and it also tests upstream's stated goal of dropping
the "the process must be named nvngx.dll" constraint.

So the gate now takes `--via-core`, and `run_tests.sh --report --m0` runs **both
variants in one report**:

| artifact | variant |
|---|---|
| `raw/m0_gate.txt` | direct (default) |
| `raw/m0_gate_via_core.txt` | `NS_NGX_VIA_CORE=1` |
| `raw/via-core/` | that variant's own env + worker log |

Both exit codes are printed in the run's stdout.

## Confidence

Init and feature creation are **verified**, not inferred: both report
`0x00000001 (Success)` with the GPU named by NVAPI. The evaluate diagnosis is
**inferred** from the two call sites and confirmed against NVIDIA's header for
the result code; the variant run is what will settle it.

If via-core also fails at evaluate, the next suspects are the `[arch] patch`
(`architecture 0x190 (spoofed to the DLL's accepted value)` — the host already
patches NGX's view of the GPU, which is a strong smell) and the eval params
struct: `Evaluate()` fills `NVSDK_NGX_D3D12_DLSS_Eval_Params`, which is the
super-resolution shape, for what is feature 18.

## Also fixed this round

`run_tests.sh` copied `native/dlss5-feed-host.log` into `raw/` **before** the
gate produced it, so every report listed the worker log as an artifact it did
not carry. It is now copied after the gate, for both variants.

---

# Round 4 — presence is not provenance (kept)

The round-3 fix worked (the setup applied: `copied nvngx.dll -> system32`,
`4/4 registry values written`), but `0xBAD00002` did not move. The setup said:

```
✓ dxgi.dll present (248K)      ✓ d3d11.dll present (460K)
✓ d3d12core.dll present (52K)  ✓ DXVK dxgi.dll + d3d11.dll already present
```

…and dxvk-nvapi still said *"Querying Vulkan entry point from DXGI factory
failed, please ensure that DXVK's dxgi.dll (version 2.1 or newer) is present"*.

Both statements were true. There **was** a `dxgi.dll` in `system32` — it was
just **not DXVK's**. Downloading the pinned releases settles it:

| file | the pinned release | what was in the prefix |
|---|---|---|
| DXVK `dxgi.dll` | 5,414,926 B (5.4 MB) | 248K |
| DXVK `d3d11.dll` | 7,483,406 B (7.4 MB) | 460K |
| vkd3d-proton `d3d12core.dll` | 5,963,790 B (5.9 MB) | 52K |
| dxvk-nvapi `nvapi64.dll` | 2.0 MB | 2.0 MB ✓ |

Those are Wine's builtins. The check was `[ -s "$SYS32/$f" ]` — file exists,
therefore fine — so the installer skipped the very files it existed to install.
Same class of mistake as round 3 (a diagnostic that could not see what it was
looking for), one layer down.

## The fix: identify the layers, don't just find them

Each layer is now identified by markers taken from the real binaries, verified
against them before landing:

| layer | marker | version |
|---|---|---|
| DXVK | `strings dxgi.dll \| grep DXVK` — 34 hits in 3.1.1, 0 in anything else | `v3.1.1`, and it must be ≥ 2.1 as dxvk-nvapi requires |
| vkd3d-proton | `strings d3d12core.dll \| grep vkd3d-proton` — 161 hits | `3.0.1` |
| dxvk-nvapi | `strings nvapi64.dll \| grep DXVK-NVAPI` | `v0.9.2` |

Anything failing that test is installed or reinstalled, and the setup says which
test failed and why (including the size comparison, so "that is Wine's builtin"
is a claim with a number behind it). `--force-layers` reinstalls all three
regardless, for when the check itself is suspect.

The replaced DLLs are kept as `*.bak_replaced` rather than overwritten silently.

## Also in this round

`tools/run_tests.sh --push` commits `test-results/<timestamp>/` and pushes it.
Scoping was verified in a throwaway repository: it commits the report directory
and nothing else, and on a failed push it says so and leaves the commit local
instead of reporting success.

## Confidence

The failure is now pinned by file size, not inference: the wrong DLLs are
identifiable and the right ones are downloadable and identifiable. If those
three markers pass and `NvAPI_Initialize` still fails, the next suspects are the
override actually taking effect at load time and Wine's own `vulkan-1`.

---

# Round 3 — `0xBAD00002`, and NVAPI finally says why (kept)

The round-2 changes took effect: dxvk-nvapi loaded (`DXVK-NVAPI v0.9.2 ... x86_64
release (nvngx.dll)`) and `DXVK_ENABLE_NVAPI=1` was clearly in force, because it
was logging at all. Then it stated the cause itself:

```
nvapi64:Querying Vulkan entry point from DXGI factory failed, please ensure
         that DXVK's dxgi.dll (version 2.1 or newer) is present
nvapi64:<-NvAPI_Initialize: NVIDIA or other suitable device not found or
         initialization failed
```

**DXVK was never installed.** dxvk-nvapi reaches the Vulkan entry point through
DXVK's `dxgi.dll` extension points; without that file `NvAPI_Initialize` fails,
NGX Core gets no platform answer, and init returns `0xBAD00002`. `tools/
wine_ngx_setup.sh --check` showed it plainly — `vkd3d-proton missing`, and no
DXVK files at all — but its section 4 was skipped as a check.

That was a **workflow bug in my own harness**, not a missing piece of
understanding. `tools/run_tests.sh --report --m0` ran the setup with `--check`,
so following my own instructions diagnosed the prefix without ever configuring
it. The gate then reported the same `0xBAD00002` with nothing saying the setup
had never been applied.

Fixes:

- `run_tests.sh --m0` now runs `wine_ngx_setup.sh` **without** `--check` (it is
  idempotent), snapshots the prefix afterwards, and stores the setup output as
  `raw/wine_ngx_setup.txt`.
- The setup script reports the presence of every layer file in **both** modes.
  A `--check` that silently omitted that is how this went unnoticed for a round.
- The gate was reading only `dlss5-feed-host.log` for its NVAPI section, so it
  printed "no NVAPI output at all" while the answer sat in Wine's console — the
  worker's stage logs and dxvk-nvapi's `nvapi64:` lines go to different streams.
  It now captures both.
- The gate detects that exact dxvk-nvapi message and quotes the fix back.
- `tests/test_worker_env_consistency.py` now also covers
  `tools/wine_ngx_setup.sh`, and it immediately earned its keep: it failed on
  this change because the setup script never mentioned `DXVK_ENABLE_NVAPI`.

## What to run now

```bash
git pull
tools/wine_ngx_setup.sh          # no --check: this is the step that installs DXVK
tools/m0_env_gate.sh
```

or simply `tools/run_tests.sh --report --m0`, which now does both.

## Confidence

Higher than round 2, because this failure was not inferred — dxvk-nvapi printed
the cause and the missing file was independently visible in the setup snapshot.
It is still not proven until the gate exits 0. If `NvAPI_Initialize` succeeds
and init passes, the next thing to watch is **feature 18 create**, where the
CuBIN path needs dxvk-nvapi ≥ 0.9.2 against vkd3d-proton ≥ 3.0.1.

---

# Round 2 — `0xBAD00002` FAIL_PlatformError (kept)

Round 1's diagnosis was right and its fix worked: the registry entry took effect
(`NGXCore registry: FullPath REG_SZ Z:\usr\lib\nvidia\wine`), and the error moved
on. Round 2 is a *different* failure, not a repeat.

`0xBAD00002` at the init stage means NGX Core loaded and ran, then asked the
platform about the GPU and did not get a usable answer. Under Wine that answer
has to come from **dxvk-nvapi**, and dxvk-nvapi's requirements are explicit in
its own README (`## Wine / Wine-Staging`):

- copy `nvapi64.dll` / `nvofapi64.dll` into the prefix's `system32`
- **copy `nvngx.dll` / `_nvngx.dll` into `system32`** (round 1 did this)
- ensure **DXVK**'s `dxgi.dll` is installed and used — *"Using Wine's D3D11 or
  DXGI implementation will fail"*
- **set `DXVK_ENABLE_NVAPI=1`** — *"to disable DXVK's nvapiHack in DXVK"*

Round 1's overrides covered `d3d12,d3d12core,nvapi64,dxgi` but **not `d3d11`**,
and `DXVK_ENABLE_NVAPI` was never set — the GPU box's environment dump confirms
it: the variable is simply absent.

`native/run_worker.sh` and `tools/m0_env_gate.sh` now set:

```
WINEDLLOVERRIDES="d3d12=n,b;d3d12core=n,b;d3d11=n,b;dxgi=n,b;nvapi64=n,b;nvofapi64=n,b;nvngx_dlssnr=n"
DXVK_ENABLE_NVAPI=1
DXVK_NVAPI_LOG_LEVEL=info        # so NvAPI_Initialize shows up in the output
```

and `tools/wine_ngx_setup.sh` now **installs** the layers rather than only
reporting them — DXVK `3.1.1`, vkd3d-proton `3.0.1`, dxvk-nvapi `0.9.2` (the
versions the reference project pins; `0.9.2` is the one that passes 64-bit CuBIN
calls to vkd3d-proton `3.0.1+`, which matters at feature-create).

The gate now prints every `NvAPI_*` line it sees. If NVAPI never answered, that
is the next thing to chase, and it will say so instead of leaving us to infer it.

## Confidence

Round 1 was a hypothesis confirmed by the change in error code. Round 2 is the
same kind of step: the binding constraint moved from "NGX Core missing" to
"NGX Core cannot see the platform", and dxvk-nvapi is the only thing under Wine
that can supply the platform answer. It is still not proven until the gate exits
0.

---

## Round 1 detail (kept — the reasoning is still what round 2 builds on)

**Where:** `test-results/20260916T044806Z/` (pushed from the GPU box)
**Verdict:** FAIL — `NVSDK_NGX_D3D12_Init -> 0xBAD00001`

The gate and the tests need to be read separately: the pytest suite never ran on
the GPU box (`No module named pytest`), and the M0 result was not the dead end
the script's own verdict implied.

## What passed (this is the expensive part)

Everything up to NGX was healthy, on Wine 11.17 Staging, driver 615.71.09,
RTX 4080 SUPER (compute capability 8.9 — inside the runtime's sm_75/86/89/120
kernel set):

```
[host] adapter 0: NVIDIA GeForce RTX 4080 SUPER vendor=0x10DE
[host] DRED settings unavailable (settings1=0x80004002, settings=0x80004002)
[pure] standalone D3D12 device ready; no swapchain or carrier modules
```

- Wine runs the PE, with all its static imports (`SpoutDX.dll` → `Spout.dll`)
- **Windows DXGI adapter enumeration works**: the NVIDIA card is seen, vendor
  `0x10DE` (the worker rejects anything else)
- **`D3D12CreateDevice` works** — a real D3D12 device on the NVIDIA adapter
- `--test` mode is reachable and the worker runs its own banner

That clears the two risks that would have killed the port outright. D3D12 on top
of Wine + VKD3D on this machine works.

## What failed, and why

```
[host] NVSDK_NGX_D3D12_Init -> 0xBAD00001 (?)
[host] Init_with_ProjectID  -> 0xBAD00001 (?)
[host] NGX unavailable
0024:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
```

`0xBAD00001` is `FAIL_FeatureNotSupported`. **At the init stage it does not mean
"unsupported GPU"** — the card is supported. It means NGX Core was never found.

`native/nvngx.dll` statically links NVIDIA's own NGX loader. Its strings name the
three paths it tries:

```
NGXGetPathUsingQAI
NGXGetPathFromRegistry
NGXCore not found next to the application
```

Under Wine only one of the three can possibly work:

| path | why it fails |
|---|---|
| `NGXGetPathUsingQAI` | needs the D3DKMT adapter query — that is the `type 48 not handled` line above. Unimplemented in Wine. |
| "next to the application" | name collision. The worker's own file **is** `nvngx.dll`, so the loader finds a module with no exports. |
| `NGXGetPathFromRegistry` | **the only one left** — and nothing had written the key. |

Two further pieces were missing from the launcher:

- `WINEDLLOVERRIDES` only set `nvngx_dlssnr=n`. Without
  `d3d12,d3d12core,nvapi64,dxgi` as native-first, Wine loads its **builtin**
  d3d12 (old vkd3d) and builtin nvapi64, and NGX cannot reach the physical GPU
  through them.
- `DISPLAY` must be set. DXVK cannot create a Vulkan instance without one.

## The fix

`tools/wine_ngx_setup.sh`:

1. find the driver's NGX bridge DLLs. **On Arch `nvidia-utils` already ships
   them** at `/usr/lib/nvidia/wine/{nvngx,_nvngx}.dll` — nothing to download.
   Elsewhere they come from the matching `.run` (`--extract-only`).
2. copy them into the prefix's `system32` and into a dedicated bridge directory
   (dedicated because of the name collision above — never next to the worker).
3. write the four registry values the loader consults:
   ```
   HKLM\SOFTWARE\NVIDIA Corporation\Global\NGXCore                    FullPath
   HKLM\SOFTWARE\NVIDIA Corporation\Global\NGXCore                    NGXPath
   HKLM\System\CurrentControlSet\Services\nvlddmkm\NGXCore             NGXPath
   HKLM\System\CurrentControlSet\Services\nvlddmkm\Parameters\NGXCore  NGXPath
   ```
4. report the translation-layer versions.

Then `native/run_worker.sh` and `tools/m0_env_gate.sh` set:

```
WINEDLLOVERRIDES="d3d12,d3d12core,nvapi64,dxgi=n,b;nvngx_dlssnr=n"
```

## Where this came from

Not guesswork — a project already doing exactly this on Linux, whose findings
match ours line for line:

- **LQCCS/ComfyUI-DLSS5NR-Wine** — DLSS 5 NR (feature 18) on Linux via Wine +
  vkd3d-proton, `docs/FINDINGS.md`. Its §⑤ is the DLL-override trap, §⑦ is the
  NGX-loader trap (same `NGXGetPathUsingQAI` / `NGXGetPathFromRegistry` strings,
  same conclusion: only the registry works), and its `install/setup_prefix.sh`
  is the source of the registry recipe above.
- **bmitch87/DLSS5VKLayer#18** — "CreateFeature(18) returns 0xbad00001 because
  the snippet cannot reach NVAPI — fixed by dxvk-nvapi + DXVK dxgi in the
  managed prefix".

## Still open after this fix

- **dxvk-nvapi ≥ 0.9.2 + vkd3d-proton ≥ 3.0.1.** The reference project needed
  both for 64-bit CuBIN calls; 0.9.1/3.0.0 gave
  `NvAPI_D3D12_CreateCubinComputeShaderExV2: Invalid pointer`. This bites at
  *feature create*, after init — so it is the next thing to look at if init
  succeeds and feature 18 does not.
- **The swapchain path needs a real refresh rate.** The reference project hit an
  integer divide-by-zero in DXVK's dxgi with Xvfb's `0.00 Hz` RandR output and
  fixed it with Xorg + the dummy driver at a real 60 Hz modeline. `--test` opens
  no swapchain, so M0 cannot hit this — but the live display loop (M3) can, and
  that is worth knowing before it looks like a NeuralScreen bug.
- The GPU box's pytest run produced only `No module named pytest`; that venv has
  no pytest. `tools/run_tests.sh` now installs it (or explains how) instead of
  writing an empty report.