#!/bin/bash
# m1_pipeline_gate.sh — does a frame come out the far end changed?
#
#   tools/m1_pipeline_gate.sh                # run both variants, print the verdict
#   tools/m1_pipeline_gate.sh --out DIR      # also copy artifacts into DIR
#   tools/m1_pipeline_gate.sh --frames N     # frames to push (default 30)
#
# WHY THIS EXISTS, AND WHY IT IS NOT M0
#
# M0 (`m0_env_gate.sh`) runs `wine nvngx.dll --test`, a synthetic 640x360 loop
# written as a stand-in for having a game attached. Reading the source against it
# shows `--test` does NOT exercise the same APIs as the real pipeline:
#
#                  create                        evaluate
#   --test         g_nr_create (NR runtime)      SDK macro NGX_D3D12_EVALUATE_DLSS_EXT
#                                                 -> NVSDK_NGX_D3D12_EvaluateFeature_C
#                                                 (NGX Core), with the DLSS-SR
#                                                 NVSDK_NGX_D3D12_DLSS_Eval_Params
#   EvaluateVideo  g_nr_create (NR runtime)      g_nr_evaluate (NR runtime), with
#   (--live)                                      DLSSNR.* params, nullptr eval params
#
# So `--test` registers a handle with one runtime and evaluates it through
# another, and fails 0xBAD00004 FAIL_FeatureNotFound. The live path is the
# product: `python -m minimal` drives `wine nvngx.dll --live`.
#
# TWO VARIANTS, because capture and the pass are separate questions
#
#   pass     --source synthetic   a known test card, no screen involved
#   capture  --source screen      the real screen
#
# The split is not decoration. Measured on the RTX box: a Wayland session with
# DISPLAY=:0 hands mss the XWayland root window, which is black by definition, so
# every frame arrives empty and the pass has nothing to act on. Running only the
# screen variant cannot distinguish "NGX is not working" from "we are feeding it
# nothing" — which is exactly the round that was wasted.
#
# PASS = the MVP exits 0, both frames exist, the input was not blank, and the
#        pass measurably altered the frame.
#
# THREE VARIANTS
#
#   pass      --source synthetic   a known test card — the effect
#   baseline  --source synthetic   the same input with the effect dialled to zero
#   capture   --source auto        the real screen
#
# `baseline` is a control, not a pass/fail: every frame travels through Wine as a
# texture and back, so part of any before/after difference can be the round trip
# rather than the network. Running the same input with intensity/local_tone/
# local_structure at zero bounds that contribution, and it can then be subtracted
# before the effect numbers are read as the network's work. It is a measurement
# and is reported as one.
#
# A no-op pass exits 0 and looks perfectly healthy, which is the failure this
# gate exists to catch. tools/frame_diff.py holds that judgement and is
# separately exercisable.
#
# The before/after pair MUST come from one iteration. It did not at first: the
# pipeline kept the first captured frame against the last processed one, so on a
# test card whose only moving part is a bar the comparison measured bar motion as
# if it were the pass, reporting 48.7/255 where the real effect was 15.8/255.
# minimal/loop.py now keeps a matched pair, and
# tests/test_pipeline_mock.py::test_saved_pair_comes_from_the_same_iteration
# fails if that regresses.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

NATIVE="$REPO/native"

OUT=""
FRAMES=30
while [ $# -gt 0 ]; do
    case "$1" in
        --out)
            if [ -z "${2:-}" ]; then echo "m1_pipeline_gate.sh: --out needs a directory" >&2; exit 2; fi
            OUT="$2"; mkdir -p "$OUT"; shift 2 ;;
        --frames)
            if [ -z "${2:-}" ]; then echo "m1_pipeline_gate.sh: --frames needs a number" >&2; exit 2; fi
            FRAMES="$2"; shift 2 ;;
        -h|--help)
            cat <<'USAGE'
m1_pipeline_gate.sh — does a frame come out the far end changed?

  tools/m1_pipeline_gate.sh              run both variants, print the verdict
  tools/m1_pipeline_gate.sh --out DIR    also copy artifacts into DIR
  tools/m1_pipeline_gate.sh --frames N   frames to push (default 30)

Exit codes:  0 = both variants PASS   1 = FAIL   2 = BLOCKED

Runs the MVP end to end twice:

  pass     --source synthetic   a known test card — tests the NR pass itself
  capture  --source screen      the real screen — tests capture

and judges each pair with tools/frame_diff.py. See the header of this script for
why M0's `--test` is not a substitute for this.

For a full report (pytest + M0 + this gate + environment) use:

  tools/run_tests.sh --report --m0 --m1
USAGE
            exit 0 ;;
        *) echo "m1_pipeline_gate.sh: unknown option: $1" >&2
           echo "try: tools/m1_pipeline_gate.sh --help" >&2; exit 2 ;;
    esac
done

pass() { printf '  \033[32m✓\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✗\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }

echo "=============================================================="
echo " M1 — live pipeline gate (MVP end to end)"
echo "=============================================================="
echo ""

PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

# --- prerequisites ----------------------------------------------------------
MISSING=0
if command -v wine >/dev/null 2>&1; then
    pass "wine: $(wine --version 2>&1)"
else
    fail "wine is not installed"; MISSING=1
fi
if [ -s "$NATIVE/nvngx.dll" ]; then
    pass "worker: nvngx.dll ($(du -h "$NATIVE/nvngx.dll" | cut -f1))"
else
    fail "missing $NATIVE/nvngx.dll"; MISSING=1
fi
if [ -s "$NATIVE/nvngx_dlssnr.dll" ]; then
    pass "NR runtime: nvngx_dlssnr.dll ($(du -h "$NATIVE/nvngx_dlssnr.dll" | cut -f1))"
else
    fail "missing $NATIVE/nvngx_dlssnr.dll (gitignored, 159 MB — copy it in)"; MISSING=1
fi
if [ "$MISSING" = "1" ]; then
    echo ""
    echo "=============================================================="
    echo " RESULT: BLOCKED — fix the prerequisites above first"
    echo "=============================================================="
    exit 2
fi

T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT

# --- one variant ------------------------------------------------------------
# Sets VARIANT_STATUS: 0 = this variant behaved, 1 = it did not.
run_variant() {
    local variant="$1" source="$2" input="${3:-}" extra="${4:-}" kind="${5:-effect}"
    local dir="$T/$variant"
    mkdir -p "$dir"
    local before="$dir/before.png" after="$dir/after.png"

    echo ""
    echo "=============================================================="
    echo " variant: $variant   (--source $source${input:+ --input-image $input})"
    [ -n "$extra" ] && echo "          $extra"
    echo "=============================================================="

    local args=(--frames "$FRAMES" --headless --source "$source"
                --save-before "$before" --save-after "$after")
    [ -n "$input" ] && args+=(--input-image "$input")
    # Deliberately word-split: $extra carries several flags as one string.
    # shellcheck disable=SC2206
    [ -n "$extra" ] && args+=($extra)

    local start elapsed rc
    start=$(date +%s)
    "$PY" -m minimal "${args[@]}" > "$dir/mvp.txt" 2>&1
    rc=$?
    elapsed=$(( $(date +%s) - start ))
    sed 's/^/  | /' "$dir/mvp.txt"
    echo "  exit code: $rc   elapsed: ${elapsed}s"

    VARIANT_STATUS=0
    if [ "$rc" != "0" ]; then
        fail "the MVP exited $rc"
        VARIANT_STATUS=1
    else
        pass "the MVP exited 0"
    fi

    local missing=0 f
    for f in "$before" "$after"; do
        if [ -s "$f" ]; then
            pass "$(basename "$f") written ($(du -h "$f" | cut -f1))"
        else
            fail "$(basename "$f") was not written"
            VARIANT_STATUS=1; missing=1
        fi
    done
    [ "$missing" = "1" ] && return

    echo ""
    echo "  --- did the pass change the frame? ---"
    "$PY" tools/frame_diff.py "$before" "$after" > "$dir/analysis.txt" 2>&1
    local drc=$?
    sed 's/^/  /' "$dir/analysis.txt"

    if [ "$kind" = "control" ]; then
        # A control is a measurement, not a pass/fail. With the effect dialled
        # off, a small difference is the EXPECTED result: it bounds what the
        # transport (RGBA -> texture -> RGBA through Wine) does on its own, so
        # that number can be subtracted from the effect variants before reading
        # them as the network's work. A large one is still not a failure — it
        # means the effect variants overstate the network, and the report says so.
        local cmad
        cmad="$(grep -oP 'mean abs diff\s+\K[0-9.]+' "$dir/analysis.txt" || echo '?')"
        echo "  control variant: the diff below is the floor, not the effect"
        if awk -v m="${cmad:-99}" 'BEGIN{exit !(m < 1.0)}'; then
            pass "with the effect off the frame barely moves (mean abs diff $cmad/255)"
        else
            warn "with the effect off the frame still moves by $cmad/255 — the"
            warn "transport perturbs pixels, so subtract that from the other"
            warn "variants before reading their diff as the network's work"
        fi
    else
        case "$drc" in
            0) pass "the pass changed the frame" ;;
            *) fail "$(grep '^VERDICT' "$dir/analysis.txt" | sed 's/^VERDICT //')"
               VARIANT_STATUS=1 ;;
        esac
    fi

    # An empty INPUT is a different failure from a failed pass, and it is the one
    # that wasted a round: with a blank input the pass has nothing to act on, so
    # "the pass is broken" cannot be concluded from this variant.
    local before_blank
    before_blank="$(grep -oP 'before is blank\s+\K\w+' "$dir/analysis.txt" || echo False)"
    if [ "$before_blank" = "True" ]; then
        fail "the INPUT frame was blank — the pass had nothing to act on"
        VARIANT_STATUS=1
        if [ "$source" != "synthetic" ]; then
            cat <<'REMEDY'

     The capture returned a flat frame. Work through these in order:

     1. Run the capture on its own, with no Wine and no worker involved:

          tools/wayland_probe.py --save-frame /tmp/shot.png

        That checks the session, jeepney, GStreamer's pipewiresrc element, the
        portal, does the ScreenCast handshake and reads real frames. It is much
        faster to iterate with than this gate, and it names the step that fails.

     2. If it reports the X11 grab was used: minimal/capture.py goes through mss,
        which is X11. On a Wayland desktop the XWayland root window is black —
        applications draw on the compositor, not there — so every frame arrives
        empty. That is a capture problem and says nothing about the neural pass;
        the `pass` variant above is what answers that.

     3. Real pixels immediately, from any screenshot tool:

          grim /tmp/shot.png        # or spectacle -b -n -o /tmp/shot.png
          python -m minimal --source image --input-image /tmp/shot.png
REMEDY
        fi
    fi
}

# --- the two variants -------------------------------------------------------
run_variant pass synthetic
PASS_STATUS=$VARIANT_STATUS

# Same source, same transport, same effect settings as `pass` — only the
# resolution the network itself works at differs. This is the experiment that
# decides whether shrinking the network's workload buys frame rate on real
# hardware: if `scaled` is not meaningfully quicker than `pass`, the cost is
# not in the network and no amount of downscaling will help.
run_variant scaled synthetic "" "--work-scale 0.5"
SCALED_STATUS=$VARIANT_STATUS

# MOTS is NOT here, and the reason is worth the lines: sending the motion field
# at the flow size (320x180) hung the real worker — "silent for 60s on frame 0",
# so the worker never answered. The protocol documents MOTS as part of the
# upstream's guides path, which gets its flow size and its luminance from the
# worker's own capture (DDA/gray). A bare small field from the pipe path is not
# something the worker accepts, so the lever is closed as implemented rather
# than pending. `--motion-small` remains for the record and the wire-format
# tests; do not expect it to run.

# The control. Same source and same worker as `pass`, effect dialled to zero:
# whatever still changes is the transport, not the network. Without this, "the
# pass changed the frame" cannot distinguish the two, and the effect numbers
# would be read as the network's work when part of them is the round trip.
run_variant baseline synthetic "" \
    "--param intensity=0 --param local_tone=0 --param local_structure=0" control
BASELINE_STATUS=$VARIANT_STATUS

# NR OFF for real. `baseline` zeroes the strengths, which may still run the
# network at zero strength; this tells the worker to skip NGX entirely. The gap
# between the two rows is the network's own price, and what is left is the
# texture upload and readback that happen either way — which is the ~48ms that
# neither the network nor the pipe traffic accounts for at 1280x720.
run_variant bypass synthetic "" "--bypass" control
BYPASS_STATUS=$VARIANT_STATUS

# THE CLIENT LOOP ITSELF. Fed with no client at all, the worker does 42.5fps at
# 2560x1440 (round 29: R^2 0.9972 over 30/60/90 frames) while the pipeline does
# 9.1 — so most of a frame's cost is the client, not the worker, the transport or
# the network. This variant sends four frames ahead instead of sending one and
# waiting for it, and writes the frame buffers directly instead of copying them
# twice per frame. Compare it against `bypass14`/`pass14` for the same size.
run_variant pipeline synthetic "" "--send-ahead 4"
PIPELINE_STATUS=$VARIANT_STATUS
run_variant pipeline14 synthetic "" "--size 2560x1440 --send-ahead 4"
PIPELINE14_STATUS=$VARIANT_STATUS

# 2560x1440 WITHOUT the portal, which is the whole point of --size: the matrix
# that decomposes the expensive case costs no dialog and no capture at all.
# capturews (2560x1440 output, network at 1280x720, through the portal) came
# back at 148.0ms against capture's 139.7 — so halving the network's resolution
# did not help, and the per-pixel model that predicted ~85ms is wrong. These
# three isolate the worker from the capture at the size that matters, which is
# the only way to find out what the 139.7ms is actually made of.
run_variant pass14 synthetic "" "--size 2560x1440"
P14_STATUS=$VARIANT_STATUS
run_variant scaled14 synthetic "" "--size 2560x1440 --work-scale 0.5"
S14_STATUS=$VARIANT_STATUS
run_variant bypass14 synthetic "" "--size 2560x1440 --bypass" control
B14_STATUS=$VARIANT_STATUS

# IS THE CLIENT'S OWN PRESENT PACING US?
#
# With the test card fixed (it was rebuilding 100MB of float32 temporaries per
# grab, 42.7ms at 1440p) the numbers settled into a shape: `send` is ~45ms per
# frame and does not care about the frame's size — 45.3ms for 64KB in bypass128,
# 55.4ms for 14.7MB in bypass14 — while the worker fed by a harness with no client
# does 23.5ms at 1440p and under 4ms at 720p. And the totals cluster near 20fps
# (bypass128 21.9, bypass 20.0).
#
# Our own write path is not it: measured directly it is 14.14ms for a 1440p frame
# and ~0 for 64KB. So the worker is being paced by something that only exists when
# the real client drives it, and the one thing the pipeline does per frame that a
# harness does not is PRESENT TO A WINDOW. SDL's swap can block on the compositor's
# frame callback, which on a 60Hz output would put frames on the third vsync —
# ~50ms, and 20fps.
#
# These two variants are the same work with --headless (no window, no present). If
# they collapse to the worker's own rate, the pipeline's ceiling is our own vsync
# and the fix is in the display path, not in the worker, the transport or the loop.
run_variant headless synthetic "" "--bypass --headless" control
HEADLESS_STATUS=$VARIANT_STATUS
run_variant headless14 synthetic "" "--size 2560x1440 --bypass --headless" control
HEADLESS14_STATUS=$VARIANT_STATUS

# ONE WRITE PER FRAME INSTEAD OF FOUR.
#
# With both clocks now printed, the shape is unmistakable: our loop pays a fixed
# ~45ms a frame in `send` at EVERY size, while the worker's own timestamps say it
# delivers a 64KB frame in 0.21ms. bypass128 is 46.7ms a frame against a worker
# that is 4762fps; bypass is 55.2ms against 78fps; bypass14 is 89.6ms against
# 23fps. Same ~45ms every time, and it is not the bytes, the reader, the display,
# the capture or the worker's frames.
#
# What is left is our own send path blocking. It issues four writes per frame
# (header, colour, motion, flush) and each can block on a full pipe waiting for
# the worker to drain it — and the worker polls its pipe with Sleep(8) between
# attempts, which under Wine's timer granularity can be ~16ms a poll. A few of
# those per frame is 45ms.
#
# These variants hand the kernel every part of a frame in ONE writev. If `send`
# collapses toward the worker's own number, the per-write blocking was the cost
# and the fix is ours. If it does not move, the cost is the worker's poll latency
# and only a host that blocks on its read instead of polling can remove it.
run_variant writev synthetic "" "--bypass --writev" control
WRITEV_STATUS=$VARIANT_STATUS
run_variant writev14 synthetic "" "--size 2560x1440 --bypass --writev" control
WRITEV14_STATUS=$VARIANT_STATUS

# A SIZE SWEEP, to split the frame's cost into the part that scales with bytes
# and the part that does not. Only the first part is something a different
# transport can remove; the second is the worker's own per-frame work and would
# survive any transport at all. bypass (1280x720) and bypass14 (2560x1440) give
# two points, and a line through two points fits anything — round 21's note that
# "~48ms at 1280x720 is neither the network nor the pipe traffic" came from
# exactly that kind of two-point reasoning and has never been tested against a
# third size. These add two, both small enough that the bytes barely matter, so
# the intercept is nearly readable directly off the smallest one.
run_variant bypass128 synthetic "" "--size 128x128 --bypass" control
B128_STATUS=$VARIANT_STATUS
run_variant bypass360 synthetic "" "--size 640x360 --bypass" control
B360_STATUS=$VARIANT_STATUS

# "auto" is what the product does: the portal on a Wayland session, the X11 grab
# otherwise. Naming it explicitly here means the gate tests the same decision the
# user's own runs go through.
run_variant capture auto
CAPTURE_STATUS=$VARIANT_STATUS

# The capture chain's CPU is the one cost so far that sits in our own code: 33%
# of a core at 2560x1440, about 42ms of CPU per frame, which is the same order as
# the 18-47ms the worker's `send` pays extra when the source is the portal. This
# variant drops the videoscale element, one 14.7MB pass out of the chain, so the
# `capture cpu:` line and `send` can be compared against `capture` in one run.
run_variant capturens auto "" "--capture-no-scale"
CAPTURENS_STATUS=$VARIANT_STATUS

# --- environment ------------------------------------------------------------
echo ""
echo "--- environment ---"
echo "  DISPLAY:           ${DISPLAY:-<unset>}"
echo "  WAYLAND_DISPLAY:   ${WAYLAND_DISPLAY:-<unset>}"
echo "  XDG_SESSION_TYPE:  ${XDG_SESSION_TYPE:-<unset>}"
if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
    warn "Wayland session: the screen variant is expected to capture nothing"
    warn "(the worker does not write dlss5-feed-host.log in --live mode; that is"
    warn " deliberate — 'if (!g_video_mode)' in dlss5-feed-host64.cpp, so its"
    warn " absence is not a failure here)"
fi

# --- copy artifacts out -----------------------------------------------------
if [ -n "$OUT" ]; then
    for v in pass scaled baseline bypass pipeline pipeline14 pass14 scaled14 bypass14 headless headless14 writev writev14 bypass128 bypass360 capture capturens; do
        mkdir -p "$OUT/$v"
        cp -f "$T/$v/before.png" "$OUT/$v/" 2>/dev/null || true
        cp -f "$T/$v/after.png" "$OUT/$v/" 2>/dev/null || true
        cp -f "$T/$v/mvp.txt" "$OUT/$v/" 2>/dev/null || true
        cp -f "$T/$v/analysis.txt" "$OUT/$v/" 2>/dev/null || true
    done
    {
        echo "date:              $(date -u)"
        echo "XDG_SESSION_TYPE:  ${XDG_SESSION_TYPE:-}"
        echo "XDG_CURRENT_DESKTOP: ${XDG_CURRENT_DESKTOP:-}"
        echo "DISPLAY:           ${DISPLAY:-}"
        echo "WAYLAND_DISPLAY:   ${WAYLAND_DISPLAY:-}"
        echo "frames pushed:     $FRAMES"
        echo "wine:              $(wine --version 2>&1)"
        echo "driver:            $(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>&1 | head -1)"
    } > "$OUT/m1_environment.txt" 2>&1
    echo ""
    echo "  artifacts -> $OUT/{pass,scaled,baseline,bypass,pass14,scaled14,bypass14,capture,capturens}/"
fi

# --- summary ----------------------------------------------------------------
STATUS=0
[ "$PASS_STATUS" != "0" ] && STATUS=1

echo ""
echo "=============================================================="
echo " M1 summary"
echo "=============================================================="
if [ "$PASS_STATUS" = "0" ]; then
    echo "  pass     PASS — the NR pass changes a known frame."
else
    echo "  pass     FAIL — the pass did not change a known frame."
fi
if [ "$BASELINE_STATUS" = "0" ]; then
    echo "  baseline measured — see the variant output for the transport floor;"
    echo "           subtract it from 'pass' and 'capture' before reading those"
    echo "           as the network's work."
else
    echo "  baseline FAIL — the control run did not complete."
    STATUS=1
fi
if [ "$BYPASS_STATUS" = "0" ]; then
    echo "  bypass   measured — NGX skipped entirely. baseline minus bypass is"
    echo "           the network's own price; what bypass still costs is the"
    echo "           texture upload and readback, which no strength setting"
    echo "           touches."
else
    echo "  bypass   FAIL — the no-NGX control did not complete."
    STATUS=1
fi
if [ "$CAPTURE_STATUS" = "0" ]; then
    echo "  capture  PASS — a real screen frame comes through."
else
    echo "  capture  FAIL — no usable screen frame (see the variant output)."
fi
if [ "$CAPTURENS_STATUS" = "0" ]; then
    echo "  capturens measured — the same capture with videoscale dropped."
    echo "            Compare its 'capture cpu:' line and its send against"
    echo "            'capture'. The chain was 33% of a core (about 42ms of CPU"
    echo "            per frame) and send was 18-47ms worse through the portal"
    echo "            than synthetically; if both fall, the contention was real"
    echo "            and it is our element to delete."
else
    echo "  capturens FAIL — caps negotiation may have refused without"
    echo "            videoscale (the portal's size and the stream's disagreeing"
    echo "            is the known way); read the variant output above."
fi
if [ "$P14_STATUS" != "0" ] || [ "$S14_STATUS" != "0" ] || [ "$B14_STATUS" != "0" ]; then
    echo "  the 2560x1440 synthetic trio did not all complete."
    STATUS=1
fi
if [ "$B128_STATUS" != "0" ] || [ "$B360_STATUS" != "0" ]; then
    echo "  the small end of the size sweep did not complete. That is itself a"
    echo "  reading: it would mean the worker refuses frames that small, and the"
    echo "  intercept has to be extrapolated up from 1280x720 instead."
fi
echo ""
echo "  the size sweep — fit bypass128, bypass360, bypass (1280x720) and bypass14"
echo "  (2560x1440) as ms/frame against bytes/frame:"
echo "    the SLOPE is the part of the journey that a different transport could"
echo "    remove. The INTERCEPT is the worker's own per-frame work, and no"
echo "    transport touches it."
echo "    for scale, the pipe measures ~1.1 GB/s and a frame crosses it three"
echo "    times in this loop (our write, the worker's read, our read of the"
echo "    result), so a purely byte-bound journey would slope at about 2.7ms per"
echo "    MB: 14.7MB would be ~40ms of pipe traffic, and 128x128 (64KB) would be"
echo "    nearly zero. A large intercept means an own-host build cannot pay for"
echo "    itself, and that the ceiling is not the transport at all."
echo ""
echo "  per-frame cost by variant — the point of the run:"
for v in pass scaled baseline bypass pipeline pipeline14 pass14 scaled14 bypass14 headless headless14 writev writev14 bypass128 bypass360 capture capturens; do
    line=$(grep -m1 '^timing:' "$T/$v/mvp.txt" 2>/dev/null || true)
    printf '    %-9s %s\n' "$v" "${line:-<no timing recorded>}"
    # Both clocks for the same run, plus the spread. The worker's timestamps know
    # nothing of our timing, so a disagreement between the two lines is what says
    # the timing line is wrong — and a steady send against a spiky one means
    # something completely different.
    clock=$(grep -m1 '^worker clock:' "$T/$v/mvp.txt" 2>/dev/null || true)
    [ -n "$clock" ] && printf '    %-9s %s\n' "" "$clock"
    spread=$(grep -m1 '^send spread:' "$T/$v/mvp.txt" 2>/dev/null || true)
    [ -n "$spread" ] && printf '    %-9s %s\n' "" "$spread"
    wstall=$(grep -m1 '^worker stall:' "$T/$v/mvp.txt" 2>/dev/null || true)
    [ -n "$wstall" ] && printf '    %-9s %s\n' "" "$wstall"
    # The capture leg's own split, which is the number that decides whether the
    # portal is the ceiling or we are.
    split=$(grep -m1 '^capture split:' "$T/$v/mvp.txt" 2>/dev/null || true)
    [ -n "$split" ] && printf '    %-9s %s\n' "" "$split"
    # The producer's wait is bimodal: 0-21ms normally, 225-303ms in some runs
    # (two of the seven recorded so far). When it is the slow mode the variant's
    # total is not a measurement of anything except that, so say so rather than
    # let it be read as the pass being slower.
    if [ -n "$split" ]; then
        wait_ms=$(echo "$split" | grep -oE 'wait [0-9.]+' | grep -oE '[0-9.]+')
        if [ -n "$wait_ms" ] && awk -v w="$wait_ms" 'BEGIN{exit !(w > 100)}'; then
            echo "              ! PRODUCER IN SLOW MODE (${wait_ms}ms waiting for"
            echo "                frames, against 0-21ms normally). This variant's"
            echo "                total is not a measurement. The copy is always"
            echo "                10-15ms, so it is never our end of the grab."
        fi
    fi
done
echo ""
echo "  Read the split, not just the fps. What the box has measured so far:"
echo "    pass      82.0ms   the reference: effect on, full work resolution"
echo "    scaled    57.6ms   -30%, but it changes TWO things at once: the"
echo "                       network's resolution and the size of the motion"
echo "                       field, which travels at the work resolution. So it"
echo "                       does not say which of the two paid."
echo "    baseline  57.9ms   the effect dialled to zero, same bytes as pass."
echo "                       Almost exactly scaled's total: turning the effect"
echo "                       off and quartering the network are worth the same"
echo "                       ~24ms, which is what a cost sitting in the worker's"
echo "                       per-frame work and in the bytes both look like."
echo "    bypass    ?        NGX skipped outright. If baseline and bypass land"
echo "                       close together then zeroing the strengths was still"
echo "                       running the network, and the worker's cost is in the"
echo "                       texture path; if bypass is much cheaper, the network"
echo "                       is worth more than its measured arithmetic (1.5ms +"
echo "                       1.51ms/Mpixel is ~2.9ms at 1280x720)."
echo "    capture  520.0ms   the portal's OWN leg was 375ms of it at 2560x1440."
echo "                       Nothing downstream can beat the rate the compositor"
echo "                       hands frames over, so measure that on its own with:"
echo "                         tools/wayland_probe.py --frames 20"
echo ""
echo "  The isolating experiment (MOTS: same zeros, sent at the flow size) is not"
echo "  in this list because the worker does not accept it from the pipe path —"
echo "  it goes silent on frame 0. See the note above it."
echo ""
echo "  The artifact that decides the milestone is pass/after.png next to"
echo "  pass/before.png — look at them. A pair of numbers can agree on a"
echo "  flat frame, which is how the last round looked healthy."
echo ""
if [ "$STATUS" = "0" ]; then
    echo " RESULT: PASS — capture -> DLSS5 NR pass -> display works."
else
    echo " RESULT: FAIL — see the failing variant above."
    echo " 'pass' failing is about NGX. 'capture' failing is about the desktop."
fi
echo "=============================================================="
exit "$STATUS"
