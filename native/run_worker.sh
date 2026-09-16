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
# d3d12 (old vkd3d) and builtin nvapi64, and NGX cannot see the NVIDIA GPU.
# Symptom when missing: NVSDK_NGX_D3D12_Init -> 0xBAD00001 (FeatureNotSupported).
# d3d12/d3d12core come from vkd3d-proton, nvapi64 from dxvk-nvapi, dxgi from DXVK.
export WINEDLLOVERRIDES="${NS_WINEDLLOVERRIDES:-d3d12,d3d12core,nvapi64,dxgi=n,b;nvngx_dlssnr=n}"
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