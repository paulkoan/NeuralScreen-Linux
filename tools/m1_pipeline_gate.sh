#!/bin/bash
# m1_pipeline_gate.sh — the M1 gate: does a frame come out the far end changed?
#
#   tools/m1_pipeline_gate.sh                # run it, print the verdict
#   tools/m1_pipeline_gate.sh --out DIR      # also copy artifacts into DIR
#   tools/m1_pipeline_gate.sh --frames N     # frames to push (default 30)
#
# WHY THIS EXISTS, AND WHY IT IS NOT M0
#
# M0 (`m0_env_gate.sh`) runs `wine nvngx.dll --test`, a synthetic 640x360 loop
# that was written as a stand-in for having a game attached. Reading the source
# against it shows `--test` does NOT exercise the same APIs as the real
# pipeline:
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
# another, and it fails with 0xBAD00004 FAIL_FeatureNotFound. The via-core
# variant makes it fail EARLIER, at create, with 0xBAD0000B
# UnableToInitializeFeature — i.e. NGX Core cannot create feature 18 under Wine
# at all. That is consistent with the Core being the piece that does not know the
# handle, and it means the `--test` evaluate failure says nothing directly about
# the live path.
#
# The live path is the product. It is what `python -m minimal` drives
# (`wine nvngx.dll --live`). So this gate runs the MVP end to end and checks the
# frame that comes back is actually changed by the pass.
#
# PASS = the MVP exits 0, both images exist, and the NR pass measurably altered
#        the frame: mean absolute difference above the floor, and the output is
#        not blank or a duplicate of the input.
#
# A "PSNR = inf" or zero-difference result is a FAIL even though the process
# exited 0: it means the pass was a no-op, which is the specific failure this
# gate is here to catch.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

NATIVE="$REPO/native"
LOG="$NATIVE/dlss5-feed-host.log"

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

  tools/m1_pipeline_gate.sh              run it, print the verdict
  tools/m1_pipeline_gate.sh --out DIR    also copy artifacts into DIR
  tools/m1_pipeline_gate.sh --frames N   frames to push (default 30)

Exit codes:  0 = PASS   1 = FAIL   2 = BLOCKED (prerequisites missing)

Runs `python -m minimal --frames N --headless --save-before/--save-after`, then
measures how much the NR pass changed the frame. Checks the live path
(EvaluateVideo), not `--test` — see the header of this script for why those are
not the same thing.

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
if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
    warn "neither DISPLAY nor WAYLAND_DISPLAY is set — screen capture will fail"
fi
if [ "$MISSING" = "1" ]; then
    echo ""
    echo "=============================================================="
    echo " RESULT: BLOCKED — fix the prerequisites above first"
    echo "=============================================================="
    exit 2
fi

# --- run the MVP ------------------------------------------------------------
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
BEFORE="$T/before.png"
AFTER="$T/after.png"
rm -f "$LOG"

echo ""
echo "--- python -m minimal --frames $FRAMES (the live path) ---"
START=$(date +%s)
"$PY" -m minimal --frames "$FRAMES" --headless \
    --save-before "$BEFORE" --save-after "$AFTER" 2>&1 | tee "$T/mvp.txt"
RC=${PIPESTATUS[0]}
ELAPSED=$(( $(date +%s) - START ))
echo ""
echo "  exit code: $RC   elapsed: ${ELAPSED}s"

# --- verdict ----------------------------------------------------------------
echo ""
echo "--- verdict ---"
STATUS=0

if [ "$RC" = "0" ]; then
    pass "the MVP exited 0"
else
    fail "the MVP exited $RC"
    STATUS=1
fi

for f in "$BEFORE" "$AFTER"; do
    if [ -s "$f" ]; then
        pass "$(basename "$f") written ($(du -h "$f" | cut -f1))"
    else
        fail "$(basename "$f") was not written"
        STATUS=1
    fi
done

# The interesting part: did the pass actually DO anything? An MVP that returns
# the input frame unchanged exits 0 and looks healthy while doing nothing.
if [ -s "$BEFORE" ] && [ -s "$AFTER" ]; then
    echo ""
    echo "--- did the pass change the frame? ---"
    ANALYSIS="$T/analysis.txt"
    "$PY" - "$BEFORE" "$AFTER" > "$ANALYSIS" 2>&1 <<'PYEOF'
import sys
import numpy as np
import cv2

def load(p):
    img = cv2.imread(p, cv2.IMREAD_COLOR)
    if img is None:
        print(f"could not read {p}")
        raise SystemExit(3)
    return img[:, :, ::-1].astype(np.float32)   # BGR -> RGB

a = load(sys.argv[1])
b = load(sys.argv[2])
if a.shape != b.shape:
    print(f"shape mismatch: before={a.shape} after={b.shape}")
    raise SystemExit(3)
mad = float(np.abs(a - b).mean())
p99 = float(np.percentile(np.abs(a - b), 99))
mse = float(((a - b) ** 2).mean())
psnr = float("inf") if mse == 0 else 10.0 * np.log10((255.0 ** 2) / mse)
print(f"size              {a.shape[1]}x{a.shape[0]}")
print(f"mean abs diff     {mad:.4f}  (0 = byte-identical)")
print(f"p99 abs diff      {p99:.2f}")
print(f"PSNR              {psnr if psnr != float('inf') else 'inf'}")
print(f"after is blank    {bool(b.std() < 0.5)}")
print(f"after == before   {bool(np.array_equal(a, b))}")
PYEOF
    ANA_RC=$?
    sed 's/^/  /' "$ANALYSIS"

    if [ "$ANA_RC" != "0" ]; then
        fail "could not compare the frames"
        STATUS=1
    else
        MAD="$(grep -oP 'mean abs diff\s+\K[0-9.]+' "$ANALYSIS" || echo 0)"
        BLANK="$(grep -oP 'after is blank\s+\K\w+' "$ANALYSIS" || echo true)"
        SAME="$(grep -oP 'after == before\s+\K\w+' "$ANALYSIS" || echo true)"

        if [ "$SAME" = "True" ]; then
            fail "the pass returned the input unchanged — it ran but did nothing"
            STATUS=1
        elif [ "$BLANK" = "True" ]; then
            fail "the output is blank — the pass ran and produced nothing"
            STATUS=1
        elif awk -v m="${MAD:-0}" 'BEGIN{exit !(m < 0.05)}'; then
            fail "the frames differ by only $MAD/255 on average — too little to be a pass"
            STATUS=1
        else
            pass "the pass changed the frame (mean abs diff $MAD/255)"
        fi
    fi
fi

# --- what the worker said ---------------------------------------------------
if [ -f "$LOG" ]; then
    pass "worker log: $(wc -l < "$LOG") lines"
    echo ""
    echo "--- worker log, stage lines ---"
    grep -iE "feature 18|Init_Ext|evaluate|NVSDK_NGX|DLSSNR|fail|error" "$LOG" \
        | tail -12 | sed 's/^/  /' || echo "  (no stage lines)"
else
    warn "no dlss5-feed-host.log — the worker did not write one"
fi

# --- copy artifacts out -----------------------------------------------------
if [ -n "$OUT" ]; then
    cp -f "$BEFORE" "$OUT/before.png" 2>/dev/null || true
    cp -f "$AFTER"  "$OUT/after.png"  2>/dev/null || true
    cp -f "$T/mvp.txt" "$OUT/mvp.txt" 2>/dev/null || true
    cp -f "$LOG" "$OUT/" 2>/dev/null || true
    [ -f "$ANALYSIS" ] && cp -f "$ANALYSIS" "$OUT/analysis.txt" 2>/dev/null || true
    {
        echo "date:              $(date -u)"
        echo "DISPLAY:           ${DISPLAY:-}"
        echo "WAYLAND_DISPLAY:   ${WAYLAND_DISPLAY:-}"
        echo "XDG_SESSION_TYPE:  ${XDG_SESSION_TYPE:-}"
        echo "frames pushed:     $FRAMES"
        echo "wine:              $(wine --version 2>&1)"
        echo "driver:            $(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>&1 | head -1)"
    } > "$OUT/m1_environment.txt" 2>&1
    echo ""
    echo "  artifacts -> $OUT/  (before.png, after.png, analysis.txt, mvp.txt)"
fi

echo ""
echo "=============================================================="
if [ "$STATUS" = "0" ]; then
    echo " RESULT: PASS — capture -> DLSS5 NR pass -> display works."
    echo " Attach before.png and after.png in the report and that is the MVP."
else
    echo " RESULT: FAIL — see the stage lines above."
    echo " M0 (--test) already proved NGX init and feature create work; this"
    echo " gate is about the live path, which is a different set of calls."
fi
echo "=============================================================="
exit "$STATUS"
