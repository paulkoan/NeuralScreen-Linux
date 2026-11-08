#!/usr/bin/env python3
"""One line if the scheduler recorded a failure for a cron job; nothing at all if it did not.

Why this is a program and not a grep. The watchdog used to read the tick's own output and search
it for the word FAILED. That output is prose, and Hermes' file-mutation verifier writes
"1 file edit(s) FAILED this turn" into the output of runs that SUCCEEDED - so on 2026-11-08 the
watchdog announced a failed tick every 15 minutes for over an hour, and told the developer the
item would never be retried, on the strength of one refused overwrite of
/opt/data/tmp/append_reported.py. Meanwhile the tick was running every 2 minutes and every one of
the 1000 rows in executions.db read "completed".

The scheduler keeps the truth in cron/executions.db, beside this profile's other cron state.
`cron_incidents` holds the failures it classified, each with a state that becomes "resolved" when
they clear; a non-completed row in `executions` is the fallback for a failure it recorded but did
not classify. Read one of those, and keep quiet otherwise.

usage: ns-cron-failure.py <executions.db> <job_id>
"""
from __future__ import annotations

import sqlite3
import sys

# A failure the scheduler has cleared is not news. Nothing here reads an incident that is closed.
_QUIET_INCIDENT_STATES = ("resolved", "closed")
# Anything that is not a finished-and-fine execution is worth looking at; these are the states that
# mean "finished and fine", so they are the ones to exclude.
_FINE_STATUSES = ("completed", "running", "scheduled", "pending")


def failure(db: str, job: str) -> str:
    """The newest recorded failure for `job`, as one line, or "" if there is none."""
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        return ""
    try:
        rows = list(conn.execute(
            "select failure_type, coalesce(error, ''), last_seen_at from cron_incidents "
            f"where job_id = ? and state not in {_QUIET_INCIDENT_STATES} "
            "order by last_seen_at desc limit 1", (job,)))
        if not rows:
            rows = list(conn.execute(
                "select status, coalesce(error, ''), finished_at from executions "
                f"where job_id = ? and status not in {_FINE_STATUSES} "
                "order by finished_at desc limit 1", (job,)))
    except sqlite3.Error:
        # A database mid-write, or a schema this does not know. Silence is the safe answer: this
        # script's job is to avoid crying wolf, and the freshness check still covers a dead tick.
        return ""
    finally:
        conn.close()
    if not rows:
        return ""
    kind, err, when = rows[0]
    err = " ".join((err or "no error recorded").split())[:200]
    return f"{kind}: {err} ({when})"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: ns-cron-failure.py <executions.db> <job_id>", file=sys.stderr)
        return 2
    line = failure(sys.argv[1], sys.argv[2])
    if line:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
