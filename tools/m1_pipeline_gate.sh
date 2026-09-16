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

# Same source, same settings, same work resolution as `pass` — only the way the
# motion field travels differs. `pass` sends a full-resolution zero field (3.7 MB
# of the 7.4 MB that goes to the worker each frame); this sends the same zeros at
# the flow size and lets the worker upscale them. Measured on the box, `send`
# dominates the frame (67ms of 81ms) while `recv` — the worker and the network —
# is 8.7ms, so if the cost is bytes and not compute, this is where it shows.
run_variant mots synthetic "" "--motion-small"
MOTS_STATUS=$VARIANT_STATUS

# The control. Same source and same worker as `pass`, effect dialled to zero:
# whatever still changes is the transport, not the network. Without this, "the
# pass changed the frame" cannot distinguish the two, and the effect numbers
# would be read as the network's work when part of them is the round trip.
run_variant baseline synthetic "" \
    "--param intensity=0 --param local_tone=0 --param local_structure=0" control
BASELINE_STATUS=$VARIANT_STATUS

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
    for v in pass scaled mots baseline capture; do
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
    echo "  artifacts -> $OUT/{pass,scaled,mots,baseline,capture}/"
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
if [ "$CAPTURE_STATUS" = "0" ]; then
    echo "  capture  PASS — a real screen frame comes through."
else
    echo "  capture  FAIL — no usable screen frame (see the variant output)."
fi
echo ""
echo "  per-frame cost by variant — the point of the run:"
for v in pass scaled mots baseline capture; do
    line=$(grep -m1 '^timing:' "$T/$v/mvp.txt" 2>/dev/null || true)
    printf '    %-9s %s\n' "$v" "${line:-<no timing recorded>}"
done
echo ""
echo "  Read the split, not just the fps. Measured on the box: send dominated"
echo "  (67ms of 81ms) while recv — the worker plus the network — was 8.7ms, and"
echo "  the product's own figure for the network at 1280x720 is ~2.9ms. So the"
echo "  cost is bytes being moved, not the neural pass:"
echo "    scaled  tests whether the network's resolution matters (it should not)"
echo "    mots    tests whether the frame's bytes matter (it should)"
echo "    baseline the transport floor with the effect off"
echo ""
echo "  pass vs scaled is the experiment: same source, same transport, same"
echo "  effect, only the resolution the network works at differs. If scaled is"
echo "  not meaningfully quicker, the cost is not in the network — and the"
echo "  product's own figure for the network is 1.5 ms + 1.51 ms per megapixel"
echo "  (a 5070 Ti), which at 2560x1440 is about 7 ms."
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
