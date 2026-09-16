#!/bin/bash
# run_worker.sh — Launch nvngx.dll (the NGX DLSS5 worker) under Wine + VKD3D.
#
# Usage:
#   ./native/run_worker.sh                # default Wine prefix
#   ./native/run_worker.sh --prefix /path  # custom prefix

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NATIVE_DIR="$SCRIPT_DIR"

DEFAULT_PREFIX="${HOME}/.neuralscreen/wine"
PREFIX="${DEFAULT_PREFIX}"

if [ "${1:-}" = "--prefix" ] && [ -n "${2:-}" ]; then
    PREFIX="$2"
    shift 2
fi

export WINEPREFIX="$PREFIX"
# The native translation layers MUST be overridden or Wine loads its builtin
# dxgi/d3d11/d3d12/nvapi64. dxvk-nvapi needs DXVK's dxgi AND d3d11 extension
# points, and vkd3d-proton's d3d12 — through Wine's builtins NGX Core loads but
# its platform check then fails (0xBAD00002 FAIL_PlatformError) because NVAPI
# cannot report the GPU.
#
#   d3d12/d3d12core  <- vkd3d-proton
#   dxgi/d3d11       <- DXVK
#   nvapi64          <- dxvk-nvapi
#   nvngx_dlssnr     <- the NR runtime itself, never a builtin
export WINEDLLOVERRIDES="${NS_WINEDLLOVERRIDES:-d3d12=n,b;d3d12core=n,b;d3d11=n,b;dxgi=n,b;nvapi64=n,b;nvofapi64=n,b;nvngx_dlssnr=n}"
# dxvk-nvapi requires this to disable DXVK's nvapiHack; without it the NGX/DLSS
# part of NVAPI stays off and NGX cannot establish the platform.
export DXVK_ENABLE_NVAPI="${DXVK_ENABLE_NVAPI:-1}"
export WINE="${WINE:-wine}"

# Auto-create prefix
if [ ! -d "$PREFIX" ]; then
    echo "[run_worker] Creating Wine prefix at $PREFIX" >&2
    mkdir -p "$PREFIX"
    WINEDLLOVERRIDES="" wineboot -u 2>/dev/null || true
    sleep 2
fi

# Check deps
if ! command -v "$WINE" &>/dev/null; then
    echo "[run_worker] ERROR: '$WINE' not found. Install Wine + VKD3D." >&2
    exit 1
fi

WORKER="$NATIVE_DIR/nvngx.dll"
if [ ! -f "$WORKER" ]; then
    echo "[run_worker] ERROR: $WORKER not found" >&2
    exit 1
fi

echo "[run_worker] Starting: $WINE $WORKER --live" >&2
exec "$WINE" "$WORKER" --live