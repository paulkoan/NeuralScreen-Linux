#!/usr/bin/env python3
"""The box is off, and the loop should not read that as a stall.

With the box powered down nothing runs, nothing publishes, and the tick's item sits blocked on a run
that cannot happen - all of which is expected and none of which is a fault to report. Left alone, the
watchdog says "the loop is stopped" about a stop that is just a machine being switched off, which is
the noise the developer asked it to stop making.

So the state is declared rather than inferred: `mark` records the reason and the results commit that
was newest at the time. It clears itself the moment anything newer is published, because a result
arriving means the box is back - the loop resumes on its own, with no one having to say so.

    ns-box-off.py mark "the box is off for the night"
    ns-box-off.py status     # the reason while it holds, nothing once the box publishes again
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROFILE = Path(__file__).resolve().parent.parent
MARKER = PROFILE / "cron" / "output" / ".box-off"
REPO = Path("/opt/data/neuralscreen-linux")


def newest_result() -> str:
    try:
        subprocess.run(["git", "-C", str(REPO), "fetch", "-q", "origin", "results"],
                       capture_output=True, timeout=25)
        done = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%h",
                               "origin/results"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def mark(reason: str) -> int:
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(f"{newest_result()}\n{reason}\n")
    print(f"recorded: the box is off ({reason}); the watchdog will stay quiet about the stop")
    return 0


def status() -> int:
    """The reason while the box is still away, and nothing once it is back."""
    if not MARKER.exists():
        return 0
    lines = MARKER.read_text().splitlines()
    seen = lines[0] if lines else ""
    reason = lines[1] if len(lines) > 1 else "the box is off"
    now = newest_result()
    if not now or not seen:
        # Cannot tell whether it is back; say nothing rather than guess in either direction.
        return 0
    if now != seen:
        MARKER.unlink(missing_ok=True)
        print(f"The box is back: it has published {now} since it was reported off. "
              f"({reason})")
        return 0
    print(reason)
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        return status()
    if args[0] == "mark":
        return mark(" ".join(args[1:]) or "the box is off")
    if args[0] == "status":
        return status()
    print(__doc__.strip().splitlines()[-3:], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
