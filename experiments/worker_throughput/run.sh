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
    shift 2
    "$PY" "$HERE/feed.py" --size "$size" --frames "$FRAMES" \
          --log "${log%.log}.worker.log" "$@" ${ARGS[@]+"${ARGS[@]}"} 2>&1 | tee "$log"
    return "${PIPESTATUS[0]}"
}

if [ -z "$PUSH" ]; then
    status=0
    for size in "${SIZES[@]}"; do
        echo "=== $size, results discarded ==="
        run_size "$size" "/tmp/nsb_feed_${size}_discard.log" || status=1
        echo
        echo "=== $size, results read the way the client reads them ==="
        run_size "$size" "/tmp/nsb_feed_${size}_read.log" --read-results || status=1
        echo
    done
    exit "$status"
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$REPO/test-results/${STAMP}-worker-throughput"
mkdir -p "$OUT/raw"

status=0
for size in "${SIZES[@]}"; do
    echo "=== $size, results discarded ==="
    run_size "$size" "$OUT/raw/feed_${size}_discard.log" || status=1
    echo
    echo "=== $size, results read the way the client reads them ==="
    run_size "$size" "$OUT/raw/feed_${size}_read.log" --read-results || status=1
    echo
done

# --- the gap test ------------------------------------------------------------
#
# THE ONE THING THIS HARNESS HAS NEVER DONE: leave a gap between frames.
#
# The pipeline now prints the worker's own clock next to its own timing line, and
# the shape it shows is a fixed ~40ms a frame in `send` at EVERY frame size:
# bypass128 is 38.4ms for a 128KB frame while the worker's own timestamps say it
# delivered in 0.17ms, and `writev` — one scatter-gather write instead of four —
# changed nothing (39.9 -> 40.8ms at 720p). So it is not our syscall shape.
#
# This harness pays none of it, because it feeds frames back to back and the
# worker is never idle. The pipeline always leaves a gap: capture, display and
# its own bookkeeping happen between frames. So the candidate is the gap itself —
# the worker drops into its poll loop, and under Wine a Sleep(8) can cost a whole
# timer tick.
#
# 720p, results read (as close to the client as this gets), gap 0 and gap 20ms.
# The fit necessarily contains the gap we put there; feed.py prints the
# remainder, and the remainder is what decides it. If the worker's own share
# jumps toward 40ms when it is given a gap, the poll is our fixed cost and only a
# host that blocks on its read removes it. If the remainder barely moves from the
# no-gap number, the poll is harmless and the fixed cost is somewhere in the
# client still.
echo
echo "=== the gap test: 720p, results read ==="
for gap in 0 20; do
    echo "--- ${gap}ms gap after every frame"
    "$PY" "$HERE/feed.py" --size 1280x720 --frames 25 --read-results \
        --gap-ms "$gap" --log "$OUT/raw/feed_gap${gap}.worker.log" \
        > "$OUT/raw/feed_gap${gap}.log" 2>&1 || true
    grep -E 'fit over|own share|worker.s own log|our clock|RESULT' \
        "$OUT/raw/feed_gap${gap}.log" || true
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
    echo "Each size runs a discarded warm-up pass first, then N, 2N and 3N frames."
    echo "The per-frame cost is the slope of a least-squares fit through those three"
    echo "points; the intercept is the startup. Three points rather than two because"
    echo "a line through two points fits anything — and because the first version of"
    echo "this used two, and the cold wineserver start landed on one of them: 60"
    echo "frames came in faster than 30, which is impossible. The fit's R^2 and"
    echo "residuals are printed, and a poor fit is refused rather than quoted."
    echo
    echo "The pipe floor is measured on this box in the same run, not assumed: 8"
    echo "bytes per pixel in (RGBA8 colour plus two float16 motion channels) and 4"
    echo "bytes per pixel back."
    echo
    for size in "${SIZES[@]}"; do
        for pass in discard read; do
            if [ "$pass" = "read" ]; then
                label="results READ like the client reads them"
            else
                label="results DISCARDED (/dev/null)"
            fi
            echo "## ${size} — ${label}"
            echo
            echo '```'
            grep -E 'size:|bytes per frame|pipe rate|warm-up|frames:|worker.s own log|our clock|fit over|off by|bytes alone|this is|RESULT' \
                "$OUT/raw/feed_${size}_${pass}.log" || true
            echo '```'
            echo
        done
    done
    echo "## The gap test"
    echo
    echo '```'
    for gap in 0 20; do
        echo "--- ${gap}ms gap after every frame"
        grep -E 'fit over|own share|worker.s own log|RESULT' \
            "$OUT/raw/feed_gap${gap}.log" || true
        echo
    done
    echo '```'
    echo
    echo "One thing this harness has never done is leave a gap between frames, and"
    echo "the pipeline always leaves one. Feed frames back to back and the worker is"
    echo "never idle; give it 20ms and it drops into its poll loop between frames,"
    echo "which under Wine can cost a whole timer tick per attempt. The fit contains"
    echo "the gap we put there, so \`feed.py\` prints the remainder — the worker's own"
    echo "share — and that remainder is what decides whether the fixed ~40ms our loop"
    echo "pays is the worker's poll or something in us."
    echo
    echo "## The comparison this run exists for"
    echo
    echo "Each size runs twice: once with the worker's results discarded, once with"
    echo "them read the way the pipeline reads them — its own \`WorkerReader\` on its"
    echo "own thread, in index order, display skipped. Everything else is identical:"
    echo "the same stream, the same sizes, the same three-point fit."
    echo
    echo "The pipeline reports ~45ms a frame in \`send\` while this harness — with"
    echo "results discarded — says the same worker does 23.5ms at 1440p and under"
    echo "4ms at 720p. Reading the results is the one thing the pipeline does per"
    echo "frame that the harness did not do, so if the READ pass is far slower than"
    echo "the DISCARD pass, the pacing is in our own result path."
    echo
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