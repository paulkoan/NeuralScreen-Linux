#!/usr/bin/env python3
"""One screen of truth: is anything actually happening?

Reads the two branches the work moves through - `main` for the plan and the queue, `results`
for the runs that finished - and says whether the pipeline is active, idle with work left, or
stuck. Built because "no message" is ambiguous: the 2-minute tick is silent when it has nothing
substantive to say, and a queued run takes minutes before its result lands.

    python3 tools/status.py
    python3 tools/status.py --json

Exit code is always 0; this is a report, not a check.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def git(*args: str, timeout: int = 30) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, timeout=timeout
    ).stdout


def age(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 90:
        return f"{seconds}s"
    if seconds < 5400:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h{seconds % 3600 // 60:02d}m"


def plan_item() -> str:
    """The first bullet under `## 1. Next work`, wrapped to one line."""
    text = git("show", "origin/main:runs/next.md")
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## 1. Next work"):
            start = i + 1
            break
    if start is None:
        return "(no plan section)"
    bullet: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.strip().startswith("* "):
            if bullet:
                break
            bullet.append(line.strip()[2:])
        elif bullet and line.strip():
            bullet.append(line.strip())
        elif bullet:
            break
    return " ".join(bullet)[:160] or "(the plan has no open item)"


def queue() -> list[str]:
    entries = [
        line.split("/")[-1].removesuffix(".json")
        for line in git("ls-tree", "--name-only", "origin/main", "runs/queue/").splitlines()
        if line.endswith(".json")
    ]
    done = git("ls-tree", "-r", "--name-only", "origin/results", "runs/done/")
    return sorted(e for e in entries if f"runs/done/{e}/" not in done)


def last_runs(n: int = 3) -> list[dict]:
    out = git(
        "log", "-n", str(n), "--format=%ct%x09%s", "origin/results"
    ).splitlines()
    runs = []
    for line in out:
        if "\t" not in line:
            continue
        ts, subject = line.split("\t", 1)
        if not subject.startswith("run "):
            continue
        runs.append({"when": int(ts), "subject": subject})
    return runs


def last_tick() -> dict | None:
    out_dir = Path("/opt/data/profiles/neuralscreen/cron/output/b639f19f57ff")
    newest = max(out_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, default=None)
    if newest is None:
        return None
    body = newest.read_text(errors="replace")
    status = next((l.split(":", 1)[1].strip() for l in body.splitlines() if l.startswith("**Status:**")), None)
    if status is None:
        # A tick that had nothing to say carries no Status line; one that acted carries the size
        # of its reply instead.
        chars = next(
            (l.split(":", 1)[1].strip() for l in body.splitlines()
             if l.startswith("**Response Characters:**")),
            None,
        )
        status = f"ran, {chars} chars" if chars else "no_change"
    return {"mtime": newest.stat().st_mtime, "name": newest.name, "status": status}


def main() -> int:
    git("fetch", "-q", "origin")
    now = time.time()
    pending = queue()
    runs = last_runs()
    tick = last_tick()
    item = plan_item()

    newest_result = runs[0]["when"] if runs else 0
    result_age = now - newest_result if newest_result else float("inf")

    if pending:
        verdict = f"ACTIVE - {len(pending)} run(s) queued: {', '.join(pending)}"
    elif result_age < 15 * 60:
        verdict = f"ACTIVE - a run finished {age(result_age)} ago"
    elif item != "(the plan has no open item)":
        verdict = f"WAITING - open work on the plan and nothing queued ({age(result_age)} since the last result)"
    else:
        verdict = "IDLE - the plan has no open item"

    data = {
        "now": int(now),
        "verdict": verdict,
        "plan_item": item,
        "queue": pending,
        "last_result_age_s": None if result_age == float("inf") else int(result_age),
        "recent_runs": runs,
        "last_tick": tick,
    }
    if "--json" in sys.argv[1:]:
        print(json.dumps(data, indent=2))
        return 0

    print(f"neuralscreen status   {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(now))}")
    print(f"  verdict      {verdict}")
    print(f"  plan item 1  {item}")
    print(f"  queued       {', '.join(pending) if pending else 'none'}")
    if runs:
        for r in runs:
            print(f"  result       {age(now - r['when']):>5} ago  {r['subject']}")
    else:
        print("  result       none on origin/results")
    if tick:
        print(f"  last tick    {age(now - tick['mtime']):>5} ago  {tick['status']}  ({tick['name']})")
    else:
        print("  last tick    no output files at all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
