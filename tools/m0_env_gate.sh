#!/bin/bash
# m0_env_gate.sh — the M0 gate: can the DLSS5 NR worker run under Wine at all?
#
#   tools/m0_env_gate.sh                 # run the gate, print the verdict
#   tools/m0_env_gate.sh --out DIR       # also write logs into DIR
#
# Runs `wine native/nvngx.dll --test`. That path needs no game, no window and no
# Python: it builds a D3D12 device, creates NGX feature 18 and runs 300
# evaluates on a synthetic 640x360 pattern.
#
# PASS = exit 0, "[pure] direct feature 18 ready" in the log, and
#        "--test finished: N/300" with N >= 250.
#
# If this fails, stop. The log names the stage that failed.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

NATIVE="$REPO/native"
WORKER="$NATIVE/nvngx.dll"
NR_DLL="$NATIVE/nvngx_dlssnr.dll"
LOG="$NATIVE/dlss5-feed-host.log"

OUT=""
while [ $# -gt 0 ]; do
    case "$1" in
        --out)
            if [ -z "${2:-}" ]; then
                echo "m0_env_gate.sh: --out needs a directory" >&2
                exit 2
            fi
            OUT="$2"; mkdir -p "$OUT"; shift 2 ;;
        -h|--help)
            cat <<'USAGE'
m0_env_gate.sh — the M0 environment gate: can the DLSS5 NR worker run under Wine?

  tools/m0_env_gate.sh                 run the gate, print the verdict
  tools/m0_env_gate.sh --out DIR       also copy the logs into DIR

Exit codes:  0 = PASS   1 = FAIL   2 = BLOCKED (prerequisites missing)

For a full report (pytest + this gate + an environment snapshot) use instead:

  tools/run_tests.sh --report --m0

which writes everything into test-results/<UTC-timestamp>/ — commit and push
that directory and it can be read straight from the repo.
USAGE
            exit 0 ;;
        *)
            echo "m0_env_gate.sh: unknown option: $1" >&2
            echo "try: tools/m0_env_gate.sh --help" >&2
            exit 2 ;;
    esac
done

pass() { printf '  \033[32m✓\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✗\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }

echo "=============================================================="
echo " M0 — environment gate"
echo "=============================================================="
echo ""

echo "--- prerequisites ---"
MISSING=0

if command -v wine >/dev/null 2>&1; then
    pass "wine: $(wine --version 2>&1)"
else
    fail "wine is not installed"
    echo "      Arch:   sudo pacman -S wine"
    echo "      Debian: sudo apt install wine wine64"
    MISSING=1
fi

if command -v nvidia-smi >/dev/null 2>&1; then
    pass "GPU: $(nvidia-smi --query-gpu=name,driver_version,compute_cap --format=csv,noheader 2>&1 | head -1)"
    CC="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>&1 | head -1 | tr -d ' ')"
    case "$CC" in
        7.5|8.6|8.9|12.0) pass "compute capability $CC is in the runtime's kernel set (sm_75/86/89/120)" ;;
        "") warn "could not read compute capability" ;;
        *)  warn "compute capability $CC is NOT in sm_75/86/89/120 — the NR pass may refuse" ;;
    esac
else
    fail "nvidia-smi not found — no NVIDIA driver visible"
    MISSING=1
fi

if ls /usr/share/vulkan/icd.d/ 2>/dev/null | grep -qi nvidia; then
    pass "Vulkan ICD: $(ls /usr/share/vulkan/icd.d/ | grep -i nvidia | head -1)"
else
    warn "no NVIDIA Vulkan ICD found — D3D12 over VKD3D will likely fail"
fi

for f in "$WORKER" "$NR_DLL" "$NATIVE/SpoutDX.dll" "$NATIVE/Spout.dll"; do
    if [ -f "$f" ]; then
        pass "$(basename "$f") ($(du -h "$f" | cut -f1))"
    else
        fail "missing: $f"
        if [ "$f" = "$NR_DLL" ]; then
            echo "      nvngx_dlssnr.dll is gitignored (159 MB). It comes from the"
            echo "      v1.6.0 release archive and must be copied into native/."
        fi
        MISSING=1
    fi
done

if [ "$MISSING" = "1" ]; then
    echo ""
    echo "=============================================================="
    echo " RESULT: BLOCKED — fix the prerequisites above first"
    echo "=============================================================="
    [ -n "$OUT" ] && { env > "$OUT/m0_environment.txt" 2>&1; }
    exit 2
fi

echo ""
echo "--- running: wine native/nvngx.dll --test ---"
rm -f "$LOG"

export WINEPREFIX="${WINEPREFIX:-$HOME/.neuralscreen/wine}"
# The native translation layers MUST be overridden, or Wine loads its builtin
# dxgi/d3d11/d3d12/nvapi64. Two distinct failures follow:
#   0xBAD00001 FAIL_FeatureNotSupported — NGX Core not found at all
#   0xBAD00002 FAIL_PlatformError       — NGX Core found, but NVAPI cannot
#                                          report the GPU to it
export WINEDLLOVERRIDES="${NS_WINEDLLOVERRIDES:-d3d12=n,b;d3d12core=n,b;d3d11=n,b;dxgi=n,b;nvapi64=n,b;nvofapi64=n,b;nvngx_dlssnr=n}"
# Without this dxvk-nvapi leaves the NGX/DLSS part of NVAPI disabled, and NGX
# Core cannot establish the platform.
export DXVK_ENABLE_NVAPI="${DXVK_ENABLE_NVAPI:-1}"
# Ask dxvk-nvapi to log, so 'NvAPI_Initialize' / 'NvAPI_GPU_GetArchInfo' show up
# in the worker's output and prove whether NVAPI answered.
export DXVK_NVAPI_LOG_LEVEL="${DXVK_NVAPI_LOG_LEVEL:-info}"
echo "  WINEPREFIX=$WINEPREFIX"
echo "  WINEDLLOVERRIDES=$WINEDLLOVERRIDES"
echo "  DXVK_ENABLE_NVAPI=$DXVK_ENABLE_NVAPI"

# The worker's NGX loader finds NGX Core through the registry on Wine (its D3DKMT
# and same-directory paths both fail there). Warn if that is not set up yet.
NGXREG="$(timeout 60 wine reg query 'HKLM\SOFTWARE\NVIDIA Corporation\Global\NGXCore' 2>/dev/null | grep -iE 'FullPath|NGXPath' | head -1)"
if [ -n "$NGXREG" ]; then
    echo "  NGXCore registry: $(echo "$NGXREG" | tr -s ' ')"
else
    echo "  NGXCore registry: NOT SET"
    echo "     -> NGX Core will not be found and init will fail with 0xBAD00001."
    echo "     -> run: tools/wine_ngx_setup.sh   (then re-run this gate)"
fi
echo ""

START=$(date +%s)
( cd "$NATIVE" && timeout 600 wine nvngx.dll --test )
RC=$?
ELAPSED=$(( $(date +%s) - START ))
echo ""
echo "  exit code: $RC   elapsed: ${ELAPSED}s"

COMBINED=""
[ -f "$LOG" ] && COMBINED="$(cat "$LOG")"

echo ""
echo "--- verdict ---"
STATUS=0

if [ "$RC" = "124" ]; then
    fail "timed out after 600s — the worker hung (a known NGX-over-Wine failure mode)"
    STATUS=1
elif [ "$RC" != "0" ]; then
    fail "the worker exited $RC"
    STATUS=1
else
    pass "the worker exited 0"
fi

if [ -f "$LOG" ]; then
    pass "produced dlss5-feed-host.log ($(wc -l < "$LOG") lines)"
else
    fail "produced NO log — Wine probably never started the process"
    STATUS=1
fi

if echo "$COMBINED" | grep -q "no NVIDIA adapter found"; then
    fail "no NVIDIA adapter visible to D3D12 — VKD3D/DXGI cannot see the card"
    STATUS=1
elif echo "$COMBINED" | grep -q "D3D12CreateDevice failed"; then
    fail "D3D12CreateDevice failed: $(echo "$COMBINED" | grep 'D3D12CreateDevice failed' | head -1)"
    STATUS=1
elif echo "$COMBINED" | grep -q "dxgi/d3d12 exports missing"; then
    fail "dxgi.dll / d3d12.dll did not load under Wine"
    STATUS=1
fi

if echo "$COMBINED" | grep -q "NVSDK_NGX_D3D12_Init"; then
    NLINE="$(echo "$COMBINED" | grep 'NVSDK_NGX_D3D12_Init' | head -1)"
    if echo "$NLINE" | grep -q "Success"; then
        pass "NGX initialised: $NLINE"
    else
        fail "NGX init failed: $NLINE"
        STATUS=1
        if echo "$NLINE" | grep -q "0xBAD00001"; then
            cat <<'REMEDY'

     0xBAD00001 = FAIL_FeatureNotSupported, and at the INIT stage it does not
     mean "unsupported GPU" — it means NGX Core was never found. The worker's
     NGX loader (strings: NGXGetPathUsingQAI / NGXGetPathFromRegistry /
     "NGXCore not found next to the application") can only reach the core
     through the registry under Wine:

       * the QAI path needs D3DKMT, unimplemented in Wine
         (`fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled`)
       * "next to the application" collides with the worker itself, whose file
         name IS nvngx.dll, so it loads a module with no exports
       * so only HKLM\...\NGXCore remains

     Fix:  tools/wine_ngx_setup.sh
REMEDY
        fi
        if echo "$NLINE" | grep -q "0xBAD00002"; then
            cat <<'REMEDY'

     0xBAD00002 = FAIL_PlatformError. NGX Core IS being found and loaded now,
     but its platform check fails — it cannot get a usable answer about the GPU.
     Under Wine that answer has to come from dxvk-nvapi, and dxvk-nvapi needs:

       * DXVK's dxgi.dll AND d3d11.dll in the prefix (it uses their extension
         points; Wine's builtin dxgi/d3d11 will not do)
       * vkd3d-proton's d3d12.dll + d3d12core.dll
       * DXVK_ENABLE_NVAPI=1 — without it the NGX/DLSS part of NVAPI is off
       * all of the above overridden native-first in WINEDLLOVERRIDES

     Check the "NvAPI_Initialize" / "NvAPI_GPU_GetArchInfo" lines below: absent
     or failing means NVAPI never answered.

     Fix:  tools/wine_ngx_setup.sh   (installs DXVK / vkd3d-proton / dxvk-nvapi)
REMEDY
        fi
    fi
else
    fail "never reached NGX init — died earlier"
    STATUS=1
fi

if echo "$COMBINED" | grep -q "feature 18 ready"; then
    pass "NGX feature 18 created"
else
    if echo "$COMBINED" | grep -q "feature 18"; then
        fail "feature 18 create failed: $(echo "$COMBINED" | grep 'feature 18' | tail -1)"
    else
        fail "feature 18 was never attempted"
    fi
    STATUS=1
fi

SUMMARY="$(echo "$COMBINED" | grep -o -- '--test finished: [0-9]*/[0-9]*' | tail -1)"
if [ -n "$SUMMARY" ]; then
    GOOD="$(echo "$SUMMARY" | sed 's|.*finished: \([0-9]*\)/.*|\1|')"
    if [ "$GOOD" -ge 250 ]; then
        pass "$SUMMARY evaluates succeeded"
    else
        fail "$SUMMARY — fewer than 250"
        STATUS=1
    fi
else
    fail "no evaluation summary — the test loop did not finish"
    STATUS=1
fi

# --- what NVAPI said (this is what NGX needs for its platform check) --------
echo ""
echo "--- NVAPI (dxvk-nvapi) ---"
NVLOG="$(echo "$COMBINED" | grep -iE "nvapi|NvAPI_Initialize|GetArchInfo|DXVK_ENABLE_NVAPI" | head -12)"
if [ -n "$NVLOG" ]; then
    echo "$NVLOG" | sed 's/^/  /'
else
    warn "no NVAPI output at all — dxvk-nvapi's nvapi64.dll is probably not"
    warn "being loaded, or DXVK_ENABLE_NVAPI=1 is not taking effect"
fi

# --- what the log says about the failure, if it failed ----------------------
if [ "$STATUS" != "0" ] && [ -f "$LOG" ]; then
    echo ""
    echo "--- the log's own explanation ---"
    grep -iE "fail|error|unavailable|0x[0-9A-Fa-f]{8}|not found|refus" "$LOG" \
        | tail -15 | sed 's/^/  /' || echo "  (nothing that looks like an error)"
fi

# --- copy artifacts out -----------------------------------------------------
if [ -n "$OUT" ]; then
    cp "$LOG" "$OUT/" 2>/dev/null || true
    # Only the variables that matter: a full `env` dump is 100+ lines of noise
    # and hides the ones this gate is about.
    {
        echo "date:              $(date -u)"
        echo "WINEPREFIX:        ${WINEPREFIX:-}"
        echo "WINEDLLOVERRIDES:  ${WINEDLLOVERRIDES:-}"
        echo "DXVK_ENABLE_NVAPI: ${DXVK_ENABLE_NVAPI:-}"
        echo "DXVK_NVAPI_LOG_LEVEL: ${DXVK_NVAPI_LOG_LEVEL:-}"
        echo "DISPLAY:           ${DISPLAY:-}"
        echo "WAYLAND_DISPLAY:   ${WAYLAND_DISPLAY:-}"
        echo "XDG_SESSION_TYPE:  ${XDG_SESSION_TYPE:-}"
        echo "wine:              $(wine --version 2>&1)"
        echo "driver:            $(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>&1 | head -1)"
    } > "$OUT/m0_environment.txt" 2>&1
    echo ""
    echo "  artifacts -> $OUT/"
fi

echo ""
echo "=============================================================="
if [ "$STATUS" = "0" ]; then
    echo " RESULT: PASS — the DLSS5 NR pass runs on this machine under Wine."
    echo " Next: python -m minimal --frames 1 --save-before before.png --save-after after.png"
else
    echo " RESULT: FAIL — stop here. The port is not viable until this passes."
    echo " The log above names the stage. Do not build downstream on this."
fi
echo "=============================================================="
exit "$STATUS"