#!/usr/bin/env bash
# Build the Windows half of the bridge test and run it under Wine.
#
#   ./run.sh                 cross-compile, then run against real Wine
#   ./run.sh --selftest      skip Wine: run the same handshake with the Python
#                            stand-in, which proves the protocol and nothing
#                            about page sharing
#   ./run.sh --rounds 20     anything else is passed to bridge_check.py
#
# Exit: 0 the pages were shared (or the selftest passed), 1 they were not,
# 2 a prerequisite is missing.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

if [ "${1:-}" = "--selftest" ]; then
    shift
    echo "selftest: the handshake with a Python stand-in for the Windows side."
    echo "It proves the layout and the protocol. It says nothing about whether"
    echo "Wine shares the pages."
    echo
    exec "$PY" "$HERE/bridge_check.py" \
        --windows-cmd "$PY $HERE/fake_windows.py {path}" "$@"
fi

CC="$(command -v x86_64-w64-mingw32-gcc || true)"
if [ -z "$CC" ]; then
    cat >&2 <<'MSG'
x86_64-w64-mingw32-gcc is not on PATH. Install the cross compiler:
  Arch:           sudo pacman -S mingw-w64-gcc
  Debian/Ubuntu:  sudo apt install gcc-mingw-w64-x86-64
MSG
    exit 2
fi

if ! command -v wine >/dev/null 2>&1; then
    echo "wine is not on PATH. Use --selftest to exercise the protocol without it." >&2
    exit 2
fi

echo "building bridge_win.exe with $CC"
"$CC" -O2 -Wall -Wextra -o "$HERE/bridge_win.exe" "$HERE/bridge_win.c"
echo

exec "$PY" "$HERE/bridge_check.py" "$@"