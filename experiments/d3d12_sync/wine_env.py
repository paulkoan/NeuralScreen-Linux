#!/usr/bin/env python3
"""Run a command under the worker's own Wine environment.

The probe has to measure the stack the worker actually uses — vkd3d-proton's
d3d12/dxgi rather than Wine's builtins, in the same prefix, with the same NVAPI
setting — or it measures something else and the numbers mean nothing. Rather than
restate those variables here and let them drift away from minimal/worker.py, this
imports the function that already knows them: worker_env() is the single source of
truth for the worker's launch environment, and a test checks that nothing in this
directory hardcodes a second copy.

    wine_env.py wine ./probe.exe     run a command with that environment
    wine_env.py --show               print the environment it would use
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from minimal.worker import worker_env  # noqa: E402

SHOWN = ("WINEPREFIX", "WINEDLLOVERRIDES", "DXVK_ENABLE_NVAPI")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: wine_env.py <command> [args...]", file=sys.stderr)
        print("       wine_env.py --show", file=sys.stderr)
        return 2

    env = worker_env()

    if argv[1] == "--show":
        for key in SHOWN:
            print(f"{key}={env.get(key, '<unset>')}")
        return 0

    try:
        return subprocess.call(argv[1:], env=env)
    except FileNotFoundError as exc:
        print(f"wine_env: cannot run {argv[1]!r}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
