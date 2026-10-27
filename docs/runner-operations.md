# Runner operations: where everything lives and how to tell what broke

`runs/README.md` describes the request/result *contract*. This file describes the
*machinery*: which piece runs where, what proves each piece is alive, and the failure modes
that have actually cost time. Read this before concluding "the runner is broken".

## Topology: three places, two schedulers

There are two independent schedulers. Confusing them is the single most expensive mistake
available here, because each one's health signal says nothing about the other.

| where | what lives there | what runs there |
|---|---|---|
| **The GPU box**, `/opt/neuralscreen/` | `policy.toml`, `state/repo` (the runner's own clone), `port/`, `model/`, `deploy_key`, `PAUSE` | the **systemd user timer** + `auto_runner.py` |
| **The agent sandbox**, `/opt/data/neuralscreen-linux/` | the developer's clone of the repo; the profile at `/opt/data/profiles/neuralscreen/` | the **Hermes cron ticker** and its jobs |
| **GitHub** | branch `main` = requests in; branch `results` = results out | neither runs; both schedulers talk to it |

The agent sandbox cannot see `/opt/neuralscreen/` at all — a plain `ls` there returns "No such
file or directory". That is expected, not a fault. Conversely, the GPU box does not read the
sandbox's checkout; it works from its own clone under `/opt/neuralscreen/state/repo`.

### Scheduler 1 — the systemd timer (GPU box): does the actual work

`neuralscreen-runner.timer` fires `neuralscreen-runner.service` **15 seconds after the
previous pass finishes** (`OnUnitInactiveSec=15s`, oneshot, so passes never stack). Each pass
runs:

```
/usr/bin/python3 /opt/neuralscreen/auto_runner.py --policy /opt/neuralscreen/policy.toml --once
```

Note it runs on **system python**, not the venv. The venv matters only when a request's argv
does `uv run python -m minimal`, which is what the `minimal` policy entry does.

Each pass: fetch `main` → look for `runs/queue/<id>.json` → skip `manual: true` → policy
check → exec in the sandbox → commit the outcome to `results` as `runs/done/<id>/`.

### Scheduler 2 — the Hermes cron ticker (sandbox): does the analysis

Profile `neuralscreen` has two jobs (`/opt/data/profiles/neuralscreen/cron/jobs.json`):

* `neuralscreen-progress` (`b639f19f57ff`), every 2 minutes — the *progress tick*. It works
  `runs/next.md`, reads new results off the `results` branch, and analyses them. Its change
  detector is `scripts/ns-results-monitor.sh`: the newest `runs/done/<id>` name plus a hash of
  `runs/next.md` as committed to `main`. It is deterministic so an idle tick produces no
  change and the loop stops instead of spinning.
* `neuralscreen-progress-watchdog` (`4ede271c53a9`), every 15 minutes —
  `scripts/ns-progress-watchdog.sh`. Silent while healthy; speaks only when the progress
  tick's output directory has had no new file for 30 minutes. Its "healthy" signal is the
  output directory `/opt/data/cron/output/b639f19f57ff/`, which the scheduler writes for every
  tick including silent `no_change` ones — so "no file" means "not being run", not "nothing
  to do".

## What proves what is alive

This is the part to get right.

* **`cron/ticker_heartbeat` (and `ticker_last_success`) = the HERMES CRON TICKER's liveness.**
  The ticker rewrites it roughly every 60 seconds (its age cycles 12s → 72s → back to 12s).
  It is written by the Hermes scheduler itself, per profile — the repo's `auto_runner.py`
  never touches it. **A fresh heartbeat therefore says nothing about the GPU runner.**

  Measured behaviour, so a false alarm is avoidable: sample it twice 12 seconds apart and the
  age simply grows by 12 — that is normal for a 60-second ticker. Only conclude "stalled" if
  the *epoch value inside the file* stops changing across more than ~2 minutes. A growing
  *age* alone is not evidence.

* **The `results` branch's newest commit time = when the GPU runner last completed a run.**
  This is the only reliable remote signal for scheduler 1. If a request sits on `main` for
  longer than a couple of minutes while the results branch's top commit is old, the GPU
  runner is not consuming requests.

* **A request that never lands as a result is not necessarily a failed run.** If the runner
  cannot start at all (missing venv, broken symlink), no result commit is written and the
  request stays in `runs/queue/` forever. A *failed* run does land — with `exit_code` 124,
  125, or 126, or the program's own code. Absence of a result means "never started", not
  "failed".

## The venv coupling — the failure mode that stops everything

The unit sets `UV_OFFLINE=1`: a run must never want PyPI, because the sandbox only reaches
GitHub. So the venv has to be primed by hand, once, in the runner's clone:

```sh
cd /opt/neuralscreen/state/repo
uv sync            # NOT --offline: the box has network (git push works)
```

Three ways this goes wrong, all seen in practice:

1. **`uv sync --offline` with an uncached dependency.** It fails on the first package not in
   the cache (`opencv-python==5.0.0.93` did exactly this) and leaves `.venv` empty or absent.
   The host has network — the offline flag was the mistake. Drop it. If offline is required,
   pre-cache the wheels first.

2. **`ProtectHome=yes` with the venv's interpreter symlinked into `/home`.** uv creates
   `.venv/bin/python -> ~/.local/share/uv/python/cpython-3.11-.../bin/python3.11`. Under
   `ProtectHome=yes` the unit cannot even traverse `/home`, so the symlink cannot be
   canonicalised and every run dies before the pipeline starts:
   `failed to canonicalize path .../.venv/bin/python: Permission denied (os error 13)`.
   Either use `ProtectHome=read-only` (the unit's current default, chosen while the worker and
   model still live in home), or stage the interpreter, the port and the model under
   `/opt/neuralscreen/` and only then switch to `yes`.

3. **A half-finished recovery.** Moving `.venv` to `.venv.old` and then failing the sync
   leaves *neither* — if the move succeeded and the sync died, `.venv.old` is the only working
   tree and it must be moved back before anything runs.

Check it directly on the box:

```sh
ls -l /opt/neuralscreen/state/repo/.venv/bin/python     # does it exist and resolve?
/opt/neuralscreen/state/repo/.venv/bin/python -c "import numpy, PIL; print('ok')"
```

## Reading a run without being at the machine

Everything needed is on the `results` branch; fetch it and read the run directory:

```sh
git fetch origin results
git ls-tree -r --name-only origin/results runs/done/<id>/
git show origin/results:runs/done/<id>/report.md
git show origin/results:runs/done/<id>/result.json     # exit_code, seconds
git show origin/results:runs/done/<id>/stdout.log | tail -40
git show origin/results:runs/done/<id>/stderr.log | tail -40
```

Exit codes the runner itself uses: `126` refused by policy, `125` the runner failed,
`124` killed by the timeout. Anything else is the program talking.

For image runs, judge the picture with `tools/jpeg_blockiness.py` rather than an edge filter.
Edge energy is the wrong instrument for compression: JPEG *ringing* raises edge energy, so a
"sharper" edge histogram can mean more artifacts. The 8x8 grid is the thing to measure — a
clean 1440p frame scores ~0.96 and a q20 re-encode ~1.56. `detail` (global variance over
blurred variance) is nearly identical between the two and cannot tell them apart.

## Checklist when a request does not come back

1. `git log origin/results --format='%h %cI %s' -3` — how old is the newest result? If it is
   older than the request, scheduler 1 is not completing runs.
2. On the GPU box: `systemctl --user list-timers neuralscreen-runner.timer` and
   `journalctl --user -u neuralscreen-runner.service -n 50`.
3. On the GPU box: does `.venv/bin/python` exist and import? (see above — this is the usual
   cause)
4. Check `/opt/neuralscreen/PAUSE` — if it exists, nothing runs and the timer keeps ticking.
5. Only after all that, suspect the request: is its `entry` named by the policy, are its args
   well-formed, and does it need `manual: true`?

The heartbeat is *not* on this list for a reason: it proves the Hermes ticker is alive and
says nothing about whether the GPU box is running anything.
