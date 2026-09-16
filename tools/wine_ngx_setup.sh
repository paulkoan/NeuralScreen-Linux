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
echo "     Wine's builtin dxgi/d3d11/d3d12/nvapi64 cannot carry NGX: dxvk-nvapi"
echo "     needs DXVK's dxgi and d3d11 extension points, and vkd3d-proton's"
echo "     d3d12. Without them NGX Core loads but its platform check fails"
echo "     (0xBAD00002 FAIL_PlatformError) because NVAPI cannot report the GPU."

DXVK_VER="3.1.1"
VKD3D_VER="3.0.1"
NVAPI_VER="0.9.2"

nv_ver() { strings -a "$SYS32/nvapi64.dll"   2>/dev/null | grep -oE '^v?0\.9\.[0-9]+' | sort -u | head -1; }
vk_ver() { strings -a "$SYS32/d3d12core.dll" 2>/dev/null | grep -oE '^3\.0\.[0-9]+'   | sort -u | head -1; }

have_dxvk=1
for f in dxgi.dll d3d11.dll; do [ -s "$SYS32/$f" ] || have_dxvk=0; done
have_vkd3d=1
for f in d3d12.dll d3d12core.dll; do [ -s "$SYS32/$f" ] || have_vkd3d=0; done
have_nvapi=1
[ -s "$SYS32/nvapi64.dll" ] || have_nvapi=0

echo "     present now: dxvk-nvapi $(nv_ver || echo missing) / vkd3d-proton $(vk_ver || echo missing)"

NEED_INSTALL=0
[ "$have_dxvk"  = "0" ] && { warn "DXVK's dxgi.dll/d3d11.dll are missing from system32"; NEED_INSTALL=1; }
[ "$have_vkd3d" = "0" ] && { warn "vkd3d-proton's d3d12.dll/d3d12core.dll are missing"; NEED_INSTALL=1; }
[ "$have_nvapi" = "0" ] && { warn "dxvk-nvapi's nvapi64.dll is missing from system32"; NEED_INSTALL=1; }

if [ "$CHECK_ONLY" = "1" ]; then
    warn "skipped (--check); re-run without --check to install"
else
    command -v zstd >/dev/null 2>&1 || NEED_ZSTD=1
    T="$(mktemp -d)"
    trap 'rm -rf "$T"' EXIT

    if [ "$have_dxvk" = "0" ]; then
        echo "     fetching DXVK $DXVK_VER ..."
        if curl -sfL -o "$T/dxvk.tar.gz" \
            "https://github.com/doitsujin/dxvk/releases/download/v$DXVK_VER/dxvk-$DXVK_VER.tar.gz" \
            && tar xzf "$T/dxvk.tar.gz" -C "$T"; then
            for f in dxgi.dll d3d11.dll d3d10core.dll; do
                src="$(find "$T" -path '*/x64/*' -name "$f" -print -quit)"
                [ -n "$src" ] || { warn "DXVK archive has no x64/$f"; continue; }
                [ -f "$SYS32/$f" ] && cp -f "$SYS32/$f" "$SYS32/$f.bak_builtin" 2>/dev/null
                cp -f "$src" "$SYS32/$f" && ok "installed DXVK $f"
            done
        else
            bad "could not fetch/extract DXVK $DXVK_VER"
        fi
    else
        ok "DXVK dxgi.dll + d3d11.dll already present"
    fi

    if [ "$have_vkd3d" = "0" ]; then
        echo "     fetching vkd3d-proton $VKD3D_VER ..."
        if ! command -v zstd >/dev/null 2>&1; then
            bad "zstd is required to unpack vkd3d-proton (install it and re-run)"
        elif curl -sfL -o "$T/vkd3d.tar.zst" \
            "https://github.com/HansKristian-Work/vkd3d-proton/releases/download/v$VKD3D_VER/vkd3d-proton-$VKD3D_VER.tar.zst" \
            && zstd -dq "$T/vkd3d.tar.zst" -o "$T/vkd3d.tar" && tar xf "$T/vkd3d.tar" -C "$T"; then
            for f in d3d12.dll d3d12core.dll; do
                src="$(find "$T" -path '*/x64/*' -name "$f" -print -quit)"
                [ -n "$src" ] || { warn "vkd3d archive has no x64/$f"; continue; }
                [ -f "$SYS32/$f" ] && cp -f "$SYS32/$f" "$SYS32/$f.bak_builtin" 2>/dev/null
                cp -f "$src" "$SYS32/$f" && ok "installed vkd3d-proton $f"
            done
        else
            bad "could not fetch/extract vkd3d-proton $VKD3D_VER"
        fi
    else
        ok "vkd3d-proton d3d12.dll + d3d12core.dll already present"
    fi

    if [ "$have_nvapi" = "0" ]; then
        echo "     fetching dxvk-nvapi $NVAPI_VER ..."
        if curl -sfL -o "$T/nvapi.tar.gz" \
            "https://github.com/jp7677/dxvk-nvapi/releases/download/v$NVAPI_VER/dxvk-nvapi-v$NVAPI_VER.tar.gz" \
            && tar xzf "$T/nvapi.tar.gz" -C "$T"; then
            for f in nvapi64.dll nvofapi64.dll; do
                src="$(find "$T" -path '*/x64/*' -name "$f" -print -quit)"
                [ -n "$src" ] || { warn "dxvk-nvapi archive has no x64/$f"; continue; }
                cp -f "$src" "$SYS32/$f" && ok "installed dxvk-nvapi $f"
            done
        else
            bad "could not fetch/extract dxvk-nvapi $NVAPI_VER"
        fi
    else
        ok "dxvk-nvapi nvapi64.dll already present"
    fi

    echo "     now: dxvk-nvapi $(nv_ver || echo missing) / vkd3d-proton $(vk_ver || echo missing)"
fi

# --- 4b. NGX Core must also be beside system32's nvngx.dll ------------------
# dxvk-nvapi's own docs ask for the driver's nvngx.dll / _nvngx.dll in system32
# for DLSS. Section 2 put them there; this just confirms it.
echo ""
echo "--- 4b. driver NGX DLLs in system32 ---"
for f in nvngx.dll _nvngx.dll; do
    if [ -s "$SYS32/$f" ]; then ok "$f ($(du -h "$SYS32/$f" | cut -f1))"
    else warn "$f missing from system32"; fi
done

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