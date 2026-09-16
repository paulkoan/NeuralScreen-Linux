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
    local variant="$1" source="$2" input="${3:-}"
    local dir="$T/$variant"
    mkdir -p "$dir"
    local before="$dir/before.png" after="$dir/after.png"

    echo ""
    echo "=============================================================="
    echo " variant: $variant   (--source $source${input:+ --input-image $input})"
    echo "=============================================================="

    local args=(--frames "$FRAMES" --headless --source "$source"
                --save-before "$before" --save-after "$after")
    [ -n "$input" ] && args+=(--input-image "$input")

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

    case "$drc" in
        0) pass "the pass changed the frame" ;;
        *) fail "$(grep '^VERDICT' "$dir/analysis.txt" | sed 's/^VERDICT //')"
           VARIANT_STATUS=1 ;;
    esac

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

# "auto" is what the product does: the portal on a Wayland session, the X11 grab
# otherwise. Naming it explicitly here means the gate tests the same decision the
# user's own runs go through.
run_variant capture auto
CAPTURE_STATUS=$VARIANT_STATUS

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
    for v in pass capture; do
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
    echo "  artifacts -> $OUT/{pass,capture}/"
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
if [ "$CAPTURE_STATUS" = "0" ]; then
    echo "  capture  PASS — a real screen frame comes through."
else
    echo "  capture  FAIL — no usable screen frame (see the variant output)."
fi
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
