#!/bin/bash
# wine_setup.sh — One-shot Wine prefix + VKD3D setup for NeuralScreen on Linux.

set -euo pipefail

PREFIX="${HOME}/.neuralscreen/wine"

echo "=========================================="
echo " NeuralScreen — Wine + VKD3D setup"
echo "=========================================="
echo ""
echo "Target prefix: $PREFIX"
echo ""

# Check Wine
if ! command -v wine &>/dev/null; then
    echo "Wine not found. Install it:"
    echo "  Debian: sudo apt install wine wine64 wine32"
    echo "  Arch:   sudo pacman -S wine"
    echo "  Fedora: sudo dnf install wine"
    exit 1
fi
echo "Wine version: $(wine --version 2>&1)"

# Check VKD3D
if command -v vkd3d-config &>/dev/null || ldconfig -p 2>/dev/null | grep -q libvkd3d; then
    echo "VKD3D (D3D12→Vulkan) found ✓"
else
    echo "VKD3D not found. Install:"
    echo "  Debian: sudo apt install vkd3d-proton libvkd3d-dev"
    echo "  Arch:   sudo pacman -S vkd3d-proton"
    echo "  Fedora: sudo dnf install vkd3d-proton"
    echo ""
fi

# Create prefix
export WINEPREFIX="$PREFIX"
if [ ! -d "$PREFIX" ]; then
    mkdir -p "$PREFIX"
    wineboot -u 2>/dev/null || true
    sleep 2
fi
echo "Prefix ready at $PREFIX"

# Verify DLLs
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/native/nvngx.dll" ]; then
    echo "Worker (nvngx.dll) ✓"
fi
if [ -f "$SCRIPT_DIR/native/nvngx_dlssnr.dll" ]; then
    S=$(stat --format=%s "$SCRIPT_DIR/native/nvngx_dlssnr.dll" 2>/dev/null || stat -f%z "$SCRIPT_DIR/native/nvngx_dlssnr.dll" 2>/dev/null)
    echo "NR runtime (nvngx_dlssnr.dll) ✓ ($((S/1024/1024)) MB)"
fi

echo ""
echo "Setup complete. Run: ./native/run_worker.sh"