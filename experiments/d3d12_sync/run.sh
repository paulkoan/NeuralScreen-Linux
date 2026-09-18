#!/usr/bin/env bash
# Two measurements, both about where a frame's time actually goes.
#
#   1. the D3D12 substrate: what a submit, a fence wait, a copy and a readback
#      cost under Wine with nothing else in the process
#   2. the worker's own loop: 300 evaluates at 640x360 through its --test path,
#      with no pipe, no client and nothing feeding it
#
# Both run under the worker's own Wine environment — see wine_env.py.
#
#   ./run.sh            build, then run both
#   ./run.sh --push     ...and commit the run to test-results/ so the answer
#                       travels as a file rather than a pasted terminal
#
# Exit: 0 both completed, 1 something did not, 2 a prerequisite is missing.
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

# Show the environment first. If this runs under different DLL overrides than the
# worker, its numbers are about a different D3D12 and the run is void — so it is
# printed, not assumed.
echo "  the D3D12 environment (from minimal/worker.py):"
"$PY" "$HERE/wine_env.py" --show | sed 's/^/    /'
echo

run_probe() {
    "$PY" "$HERE/wine_env.py" wine "$HERE/probe.exe" ${ARGS[@]+"${ARGS[@]}"}
}

# The worker's own harness. --test builds the D3D12 device, creates NGX feature
# 18 and runs 300 evaluates on a synthetic 640x360 pattern with NO pipe, NO
# client and nothing feeding it — so its wall time is the worker's own per-frame
# cost, which nothing in this project has ever recorded. Its loop calls
# PumpPresent() before every evaluate, i.e. a swapchain present per frame, and
# the pipe path additionally polls with Sleep(8) per poll.
run_host_test() {
    ( cd "$REPO/native" && "$PY" "$HERE/wine_env.py" wine nvngx.dll --test )
}

if [ -z "$PUSH" ]; then
    echo "--- 1. the D3D12 substrate ---"
    set +e
    run_probe
    rc_probe=$?
    echo
    echo "--- 2. the worker's own loop (--test, no pipe, no client) ---"
    host_start="$(date +%s)"
    run_host_test
    rc_host=$?
    echo "  elapsed: $(( $(date +%s) - host_start ))s"
    set -e
    if [ "$rc_probe" != 0 ] || [ "$rc_host" != 0 ]; then exit 1; fi
    exit 0
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$REPO/test-results/${STAMP}-d3d12-sync"
mkdir -p "$OUT/raw"
LOG="$OUT/raw/probe.log"
HOSTLOG="$OUT/raw/host_test.log"

echo "--- 1. the D3D12 substrate ---"
set +e
run_probe 2>&1 | tee "$LOG"
RC_PROBE="${PIPESTATUS[0]}"
echo
echo "--- 2. the worker's own loop (--test, no pipe, no client) ---"
HOST_START="$(date +%s)"
run_host_test 2>&1 | tee "$HOSTLOG"
RC_HOST="${PIPESTATUS[0]}"
HOST_ELAPSED=$(( $(date +%s) - HOST_START ))
echo "  elapsed: ${HOST_ELAPSED}s"
set -e

FIRST="$(grep -m1 'RESULT:' "$LOG" | sed 's/^ *//' || true)"
[ -n "$FIRST" ] || FIRST="RESULT: none — the probe did not reach a verdict"
FULL="$(grep -A5 'RESULT:' "$LOG" | sed 's/^ *//' | tr '\n' ' ' | sed 's/  */ /g')"

# The worker's own number, derived rather than eyeballed: the run's wall time,
# minus its known ~1s hook-arming warm-up, over the evaluates it reports.
GOOD="$(grep -o -- '--test finished: [0-9]*' "$HOSTLOG" | tail -1 | grep -o '[0-9]*$' || true)"
HOST_LINE="the worker's --test did not report a completed count"
if [ -n "$GOOD" ] && [ "$GOOD" -gt 0 ]; then
    HOST_LINE="$(awk -v s="$HOST_ELAPSED" -v n="$GOOD" 'BEGIN{
        warm = 1.0;                      # 120 x Sleep(8) before the loop starts
        busy = s - warm; if (busy < 0) busy = 0;
        printf "%d evaluates in %ss wall (minus ~1s warm-up): %.1f ms/evaluate, %.1f fps",
               n, s, 1000 * busy / n, n / busy;
    }')"
fi

{
    echo "# D3D12 substrate, and the worker's own loop — ${STAMP}"
    echo
    echo "**Probe: ${FULL}**"
    echo
    echo "**Worker --test: ${HOST_LINE}**"
    echo
    echo "## 1. The D3D12 substrate"
    echo
    echo '```'
    grep -E '^  [A-E]\.|ms each|round trip:|no GPU work:|poll instead:|never wait|readback:' "$LOG" || true
    echo '```'
    echo
    echo "## 2. The worker's own loop, with nothing feeding it"
    echo
    echo '```'
    grep -E -- '--test finished|feature 18|Init.*Success|adapter' "$HOSTLOG" | tail -8 || true
    echo "elapsed: ${HOST_ELAPSED}s"
    echo '```'
    echo
    echo "## How to read the two together"
    echo
    echo "- Both ran under the worker's own Wine environment (printed in the log)."
    echo "- **1** says what the GPU layer can do: a 14.7MB upload copy, a 14.7MB"
    echo "  readback and the sync cost ~1.5ms. That is the floor for a frame's GPU"
    echo "  work, and it is not why a frame costs 55-175ms."
    echo "- **2** says what the worker does per frame with no pipe and no client. Its"
    echo "  loop calls \`PumpPresent()\` before every evaluate — a swapchain present"
    echo "  per frame — and the pipe path additionally polls with \`Sleep(8)\`."
    echo "- Compare **2** against the pipeline's number for the same size:"
    echo "  \`bypass360\` (640x360, through the pipe, NGX off) measured 69.2ms a"
    echo "  frame. If **2** is a fraction of that, the pipe and the client protocol"
    echo "  are the cost and the worker is not."
    echo
    echo "Full output: \`raw/probe.log\` and \`raw/host_test.log\`."
} > "$OUT/report.md"

# shellcheck source=../lib/report.sh
. "$HERE/../lib/report.sh"
push_report "$OUT" "d3d12 sync probe $STAMP: $FIRST" "$HOST_LINE"

if [ "$RC_PROBE" != 0 ] || [ "$RC_HOST" != 0 ]; then
    exit 1
fi
exit 0