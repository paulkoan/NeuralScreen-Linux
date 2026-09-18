#!/usr/bin/env bash
# Build the D3D12 sync probe and run it under the worker's own Wine environment.
#
#   ./run.sh            build, then run
#   ./run.sh --push     ...and commit the run to test-results/ so the answer
#                       travels as a file rather than a pasted terminal
#
# Exit: 0 the probe completed, 1 it did not, 2 a prerequisite is missing.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

PUSH=""
ARGS=()
for a in "$@"; do
    case "$a" in
        --push) PUSH=1 ;;
        *)      ARGS+=("$a") ;;
    esac
done

CXX="$(command -v x86_64-w64-mingw32-g++ || true)"
if [ -z "$CXX" ]; then
    cat >&2 <<'MSG'
x86_64-w64-mingw32-g++ is not on PATH. Install the cross compiler:
  Arch:           sudo pacman -S mingw-w64-gcc
  Debian/Ubuntu:  sudo apt install g++-mingw-w64-x86-64
MSG
    exit 2
fi

if ! command -v wine >/dev/null 2>&1; then
    echo "wine is not on PATH" >&2
    exit 2
fi

echo "building probe.exe with $CXX"
"$CXX" -O2 -Wall -o "$HERE/probe.exe" "$HERE/probe.cpp" -ld3d12 -ldxgi -luuid
echo

# Show the environment first. If this probe runs under different DLL overrides
# than the worker, its numbers are about a different D3D12 and the run is void —
# so it is printed, not assumed.
echo "  the D3D12 environment it will run in (from minimal/worker.py):"
"$PY" "$HERE/wine_env.py" --show | sed 's/^/    /'
echo

if [ -z "$PUSH" ]; then
    exec "$PY" "$HERE/wine_env.py" wine "$HERE/probe.exe" ${ARGS[@]+"${ARGS[@]}"}
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$REPO/test-results/${STAMP}-d3d12-sync"
mkdir -p "$OUT/raw"
LOG="$OUT/raw/probe.log"

set +e
"$PY" "$HERE/wine_env.py" wine "$HERE/probe.exe" ${ARGS[@]+"${ARGS[@]}"} 2>&1 | tee "$LOG"
RC="${PIPESTATUS[0]}"
set -e

FIRST="$(grep -m1 'RESULT:' "$LOG" | sed 's/^ *//' || true)"
[ -n "$FIRST" ] || FIRST="RESULT: none — the probe did not reach a verdict"
FULL="$(grep -A5 'RESULT:' "$LOG" | sed 's/^ *//' | tr '\n' ' ' | sed 's/  */ /g')"

{
    echo "# D3D12 sync probe — ${STAMP}"
    echo
    echo "**${FULL}**"
    echo
    echo "## What it measured"
    echo
    echo '```'
    grep -E '^  [A-E]\.|ms each|round trip:|no GPU work:|poll instead:|never wait|readback:' "$LOG" || true
    echo '```'
    echo
    echo "## How to read it"
    echo
    echo "- Ran \`experiments/d3d12_sync/run.sh\` on the box with the GPU, under the"
    echo "  same Wine environment the worker gets (printed in the log)."
    echo "- Headless on purpose: no window, no swapchain, no NGX, no pipe. A window"
    echo "  would measure DXVK's present path instead of the synchronisation."
    echo "- The discriminator is **B**, the wait on an already-complete fence with no"
    echo "  GPU work outstanding. Whatever that costs is paid by every wait, whoever"
    echo "  wrote the host, so it is the part that is not ours to fix."
    echo "- Context: the pipeline spends ~55ms per frame with NGX off at *any* size"
    echo "  (a 64KB frame cost 64.5ms, a 3.7MB frame 54.9ms), so the cost is not the"
    echo "  bytes and not the network."
    echo
    echo "Full output: \`raw/probe.log\`."
} > "$OUT/report.md"

# shellcheck source=../lib/report.sh
. "$HERE/../lib/report.sh"
push_report "$OUT" "d3d12 sync probe $STAMP: $FIRST"

exit "$RC"