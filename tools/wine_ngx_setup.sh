#!/bin/bash
# wine_ngx_setup.sh — make the Wine prefix able to load NVIDIA's NGX Core.
#
#   tools/wine_ngx_setup.sh                 # diagnose + fix the default prefix
#   tools/wine_ngx_setup.sh --prefix PATH   # a specific WINEPREFIX
#   tools/wine_ngx_setup.sh --check         # diagnose only, change nothing
#   tools/wine_ngx_setup.sh --bridge DIR    # where the driver's NGX DLLs live
#
# WHY THIS EXISTS
#
# native/nvngx.dll statically links NVIDIA's own NGX loader. The strings in the
# binary name its three lookup paths:
#
#     NGXGetPathUsingQAI              -> goes through D3DKMT
#     NGXGetPathFromRegistry          -> HKLM\...\NGXCore
#     NGXCore not found next to the application
#
# Under Wine only ONE of those can work:
#
#   * the QAI path is dead: Wine does not implement the D3DKMT adapter query it
#     needs (visible in the log as
#     `fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled`);
#   * the "next to the application" path is a name collision — the worker's own
#     file IS nvngx.dll, so the loader finds a module with no exports;
#   * leaving only the registry.
#
# With no registry entry NGX Core is never loaded, so NVSDK_NGX_D3D12_Init
# returns 0xBAD00001 (FAIL_FeatureNotSupported). That is exactly what the first
# M0 run on the RTX 4080 reported. The fix is to install the driver's NGX bridge
# DLLs and point NGXCore at them.
#
# On Arch, nvidia-utils already ships them at /usr/lib/nvidia/wine/ — nothing to
# download. On other distros they come from the matching NVIDIA .run installer
# (`--extract-only`); this script searches for them and says so if they are missing.
#
# The second half is the DLL overrides. Without
#     d3d12,d3d12core,nvapi64,dxgi = native-first
# Wine loads its BUILTIN d3d12 (old vkd3d) and builtin nvapi64, and NGX cannot
# see the physical GPU through them. The previous launcher only overrode
# nvngx_dlssnr, so this was missing too.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PREFIX="${WINEPREFIX:-$HOME/.neuralscreen/wine}"
BRIDGE=""
CHECK_ONLY=0

while [ $# -gt 0 ]; do
    case "$1" in
        --prefix) PREFIX="$2"; shift 2 ;;
        --bridge) BRIDGE="$2"; shift 2 ;;
        --check)  CHECK_ONLY=1; shift ;;
        -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
export WINEPREFIX="$PREFIX"

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }

echo "=============================================================="
echo " Wine NGX setup — $PREFIX"
echo "=============================================================="
echo ""

if [ ! -d "$PREFIX/drive_c" ]; then
    echo "The prefix does not exist yet: $PREFIX"
    echo "Creating it with wineboot (this takes a moment)..."
    mkdir -p "$PREFIX"
    WINEDLLOVERRIDES="" wineboot -u >/dev/null 2>&1 || true
    sleep 3
fi
if [ ! -d "$PREFIX/drive_c" ]; then
    bad "could not create the prefix — is wine installed?"
    exit 1
fi
ok "prefix exists"

SYS32="$PREFIX/drive_c/windows/system32"

# --- DISPLAY: DXVK cannot create a Vulkan instance without one ---------------
if [ -z "${DISPLAY:-}" ]; then
    warn "DISPLAY is not set — DXVK cannot create a Vulkan instance without a display"
    warn "export DISPLAY=:0 (or your real display) before running the worker"
else
    ok "DISPLAY=$DISPLAY"
fi

# --- 1. the driver's NGX bridge DLLs -----------------------------------------
echo ""
echo "--- 1. NVIDIA NGX bridge (nvngx.dll / _nvngx.dll) ---"

if [ -z "$BRIDGE" ]; then
    for cand in \
        /usr/lib/nvidia/wine \
        /usr/lib64/nvidia/wine \
        /lib/nvidia/wine \
        /lib64/nvidia/wine \
        /usr/lib/x86_64-linux-gnu/nvidia/wine \
        /usr/lib/x86_64-linux-gnu/nvidia/current/wine \
        /usr/lib/x86_64-linux-gnu/nvidia/current/nvidia/wine \
        "$PREFIX/drive_c/ngx_bridge"
    do
        if [ -s "$cand/nvngx.dll" ] && [ -s "$cand/_nvngx.dll" ]; then
            BRIDGE="$cand"
            ok "found the driver's NGX bridge at $BRIDGE"
            break
        fi
    done
fi

if [ -z "$BRIDGE" ] || [ ! -s "$BRIDGE/nvngx.dll" ] || [ ! -s "$BRIDGE/_nvngx.dll" ]; then
    bad "no NGX bridge DLLs found (nvngx.dll + _nvngx.dll)"
    cat <<'EOF'

     These are NVIDIA's Wine-side NGX loaders, shipped with the driver:

       Arch:   nvidia-utils installs them at /usr/lib/nvidia/wine/
       Debian: /usr/lib/x86_64-linux-gnu/nvidia/wine/
       others: extract from the matching .run (no install needed):

         DRV=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | tr -d ' ')
         curl -O https://us.download.nvidia.com/XFree86/Linux-x86_64/$DRV/NVIDIA-Linux-x86_64-$DRV.run
         sh NVIDIA-Linux-x86_64-$DRV.run --extract-only --target /tmp/nvdrv
         mkdir -p ~/.neuralscreen/ngx_bridge
         cp /tmp/nvdrv/nvngx.dll /tmp/nvdrv/_nvngx.dll ~/.neuralscreen/ngx_bridge/

     then re-run this script with --bridge ~/.neuralscreen/ngx_bridge
EOF
    exit 1
fi

for f in nvngx.dll _nvngx.dll; do
    ok "$f ($(du -h "$BRIDGE/$f" | cut -f1))"
done

# --- 2. put them where the loader can find them ------------------------------
echo ""
echo "--- 2. install into the prefix ---"

if [ "$CHECK_ONLY" = "1" ]; then
    for f in nvngx.dll _nvngx.dll; do
        if [ -s "$SYS32/$f" ]; then ok "$f already in system32"; else warn "$f missing from system32"; fi
    done
else
    for f in nvngx.dll _nvngx.dll; do
        if cp -f "$BRIDGE/$f" "$SYS32/$f" 2>/dev/null; then
            ok "copied $f -> system32"
        else
            bad "could not copy $f into system32"
        fi
    done
fi

# --- 3. point the registry at the bridge dir --------------------------------
echo ""
echo "--- 3. registry: NGXCore -> the bridge directory ---"

if [ "$CHECK_ONLY" = "1" ]; then
    warn "skipped (--check)"
else
    WBRIDGE="$(WINEDLLOVERRIDES="" wine winepath -w "$BRIDGE" 2>/dev/null | tr -d '\r\n')"
    if [ -z "$WBRIDGE" ]; then
        # winepath failing is not fatal: derive the Z: path by hand.
        WBRIDGE="Z:$(printf '%s' "$BRIDGE" | tr '/' '\\')"
        warn "winepath failed; using $WBRIDGE"
    fi
    ok "bridge as a Windows path: $WBRIDGE"

    # The three locations NVIDIA's loader consults, plus the two value names
    # under the Global key (different driver generations read different ones).
    SET_OK=0
    while IFS='|' read -r key value; do
        if WINEDLLOVERRIDES="" timeout 90 wine reg add "$key" /v "$value" /d "$WBRIDGE" /f >/dev/null 2>&1; then
            SET_OK=$((SET_OK + 1))
        else
            warn "could not set $key\\$value"
        fi
    done <<'KEYS'
HKLM\SOFTWARE\NVIDIA Corporation\Global\NGXCore|FullPath
HKLM\SOFTWARE\NVIDIA Corporation\Global\NGXCore|NGXPath
HKLM\System\CurrentControlSet\Services\nvlddmkm\NGXCore|NGXPath
HKLM\System\CurrentControlSet\Services\nvlddmkm\Parameters\NGXCore|NGXPath
KEYS
    ok "$SET_OK/4 registry values written"
fi

# --- 4. the translation layers ----------------------------------------------
echo ""
echo "--- 4. translation layers (DXVK / vkd3d-proton / dxvk-nvapi) ---"
echo "     (Wine's builtin d3d12 and nvapi64 cannot see the NVIDIA GPU; the"
echo "      native ones must be present AND overridden — see 5 below)"

for f in dxgi.dll d3d12.dll d3d12core.dll nvapi64.dll; do
    if [ -s "$SYS32/$f" ]; then
        ok "$f present ($(du -h "$SYS32/$f" | cut -f1))"
    else
        warn "$f not in system32 — the matching native build should be there"
    fi
done

NVVER="$(strings -a "$SYS32/nvapi64.dll" 2>/dev/null | grep -oE '^v?0\.9\.[0-9]+' | sort -u | head -1)"
VKVER="$(strings -a "$SYS32/d3d12core.dll" 2>/dev/null | grep -oE '^3\.0\.[0-9]+' | sort -u | head -1)"
echo "     dxvk-nvapi ${NVVER:-?} / vkd3d-proton ${VKVER:-?}"
if [ "$NVVER" != "v0.9.2" ] && [ "$NVVER" != "0.9.2" ]; then
    warn "dxvk-nvapi 0.9.2 is the version that passes 64-bit CuBIN calls"
    warn "to VKD3D-Proton 3.0.1+; older builds fail the feature-18 create step."
    warn "Only upgrade if NGX initialises but feature 18 still fails."
fi

# --- 5. report the overrides to use -----------------------------------------
echo ""
echo "--- 5. the DLL overrides the worker must be launched with ---"
cat <<'EOF'

    WINEDLLOVERRIDES="d3d12,d3d12core,nvapi64,dxgi=n,b;nvngx_dlssnr=n"

  Without d3d12/d3d12core here, Wine loads its own old vkd3d and NGX cannot
  reach the GPU. native/run_worker.sh and tools/m0_env_gate.sh now set this.

EOF

echo "=============================================================="
if [ "$CHECK_ONLY" = "1" ]; then
    echo " RESULT: diagnosis only (--check). Re-run without --check to apply."
else
    echo " RESULT: prefix configured. Now run: tools/m0_env_gate.sh"
fi
echo "=============================================================="
exit 0