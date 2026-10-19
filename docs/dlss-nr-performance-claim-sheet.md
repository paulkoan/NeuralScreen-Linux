# DLSS-NR performance claim sheet

Question 3 of the 310.8.16.0 investigation (`t_5aa7042d`, child of `t_2cab16c2`):
**make the "310.8.16.0 is more performant" claim checkable, or establish that it
currently is not.**

Written 2026-10-19 from the repo at `/opt/data/neuralscreen-linux` (main),
reading the run artifacts on `origin/results`. No port was run and no run was
queued from this card.

## Where the claim comes from

The belief does **not** originate in this repo. It enters through the human:

* Human message, Telegram DM, 2026-10-14 — session
  `@session:neuralscreen/20261014_054958_cefafc47`, message id 2122:
  *"Add a kanban triage to investigate vs 310.8.16.0 DLSS NR as it should be
  more performant"*.
* It was recorded into the triage card `t_2cab16c2` body as: *"a DLSS-NR runtime
  at version 310.8.16.0 is believed to be more performant than the runtime this
  port is built around"* (`t_2cab16c2` body, "Why:").

No source, URL, version string or measurement accompanies it. The string
`310.8.16` appears nowhere in the working tree, and `git log --all -S "310.8.16"`
returns **zero** commits — the version number has never existed anywhere in this
repository's history. (Whether the bundled DLL's full file version really is
`310.8.16.0` is settled from the binary by sibling `t_057cec57`; the external
provenance of the version is traced by sibling `t_93b39d01`.)

## What "network+composite" measures

Every number below is the worker's own per-frame timer bucket. The boundaries
are defined in `experiments/opendlss_port/linux-port.patch`:

| Timestamp | Patch line | Meaning |
|---|---|---|
| `began` | `experiments/opendlss_port/linux-port.patch:1410` | frame starts |
| `afterUpload` | `experiments/opendlss_port/linux-port.patch:1426` | input uploaded to D3D12 |
| `afterRecord` | `experiments/opendlss_port/linux-port.patch:1447` | NGX evaluate + composite recorded |
| `afterDownload` | `experiments/opendlss_port/linux-port.patch:1475` | readback copied back |
| `afterSend` | end of frame | reply sent |

The print that maps them to buckets is the `fprintf` at
`experiments/opendlss_port/linux-port.patch:1498-1501`:

```
serve frame %u: %.1f ms (proxy %.1f, network+composite %.1f, readback %.1f, reply %.1f)
index, ms, since(began, afterUpload), since(afterUpload, afterRecord),
since(afterRecord, afterDownload), since(afterDownload, afterSend)
```

So **`network+composite` = the interval from just after the input upload to just
after the NGX feature-18 evaluate plus the composite dispatch.** It is:

* **not network-only** — the composite dispatch is inside the interval;
* **not total frame time** — proxy upload, readback and IPC reply are separate buckets;
* measured at the work resolution (here 2560x1440, work scale 1.00).

## Claim sheet — one row per quoted number

| # | Value | What it measures | Frame | Resolution | Fixture / scene | Hardware | Source |
|---|---|---|---|---|---|---|---|
| 1 | **12.2 ms** | worker per-frame `network+composite` | frame 29 of 60 | 2560x1440 | `fixtures/youtube-1440p.png`, still, `--no-motion` | RTX 4080 SUPER 615.71.09, Arch/KDE | `origin/results:runs/done/r2026-10-12-b/stderr.log:17` |
| 2 | **12.0 ms** | same | frame 59 of 60 | same | same | same | `origin/results:runs/done/r2026-10-12-b/stderr.log:18` |
| 3 | **12.7 ms** | same | frame 29 of 60 | same | same | same | `origin/results:runs/done/r2026-10-12-d/stderr.log:18` |
| 4 | **12.2 ms** | same | frame 59 of 60 | same | same | same | `origin/results:runs/done/r2026-10-12-d/stderr.log:19` |
| 5 | **13.1 ms** | same | frames 29 and 59 | same | same | same | `origin/results:runs/done/r2026-10-11-c/stderr.log:16-17` |
| 6 | **12.5 ms** | "the plan" comparison figure — **not a measurement** | — | — | — | — | `runs/queue/r2026-10-11-f.json:20` |

The same four numbers are quoted in prose at these places:

| Value | Quoted at |
|---|---|
| 12.2 / 12.0 ms (b) | `runs/next.md:42`; `experiments/opendlss_port/README.md:333-334` |
| 12.7 / 12.2 ms (d) | `runs/next.md:53`; `experiments/opendlss_port/README.md:335` |
| 13.1 / 13.1 ms (c) | `runs/next.md:42` and `:53`; `runs/queue/r2026-10-12-b.json:1` |
| 12.5 ms | `runs/queue/r2026-10-11-f.json:20` |

### Run metadata behind the rows

| Run | Rev (port repo) | Worker build | Patch | Resolution line | Exit |
|---|---|---|---|---|---|
| `r2026-10-12-b` | `dc44bf7e57d8` | port 9d08f41 | `c2c4279a9623` | `origin/results:runs/done/r2026-10-12-b/report.md:8` | 0 |
| `r2026-10-12-d` | `17ea04efdc36` | port 9d08f41 | `08e297c8a802` | `origin/results:runs/done/r2026-10-12-d/report.md:8` | 0 |
| `r2026-10-11-c` | `af52854a7e61` | port 9d08f41 | `ea90414e2b00` | `origin/results:runs/done/r2026-10-11-c/report.md:8` | 0 |

All three ran the identical command (`origin/results:runs/done/<run>/command.txt`):
`uv run python -m minimal --source image --input-image fixtures/youtube-1440p.png
--headless --frames 60 --worker-log --shm --no-motion --send-ahead 2
--save-before before.png --save-after after.png`

Fixture: `fixtures/youtube-1440p.png`, sha256
`433847df0701176e548a24fbdd6c7a86b43a8bf473593effa2850f68af94c10f`.

### Hardware and OS

* GPU named by the run itself: `origin/results:runs/done/r2026-10-12-b/stderr.log:9`
  — `[worker] serve: device NVIDIA GeForce RTX 4080 SUPER`.
* Box: `test-results/20260919T075517Z/raw/environment.txt:2-6,10` — hostname
  `zone`, kernel `7.1.11-zen1-1-zen` (Arch), `XDG_SESSION_TYPE=wayland`,
  `desktop: KDE`, GPU `NVIDIA GeForce RTX 4080 SUPER, 615.71.09`.

## What these baselines are NOT

1. **Not total frame time.** The same runs report `total 88.8 ms/frame` (b),
   `94.5 ms/frame` (d) and `96.9 ms/frame` (c)
   (`origin/results:runs/done/r2026-10-12-b/stdout.log:10` and the matching
   lines in d and c) — dominated by `recv`. Quoting "12.2 ms" as "the frame
   costs 12.2 ms" would understate it by ~7x.
2. **Not network-only.** See the definition above; the composite dispatch is inside.
3. **Not a comparison of two runtimes.** All three runs load the same bundled
   `native/nvngx_dlssnr.dll`, described in the repo as the leaked **310.8.0**
   runtime (`README.md:260`, `README.md:264`, `TECHNICAL.md:376`,
   `docs/MVP-PLAN.md:39`). The only difference between the runs is the port's own
   patch: c = no history, b = history feed, d = history feed + blend. Nothing
   here varies the DLL.
4. **Not a 720p number.** The only other resolution figure in the repo is the
   whole-pipeline fps table, a different metric: `docs/M0-FINDINGS.md:462`
   (`1280x720 | 51.1ms (19.6 fps) | 78.6ms (12.7 fps) | 27.5ms`) and
   `docs/M0-FINDINGS.md:463` (`2560x1440 | 85.5ms (11.7 fps) | 98.6ms (10.1 fps)
   | 5-13ms`).

## Verdict on "310.8.16.0 is more performant"

**Unanchored as given — it cannot be checked against anything in this repo.**

1. No measurement in the repo compares two runtime versions. The only quoted
   baselines (12.2/12.0 ms, 12.7/12.2 ms, 13.1/13.1 ms) all measure the port's
   worker running the **same** bundled DLL.
2. "More performant" is undefined. The port's only quotable per-frame metric is
   `network+composite` ms at 2560x1440 on `fixtures/youtube-1440p.png`, on an
   RTX 4080 SUPER under Arch/KDE. A performance claim without a metric,
   resolution, frame and fixture cannot be evaluated.
3. Even if `310.8.16.0` is a distinct build (sibling `t_057cec57` decides this),
   there is no way to produce a comparable number today: the port's PTX kernels
   are extracted from the bundled DLL, so a different DLL would have to be
   extracted and driven through the same harness. That spec does not exist; the
   root card `t_2cab16c2` lists it as a "done when" condition.

If someone later wants to make the claim checkable, the minimum is: the
`network+composite` value at frames 29 and 59 of a 60-frame, `--shm --no-motion`,
2560x1440 run on `fixtures/youtube-1440p.png`, with the 310.8.16.0 DLL in
`native/`, compared against 12.2/12.0 ms (b) and 12.7/12.2 ms (d).

## Gaps called out explicitly

* **The plan's 12.5 ms disagrees with the run it cites.** The note at
  `runs/queue/r2026-10-11-f.json:20` reads "against 12.5ms (r2026-10-11-c)", but
  `r2026-10-11-c` actually reads **13.1 ms at both frames 29 and 59**
  (`origin/results:runs/done/r2026-10-11-c/stderr.log:16-17`). No measurement
  behind 12.5 ms exists in the repo. The later note at
  `runs/queue/r2026-10-12-b.json:1` corrects this to "a steady 13.1ms ... the plan
  quotes 12.5".
* **"Inside noise" is asserted, not measured.** b vs d differ by 0.5 ms at frame 29
  and 0.2 ms at frame 59. `runs/next.md:53` calls this "inside noise", but each
  number is a single run with no repeat count, error bar or variance. The gap
  between 12.2 and 12.7 ms is not distinguished from run-to-run drift by any
  evidence in the repo.
* **One resolution only.** Every baseline number is 2560x1440. The port's own
  README caps the network at 2560x1440 (`README.md:259`), so the claim cannot be
  probed above that; no 720p `network+composite` value for the same build exists.
* **Single frame pair.** Each run reports only frames 29 and 59 (the worker prints
  frames 0-3 and then every 30th, `linux-port.patch:1496`). Frame 0 is
  excluded as warm-up; there is no median or distribution.
