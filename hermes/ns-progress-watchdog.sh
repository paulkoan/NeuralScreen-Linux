#!/bin/bash
# Watches the watcher: is the progress tick (cron job b639f19f57ff) still running?
#
# Silent while it is healthy - the whole point is not to add to the noise. It speaks only when
# the tick has gone quiet for longer than its schedule can explain, which is the failure that
# cost us an hour this evening: the job backed off after a run died, kept saying "scheduled",
# and nothing anywhere said it had stopped.
#
# The signal is the job's own output directory. The scheduler writes a file there for every
# tick, including the silent no_change ones, so "no new file in N minutes" means the scheduler
# is not running it at all rather than "there was nothing to do".
#
# Empty stdout sends no message. A line of stdout is delivered. Nothing here is clever.
set -uo pipefail

# The output directory belongs to THIS profile. Derive it from the script's own location so a
# move between profiles cannot leave the watchdog watching a directory that no longer exists -
# which made it report "may never have run" every 15 minutes while the tick was in fact healthy.
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../cron/output/b639f19f57ff" 2>/dev/null && pwd)"
limit_minutes=30

newest=$(ls -t "$dir"/*.md 2>/dev/null | head -1)
if [ -z "$newest" ]; then
    echo "neuralscreen-progress has produced no output at all - it may never have run."
    exit 0
fi

age_minutes=$(( ($(date +%s) - $(stat -c %Y "$newest")) / 60 ))
if [ "$age_minutes" -gt "$limit_minutes" ]; then
    echo "neuralscreen-progress has not run for ${age_minutes} minutes (newest tick: $(basename "$newest"))."
    echo "The tick is probably wedged rather than idle - check its state with cronjob list, and the runner with 'systemctl --user list-timers neuralscreen-runner.timer' on the GPU box."
    exit 0
fi

# A FAILED tick still writes a file, so freshness alone cannot see it - and because a failed run
# also advances the monitor's change-detector baseline, the item it was working is dropped and
# never retried. Ask the SCHEDULER, which records failures as failures, instead of reading the
# tick's own prose.
#
# This block used to grep that prose for the word FAILED, and that word appears in the output of
# runs that SUCCEEDED: Hermes' file-mutation verifier writes "1 file edit(s) FAILED this turn"
# whenever one of the run's own writes was refused. So on 2026-11-08 it announced a failed tick
# every 15 minutes for over an hour, telling the developer the item would never be retried, on the
# strength of one refused overwrite of /opt/data/tmp/append_reported.py - while the tick was
# running every 2 minutes and all 1000 rows in executions.db read "completed".
#
# Once per incident as well: a failure that has already been reported is not news 15 minutes later.
exdb="$(cd "$(dirname "$dir")/.." 2>/dev/null && pwd)/executions.db"
fmarker="$(dirname "$dir")/.failure-notified"
incident=""
if [ -f "$exdb" ]; then
    helper="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)/ns-cron-failure.py"
    if [ -f "$helper" ] && command -v python3 >/dev/null 2>&1; then
        incident=$(python3 "$helper" "$exdb" b639f19f57ff 2>/dev/null)
    fi
fi
if [ -n "$incident" ]; then
    if [ ! -f "$fmarker" ] || [ "$(cat "$fmarker" 2>/dev/null)" != "$incident" ]; then
        printf '%s\n' "$incident" > "$fmarker" 2>/dev/null || true
        echo "neuralscreen-progress has a failure the scheduler recorded:"
        echo "  $incident"
        echo "The item it was working stays in runs/next.md and is not retried by itself."
    fi
else
    # Nothing on the books: clear the marker so a later failure may speak. Without this, a failure
    # that cleared and then recurred could present the same text while the marker from the first
    # occasion was still in place, and the second one would be swallowed.
    [ -f "$fmarker" ] && rm -f "$fmarker"
fi

# An EMPTY plan is the quietest stall of all: every tick finds nothing to do, writes a no_change
# stub, and the change detector never fires because the plan genuinely did not change. Freshness
# looks perfect and the project sits still for hours - which is exactly what happened on
# 2026-10-29, and cost a morning. Check the actionable section of next.md on origin/main: if it
# holds no bullet, the tick has nothing to act on and nobody will ever be told.
repo="/opt/data/neuralscreen-linux"
plan_marker="$dir/.empty-plan-notified"
if [ -d "$repo/.git" ]; then
    timeout 20 git -C "$repo" fetch -q origin main 2>/dev/null || true
    # learned: bullets are history parked in this section, not work - excluding them is what
    # makes "no work items" mean no work rather than "twelve notes and nothing to do".
    bullets=$(git -C "$repo" show origin/main:runs/next.md 2>/dev/null \
              | sed -n '/^## 1\. Next work/,/^## /p' \
              | grep -E '^\s*\* ' | grep -vcE '^\s*\* learned:' || true)
    if [ "${bullets:-0}" -eq 0 ]; then
        # Once, not every fifteen minutes: a marker ages out after six hours and it says so again.
        if [ ! -f "$plan_marker" ] || [ $(( ($(date +%s) - $(stat -c %Y "$plan_marker")) / 60 )) -gt 360 ]; then
            touch "$plan_marker"
            echo "runs/next.md has NO work items in '## 1. Next work' on origin/main."
            echo "Every tick will report no_change and the project will stand still without a word - which is not the same as having nothing to do. Re-arm the plan."
        fi
    else
        rm -f "$plan_marker" 2>/dev/null || true
    fi
fi

# ---- the model itself: a provider returning nothing is not a plan problem -----------------
# The tick runs on the main agent model. When the provider keeps returning empty responses,
# the tick's agent runs fail and its output still reads "no_change", so neither freshness nor
# the FAILED scan below sees it - the only signal is the error log. Say when the provider has
# returned nothing in the last ten minutes, with the line, so "not replying" is a fact.
errlog="/opt/data/profiles/neuralscreen/logs/errors.log"
if [ -f "$errlog" ]; then
    last=$(grep -E "Empty response|Reasoning-only" "$errlog" 2>/dev/null | tail -1)
    if [ -n "$last" ]; then
        ts=$(printf '%s\n' "$last" | awk '{print $1" "$2}')
        ts="${ts%,*}"
        age=$(( $(date +%s) - $(date -d "$ts" +%s 2>/dev/null || echo 0) ))
        if [ "$age" -ge 0 ] && [ "$age" -le 600 ]; then
            echo "The model is returning empty responses: ${last:0:170}"
            echo "The tick runs on this model, so its runs can be failing while its output still reads 'no_change'. Check the provider before trusting the tick's silence."
        fi
    fi
fi

# ---- heartbeat: silence should mean "nothing to say", not "maybe stopped" ----------------
# While the plan has open work and no run has finished for half an hour, say so once every 30
# minutes. This is the answer to "are you stopped?": the tick only speaks when it acts, and a
# queued run plus its tick can be quiet for several minutes at a time.
marker="$(dirname "$dir")/.heartbeat-last"
repo="/opt/data/neuralscreen-linux"
if [ -d "$repo/.git" ]; then
    ( cd "$repo" && timeout 20 git fetch -q origin ) 2>/dev/null || true
    last_result=$(cd "$repo" && git log -1 --format=%ct origin/results 2>/dev/null || echo 0)
    now=$(date +%s)
    idle=$(( now - ${last_result:-0} ))
    plan=$(cd "$repo" && git show origin/main:runs/next.md 2>/dev/null)
    # Only real work counts: a learned note in this section is history, not a queued item.
    # Counting every bullet inflated the heartbeat to "12 open items" when the plan held one.
    open=$(printf '%s\n' "$plan" | awk '/^## 1\. Next work/{f=1;next} /^## /{f=0} f && /^[[:space:]]*\* / && !/^[[:space:]]*\* learned:/' | wc -l)
    # A manual request is waiting on a person, not stalled. Saying "still on it" every half hour
    # while the developer is asleep is noise, not information: the queue is held, not stuck.
    manual=""
    for f in $(git -C "$repo" ls-tree --name-only origin/main runs/queue/ 2>/dev/null | sort | tail -15); do
        if git -C "$repo" show "origin/main:$f" 2>/dev/null | grep -qE '"manual"[[:space:]]*:[[:space:]]*true'; then
            manual="$f"; break
        fi
    done
    if [ -n "$manual" ]; then
        open=0
    fi
    last_hb=$(cat "$marker" 2>/dev/null || echo 0)
    if [ "${open:-0}" -gt 0 ] && [ "$idle" -ge 1800 ] && [ $(( now - ${last_hb:-0} )) -ge 1800 ]; then
        item=$(printf '%s\n' "$plan" | awk '/^## 1\. Next work/{f=1;next} /^## /{f=0} f && /^[[:space:]]*\* / && !/^[[:space:]]*\* learned:/{sub(/^[[:space:]]*\* /,""); print; exit}')
        echo "Still on it: ${open} open item(s), last run finished $(( idle / 60 )) min ago."
        echo "Next: ${item:0:220}"
        echo "Full picture: python3 $repo/tools/status.py"
        echo "$now" > "$marker"
    fi
fi
