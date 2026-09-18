"""How much CPU a process has used — one implementation, two callers.

The probe reports the capture chain's CPU share to explain contention, and the
MVP reports the same thing for its own run so it lands in a test report instead
of needing a separate command. Two copies of this would drift, which is the
lesson this repo keeps relearning about the worker's launch environment.
"""

from __future__ import annotations

import os


def process_cpu_seconds(pid: int | None) -> float | None:
    """CPU time a process has used, in seconds (utime + stime).

    Returns None if the process is gone or /proc is unreadable, so a caller can
    report "unknown" rather than a fabricated zero — a made-up 0 would read as
    "the pipeline is doing nothing", which is the opposite of the interesting
    case.

    Field 2 of /proc/<pid>/stat is the command name in parentheses and may
    itself contain spaces, so the fields after it are counted from the last ')'
    rather than from a whitespace split of the whole line. utime/stime are
    fields 14 and 15, i.e. indices 11 and 12 once state (field 3) leads.
    """
    if pid is None:
        return None
    try:
        with open(f"/proc/{pid}/stat", "rb") as fh:
            raw = fh.read()
        rest = raw[raw.rfind(b")") + 2:].split()
        utime, stime = int(rest[11]), int(rest[12])
        return (utime + stime) / os.sysconf("SC_CLK_TCK")
    except Exception:
        return None


def cpu_share(before: float | None, after: float | None,
              wall_seconds: float) -> float | None:
    """The fraction of one core used between two samples, or None if unknown."""
    if before is None or after is None or wall_seconds <= 0:
        return None
    return (after - before) / wall_seconds
