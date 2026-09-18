#!/usr/bin/env bash
# Time the worker with no client in the way, at both sizes that matter.
#
#   ./run.sh            run it
#   ./run.sh --push     ...and commit the run to test-results/ the way the other
#                       experiments report, so the answer travels as a file
#
# Exit: 0 both sizes ran, 1 something did not, 2 a prerequisite is missing.
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

if ! command -v wine >/dev/null 2>&1; then
    echo "wine is not on PATH" >&2
    exit 2
fi

# Two sizes on purpose. The pipe's own floor at 8 bytes per pixel in and 4 back
# is ~10ms a frame at 1280x720 and ~40ms at 2560x1440, so 720p is where a slow
# worker shows up on its own and 1440p is where the pipe starts to hide it. One
# size alone cannot tell those apart.
SIZES=(1280x720 2560x1440)
FRAMES=30

run_size() {
    local size="$1" log="$2"
    "$PY" "$HERE/feed.py" --size "$size" --frames "$FRAMES" \
          --log "${log%.log}.worker.log" ${ARGS[@]+"${ARGS[@]}"} 2>&1 | tee "$log"
    return "${PIPESTATUS[0]}"
}

if [ -z "$PUSH" ]; then
    status=0
    for size in "${SIZES[@]}"; do
        echo "=== $size ==="
        run_size "$size" "/tmp/nsb_feed_${size}.log" || status=1
        echo
    done
    exit "$status"
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$REPO/test-results/${STAMP}-worker-throughput"
mkdir -p "$OUT/raw"

status=0
for size in "${SIZES[@]}"; do
    echo "=== $size ==="
    run_size "$size" "$OUT/raw/feed_${size}.log" || status=1
    echo
done

VERDICT="$(grep -h -m1 'RESULT:' "$OUT"/raw/feed_*.log | head -1 | sed 's/^ *//' || true)"
[ -n "$VERDICT" ] || VERDICT="RESULT: none — the feeder did not reach a verdict"

{
    echo "# Worker throughput, no client in the way — ${STAMP}"
    echo
    echo "**${VERDICT}**"
    echo
    echo "## What this is"
    echo
    echo "The worker fed a byte-identical stream as fast as it will take one, with"
    echo "its results discarded rather than read, so nothing in the process is"
    echo "waiting on a round trip. Every other number this project has includes"
    echo "the client's strictly serial loop — send a frame, wait for that frame —"
    echo "which is what this removes."
    echo
    echo "Each size runs twice, with N frames and 2N, and the per-frame cost is"
    echo "the difference: NGX init and shutdown are a second or two and cancel"
    echo "exactly. The stream is built with the client's own \`stream_header\` and"
    echo "\`protocol.send_frame\`, so it cannot be rejected for being a second"
    echo "implementation of the protocol."
    echo
    echo "The pipe floor is 8 bytes per pixel in (RGBA8 colour + two float16 motion"
    echo "channels) plus 4 bytes per pixel back, at the ~1.1 GB/s measured here."
    echo "That is ~10ms a frame at 720p and ~40ms at 1440p."
    echo
    for size in "${SIZES[@]}"; do
        echo "## ${size}"
        echo
        echo '```'
        grep -E 'size:|bytes per frame|frames:|derived per frame|pipe alone|floor|RESULT' \
            "$OUT/raw/feed_${size}.log" || true
        echo '```'
        echo
    done
    echo "## How to read it"
    echo
    echo "- **At the pipe's rate** → the worker keeps up with its own pipe once"
    echo "  nothing waits on it. The pipeline's 12-18fps is then the client loop,"
    echo "  not the worker, and the proven shared-file transport (~4x one way, see"
    echo "  \`experiments/mmap_bridge/\`) lifts that ceiling directly."
    echo "- **Well above the pipe's rate** → the worker is the wall. It took longer"
    echo "  than the pipe needs for the same bytes with nothing else running, so no"
    echo "  client change and no faster transport moves it; only a host we write"
    echo "  would."
    echo
    echo "Both sizes matter: 720p is where a slow worker shows up alone, 1440p is"
    echo "where the pipe starts to hide it."
    echo
    echo "Full output: \`raw/feed_*.log\`, and each run's worker stderr in"
    echo "\`raw/feed_*.worker.log\`."
} > "$OUT/report.md"

# shellcheck source=../lib/report.sh
. "$HERE/../lib/report.sh"
push_report "$OUT" "worker throughput $STAMP: $VERDICT"

if [ "$status" != 0 ]; then
    exit 1
fi
exit 0