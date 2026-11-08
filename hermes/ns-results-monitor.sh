#!/bin/bash
# Change detector for the progress tick. Prints two stable things:
#
#   * the newest run id on the results branch - a new result means something to analyse;
#   * a hash of the WORK ITEMS in runs/next.md as committed to main - a change to the
#     ready work means work to do. Only the part above "## Learned" is hashed: the
#     Learned section is a running log that grows every time a tick retires an item,
#     and hashing it woke the tick on its own bookkeeping (the "nothing to report"
#     spam). A tick that edits the work items still wakes the next one.
#
# The second half is what stops the loop deadlocking: the plan can hold ready work that no
# result will ever trigger, and a tick that only woke on results would sit still while the plan
# said "ready". It also means a tick that edits the plan wakes the next one, so the plan is
# worked through in order and the ticks stop when it is empty or a tick leaves it alone.
#
# Deterministic on purpose: no timestamps, no pids - anything unstable would fire every tick.
set -uo pipefail
cd /opt/data/neuralscreen-linux 2>/dev/null || exit 0
export GIT_ASKPASS=/opt/data/secrets/github-askpass.sh
export GIT_TERMINAL_PROMPT=0
git fetch -q origin main results 2>/dev/null || exit 0
# The newest run by COMMIT TIME, not by name. `sort | tail -1` reads the name, and names sort
# by their own spelling: r2026-11-08-1080p-video sorts before r2026-11-08-recsplit, so a run
# whose id starts with a digit was invisible and the tick sat suppressed while results piled
# up. The commit message carries the run id and the commit time is what "newest" means.
git log -1 --format=%s origin/results 2>/dev/null
git show origin/main:runs/next.md 2>/dev/null | sed '/^## Learned/,$d' | sha256sum | cut -c1-12
