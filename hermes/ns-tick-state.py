#!/usr/bin/env python3
"""The tick's own record of what it did, so the loop is level-triggered instead of edge-triggered.

The fault this exists to fix. The tick is gated by a change detector: the scheduler skips the agent
run when the detector's output is unchanged. The detector prints the newest result and a hash of
the work items in runs/next.md - and both of those change only when the loop *succeeds*. So a tick
that fails, or that finds its item needs a decision, leaves the detector output identical and is
never run again. The comment in the detector claims the plan hash is what stops the loop
deadlocking; it does not, because it watches for the plan *changing*, not for the plan *having
work*. On 2026-11-08 that read: 50 tick fires, 3 agent runs, 47 suppressions, and a heartbeat
telling the developer "still on it" every 32 minutes while nothing moved.

What this file adds. Every tick records an outcome here, and the detector folds it into its output.
A run that does not retire its item therefore *changes* the detector's output and wakes the next
tick - one retry - and the attempts counter is capped in the detector's line (not here, so the
history stays true), so after the cap the output settles and the loop stops rather than retrying
forever. The watchdog then says once why it stopped, instead of reassuring every half hour.

usage:
  ns-tick-state.py record --item NAME [--outcome done|blocked|failed|idle] --reason "one line"
  ns-tick-state.py line      deterministic one-line fragment for the change detector
  ns-tick-state.py report    a line for the watchdog when the loop cannot progress, else nothing
  ns-tick-state.py show      the whole record, for a person

`record` keeps the attempts count: same item as last time increments it, a different item resets
it to 1, and outcome `done` resets it too, because a retired item is not a stuck one.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

OUTCOMES = ("done", "blocked", "failed", "idle")
# How many times the detector's line will keep changing before it settles. The loop retries this
# many times and then waits, which is the difference between a loop that recovers from a bad run
# and one that either gives up instantly or spins.
CAP = 3


def state_path() -> Path:
    """Beside the profile's other loop scratch, derived from this script's own location."""
    here = Path(__file__).resolve().parent
    return Path(os.environ.get("NS_TICK_STATE") or here.parent / "cron" / "output" / "tick_state.json")


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic: the detector may read this at any moment, and half a record would read as junk.
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tick_state-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(record, fh, indent=1, sort_keys=True)
        os.replace(tmp, path)
    except BaseException:
        with __import__("contextlib").suppress(OSError):
            os.unlink(tmp)
        raise


def record_line(record: dict) -> str:
    """The deterministic fragment. No timestamp: an unstable line would fire every tick."""
    if not record:
        return "state: none"
    item = str(record.get("item") or "?")[:60]
    outcome = str(record.get("outcome") or "?")
    attempts = min(int(record.get("attempts") or 1), CAP)   # capped here, not in the record
    return f"state: {outcome} {item} #{attempts}"


def report(record: dict) -> str:
    """One line when the loop cannot progress on its own, nothing when it can."""
    if not record:
        return ""
    outcome = str(record.get("outcome") or "")
    if outcome not in ("blocked", "failed"):
        return ""
    item = str(record.get("item") or "?")[:80]
    reason = " ".join(str(record.get("reason") or "").split())[:200]
    attempts = int(record.get("attempts") or 1)
    verb = "could not be done" if outcome == "blocked" else "failed"
    return (f"The loop is stopped: {item} {verb} {attempts} time(s). {reason or 'no reason recorded'}")


def cmd_record(args) -> int:
    path = state_path()
    previous = load(path)
    same = args.item and previous.get("item") == args.item
    # A finished item is not a stuck one, and a different item is a fresh attempt.
    if args.attempts is not None:
        attempts = args.attempts
    elif same and args.outcome != "done":
        attempts = int(previous.get("attempts") or 1) + 1
    else:
        attempts = 1
    save(path, {"item": args.item, "outcome": args.outcome, "reason": args.reason or "",
                "attempts": attempts})
    print(f"recorded: {args.outcome} {args.item} #{attempts}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record")
    rec.add_argument("--item", required=True)
    rec.add_argument("--outcome", choices=OUTCOMES, default="done")
    rec.add_argument("--reason", default="")
    rec.add_argument("--attempts", type=int, default=None,
                     help="set the count outright instead of incrementing")
    rec.set_defaults(func=cmd_record)

    for name in ("line", "show", "report"):
        p = sub.add_parser(name)
        p.set_defaults(func=lambda a, n=name: print(
            {"line": record_line, "show": lambda r: json.dumps(r, indent=1, sort_keys=True),
             "report": report}[n](load(state_path()))) or 0)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
