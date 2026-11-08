# hermes/ - the agents that drive this project

Not the port. These are the Hermes-side scripts for the `neuralscreen` profile on the machine
that holds this repo's checkout, and they are here because they were previously installed in the
profile and **nowhere else**. On 2026-11-08 the progress watchdog was rewritten to stop it
reporting failures that had not happened, and the only copy of that fix was on one box, inside a
directory no git command looks at. A script that decides whether the project is making progress
should be readable, diffable and restorable.

| file | what it does |
|---|---|
| `ns-results-monitor.sh` | The change detector. Prints the newest run id on the results branch (by commit time, not by name), a 12-char hash of the work items in `runs/next.md` above `## Learned`, and the tick's last recorded outcome. The scheduler skips the agent run when this output is unchanged, so it decides when the loop wakes. |
| `ns-tick-state.py` | The tick's record of what it did: item, outcome (done / blocked / failed / idle), reason, attempts. The detector folds its `line` subcommand in, and the watchdog's stop report reads its `report` subcommand. |
| `ns-progress-watchdog.sh` | Fires every 15 minutes and is silent unless something is wrong: the tick has stopped, the plan's `## 1. Next work` holds no items, the model is returning empty responses, the scheduler has recorded a failure, or the loop has stopped with a reason. Empty stdout sends nothing - saying nothing is the normal case. |
| `ns-cron-failure.py` | The watchdog's failure check. Reads the scheduler's `cron/executions.db` (open incidents, else a non-completed execution) and prints one line, or nothing. |

## Why the loop goes quiet, and why that is now meaningful

The tick is gated: it only runs when the detector's output changes. For most of this loop's life
that output was the newest result plus a hash of the plan - and **both of those change only when
the loop succeeds**. A tick that failed, or that found its item needed a decision, left the output
identical and was never run again. Measured on 2026-11-08: **50 fires, 3 agent runs, 47
suppressions**, while a heartbeat told the developer "still on it" every 32 minutes. The loop was
not stuck in a way anything could see.

Two changes fix that, and they only work together:

1. **The tick records an outcome every run** (`ns-tick-state.py record`). The detector folds it in,
   so a run that does not retire its item still changes the detector's output and wakes the next
   tick. The attempts count is capped *in the detector's line*, not in the record, so the loop
   retries up to three times and then settles instead of spinning.
2. **The watchdog's heartbeat is gone, replaced by a stop report.** It speaks once when the loop
   cannot get on by itself, naming the item and the reason, and stays quiet until that changes.
   The old heartbeat could not answer "is it stuck", because it looked identical whether the loop
   was working or wedged.

The rule this all follows: **never infer the loop's health from prose.** The failure check reads
the scheduler's database, the state reads a record the tick writes, and the only thing still
parsed from text is the plan's work-item count.

## Installing

The profile directory is **not** a git repository, so these are copied in:

```
hermes/install.sh            # copy them into the profile
hermes/install.sh --check    # report drift, change nothing (exit 1 if anything differs)
```

That copy-in is the one manual step, and it is exactly the trap the port's `run_manually.sh` fell
into: a fix committed here does not reach the profile by itself. `--check` is the answer - run it
after editing anything in this directory. Set `NEURALSCREEN_PROFILE` if the profile is somewhere
else.

## What is deliberately not here

The job definitions - schedules, prompts, and the tick's own instructions, including its hard
limits - live in the profile's `cron/jobs.json`, which the scheduler owns. Prefer the cron tool.
A whole-prompt update round-trips kilobytes of text through an interface that does not diff it,
though, so a targeted patch on the file is sometimes the safer instrument - that is how the tick's
scratch-file instruction was corrected on 2026-11-08, after a reused script name tripped the
file-mutation verifier. Either way: follow a change to that file with `cronjob list` to confirm
the job still loads, and keep the tick's hard limits intact, since they are what bound it.

The current three, for reference:

- `b639f19f57ff` `neuralscreen-progress` - every 2 minutes, the tick, gated by `ns-results-monitor.sh`
- `4ede271c53a9` `neuralscreen-progress-watchdog` - every 15 minutes, `ns-progress-watchdog.sh`, no agent
- `474ad7960b3c` `dlss5-ecosystem-survey` - Mondays 09:00, the periodic look at other DLSS-5 work

## A note on what these are allowed to conclude

The watchdog's failure check is deliberate about its evidence. It used to grep the tick's own
output for the word `FAILED`, which is prose, and Hermes' file-mutation verifier writes
`1 file edit(s) FAILED this turn` into the output of runs that *succeeded* - so one refused
overwrite of a scratch file produced a failure notice every 15 minutes for over an hour while the
tick ran normally. It now asks the scheduler, which records failures as failures, and speaks once
per incident. The same rule applies to anything added here: prefer a source that has no opinion.
