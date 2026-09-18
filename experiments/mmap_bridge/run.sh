#!/usr/bin/env bash
# Build the Windows half of the bridge test and run it under Wine.
#
#   ./run.sh                 cross-compile, then run against real Wine
#   ./run.sh --push          ...and commit the run to test-results/ the way the
#                            delivery gate reports, so the answer travels as
#                            files instead of a pasted terminal
#   ./run.sh --selftest      skip Wine: the same handshake with the Python
#                            stand-in, which proves the protocol and nothing
#                            about page sharing (and says so in its own result)
#   ./run.sh --rounds 20     anything else is passed to bridge_check.py
#
# --push writes the run to test-results/<UTC>-mmap-bridge/ (report plus the raw
# log) and pushes it via ../lib/report.sh, which owns the auth convention and the
# honest failure messages for both experiments.
#
# Exit: 0 the pages were shared, 1 they were not, 2 a prerequisite is missing.
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

# selftest is consumed here rather than passed through, because it changes which
# process is on the other side.
SELFTEST=0
REST=()
for a in ${ARGS[@]+"${ARGS[@]}"}; do
    case "$a" in
        --selftest) SELFTEST=1 ;;
        *)          REST+=("$a") ;;
    esac
done
ARGS=(${REST[@]+"${REST[@]}"})

if [ "$SELFTEST" = 1 ]; then
    echo "selftest: the handshake with a Python stand-in for the Windows side."
    echo "It proves the layout and the protocol. It says nothing about whether"
    echo "Wine shares the pages, and the result will say so."
    echo
    set -- --windows-cmd "$PY $HERE/fake_windows.py {path}"
else
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
    set --
fi

set -- "$@" ${ARGS[@]+"${ARGS[@]}"}

if [ -z "$PUSH" ]; then
    exec "$PY" "$HERE/bridge_check.py" "$@"
fi

# --push: keep the run. This one decides whether a host gets built, so an
# unwritten report is a report that gets asked for twice.
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if [ "$SELFTEST" = 1 ]; then
    # The directory name has to carry this, or a stand-in run sits in
    # test-results/ looking exactly like a result from the box.
    SUFFIX="-mmap-bridge-selftest"
else
    SUFFIX="-mmap-bridge"
fi
OUT="$REPO/test-results/${STAMP}${SUFFIX}"
mkdir -p "$OUT/raw"
LOG="$OUT/raw/bridge_check.log"

set +e
"$PY" "$HERE/bridge_check.py" "$@" 2>&1 | tee "$LOG"
RC="${PIPESTATUS[0]}"
set -e

VERDICT="$(grep -m1 'RESULT:' "$LOG" | sed 's/^ *//' || true)"
[ -n "$VERDICT" ] || VERDICT="RESULT: none — the run did not reach a verdict"

{
    echo "# mmap bridge test — ${STAMP}"
    echo
    echo "**${VERDICT}**"
    echo
    if [ "$SELFTEST" = 1 ]; then
        echo "**Not a box result.** This run used the Python stand-in for the"
        echo "Windows side, not Wine. It proves the harness works end to end and"
        echo "says nothing about page sharing across the Wine boundary."
        echo
    fi
    if grep -q 'written and returned' "$LOG"; then
        echo "## Transport"
        echo
        echo '```'
        grep -E 'written and returned|our own write|for scale' "$LOG" || true
        echo '```'
        echo
    fi
    echo "## How to read it"
    echo
    echo "- Ran \`experiments/mmap_bridge/run.sh\` on the box that has Wine."
    echo "- Each side fills the payload with its own byte and verifies *every* byte"
    echo "  the other wrote, so a pass is a coherence claim, not a liveness check."
    echo "- Wine's \`map_file_into_view\` maps a writable file-backed view with"
    echo "  \`mmap(fd, MAP_SHARED)\` — the same page cache native Linux uses — so a"
    echo "  pass is the expected result, and a failure arrives named by Wine's own"
    echo "  error strings rather than as a silent private copy."
    echo "- \`--flush\` was off: an msync per round forces writeback and overstated an"
    echo "  earlier round trip by 4x."
    echo
    echo "Full output, including which process was on the other side:"
    echo "\`raw/bridge_check.log\`."
} > "$OUT/report.md"

# shellcheck source=../lib/report.sh
. "$HERE/../lib/report.sh"
push_report "$OUT" "mmap bridge result $STAMP: $VERDICT" \
    "$(grep -E 'written and returned|our own write' "$LOG" || true)"

exit "$RC"