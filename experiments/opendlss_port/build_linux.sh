#!/usr/bin/env bash
# Build dlss5vk on Linux. Mirrors scripts/build.ps1 (host) + scripts/build_shaders.ps1
# (shaders and PTX) with the same pinned deps, so the two produce the same artifact.
#
# What differs from Windows, and why:
#   * volk.c is C, so gcc compiles it; g++ compiling it as C++ pulls in errors that
#     have nothing to do with this project.
#   * glslang comes from the system (or $GLSLANG) instead of tools/glslang/bin/glslang.exe.
#   * -DVK_ENABLE_BETA_EXTENSIONS is required on both: VK_NV_cuda_kernel_launch lives
#     behind it in vulkan_beta.h.
#   * the MSVC-only defines (NOMINMAX, WIN32_LEAN_AND_MEAN, _CRT_SECURE_NO_WARNINGS)
#     are dropped, since nothing in src/ is Windows-specific.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

JOBS="${JOBS:-$(nproc)}"
CXX="${CXX:-g++}"
CC="${CC:-gcc}"
GLSLANG="${GLSLANG:-$(command -v glslang || command -v glslangValidator || true)}"

# --- toolchain ---------------------------------------------------------------
# fetch_tools.ps1 downloads Vulkan-Headers and volk into tools/ (glslang too, as
# a Windows release zip). On Linux they are two shallow clones at the same pinned
# tags, and glslang is expected from the system. Fetching them here rather than
# only documenting it is the difference between "go build it" and a cc1 error
# about tools/volk/volk.c that says nothing about why it is missing.
VULKAN_HEADERS_TAG="${VULKAN_HEADERS_TAG:-v1.4.363}"
VOLK_TAG="${VOLK_TAG:-vulkan-sdk-1.4.357.0}"
fetch_dep() {   # repo, tag, directory, file that proves it is there
  [ -e "$3/$4" ] && return 0
  echo "fetching $1 at $2 -> $3"
  git clone --depth 1 --branch "$2" -q "https://github.com/$1.git" "$3" \
    || { echo "could not fetch $1 (no network?): tools/ is required" >&2; exit 1; }
  [ -e "$3/$4" ] || { echo "$1 fetched but $3/$4 is absent" >&2; exit 1; }
}
fetch_dep KhronosGroup/Vulkan-Headers "$VULKAN_HEADERS_TAG" tools/Vulkan-Headers include/vulkan/vulkan.h
fetch_dep zeux/volk                   "$VOLK_TAG"            tools/volk            volk.c

inc=(-I"$root/tools/Vulkan-Headers/include" -I"$root/tools/volk" -I"$root/src")
flags=(-std=c++20 -O2 -DVK_ENABLE_BETA_EXTENSIONS -pthread)

mkdir -p build/obj build/shaders build/ptx

# --- shaders -----------------------------------------------------------------
if [ -z "$GLSLANG" ]; then
  echo "no glslang found: install it (glslang-tools / glslang on Arch) or set GLSLANG=" >&2
  echo "skipping shader compilation; the host still builds" >&2
else
  echo "glslang: $GLSLANG ($("$GLSLANG" --version 2>/dev/null | head -1))"
  failed=0
  for f in shaders/*.comp; do
    out="build/shaders/$(basename "${f%.comp}").spv"
    "$GLSLANG" -V --target-env vulkan1.3 -I"$root/shaders" "$f" -o "$out" || failed=1
  done
  [ "$failed" -eq 0 ] || { echo "shader compilation failed" >&2; exit 1; }
  echo "shaders -> build/shaders ($(ls build/shaders/*.spv | wc -l) modules)"
fi

# --- PTX kernels (VK_NV_cuda_kernel_launch) ----------------------------------
# Straight from build_shaders.ps1: the emitters are Python and portable, so the
# same invocations produce the same PTX.
gen() { python3 "$root/scripts/ptx/$1" "${@:2}"; }
for k in 64 128 256; do
  gen mlp_e4m3.py "$k" "build/ptx/mlp_e4m3_K$k.ptx" 3 1 1
done
for c in 64 128 256 512; do
  gen qkv_e4m3.py "$c" "build/ptx/qkv_e4m3_K$c.ptx" 80
done
for k in 32 64 128 256 512 1024; do
  for f in 5 13 4 8 6; do
    gen gemm2_e4m3.py "$k" "$f" "build/ptx/gemm2_e4m3_K${k}_f$f.ptx"
  done
done
for cfg in "64 4 0" "128 4 0" "256 3 80" "256 4 64"; do
  set -- $cfg
  gen ffn_e4m3.py "$1" "$2" "build/ptx/ffn_e4m3_C$1_R$2.ptx" "$3"
  gen ffn_e4m3.py "$1" "$2" "build/ptx/ffn_e4m3_C$1_R$2_proj.ptx" "$3" 1
done
for cfg in "4096 1 32 4" "1024 0 16 2" "1024 1 8 4" "1024 0 8 4"; do
  set -- $cfg
  gen gemmt_e4m3.py "$1" "$2" "$3" "$4" "build/ptx/gemmt_e4m3_K$1_f$2_p$3_s$4.ptx"
done
for cfg in "4 4" "2 8" "4 8"; do
  set -- $cfg
  gen reduce_e4m3.py "$1" "$2" "build/ptx/reduce_e4m3_s$1_f$2.ptx"
done
for cfg in "1024 6 1" "4096 5 4" "1024 8 2" "1024 5 4"; do
  set -- $cfg
  gen gemmv_e4m3.py "$1" "$2" "$3" "build/ptx/gemmv_e4m3_K$1_f$2_s$3.ptx"
  gen gemmv_e4m3.py "$1" "$2" "$3" "build/ptx/gemmv_e4m3_K$1_f$2_s$3_m96.ptx" 4 6 0 0 0 96
done
for p in 64 128 192 256; do
  gen global_attention_e4m3.py "$p" "build/ptx/global_attention_e4m3_p$p.ptx"
done
gen global_attention_stream_e4m3.py normalize build/ptx/global_normalize_e4m3.ptx
gen global_attention_stream_e4m3.py attention build/ptx/global_attention_stream_e4m3.ptx 4
# split-512 GEMMs through gemmv (96-row tiles, no partition): layer 0 (E4), contract
# (residual + E4), projection (dual); plus the unsplit ViT shapes of high resolutions
# (many token row groups): contract K4096 f5, qkv K1024 f8, projection K1024 f5
for cfg in "512 4" "512 5" "512 13" "256 5" "4096 5" "1024 8" "1024 5"; do
  set -- $cfg
  gen gemmv_e4m3.py "$1" "$2" 1 "build/ptx/gemmv_e4m3_K$1_f$2_s1_m96.ptx" 4 6 0 0 0 96
done
# fused 32-channel block variants: E4 out; E4 + pool; pre + E4 + pool; upres + E4; post + head
for f in 2 66 74 130 48; do
  gen block32_e4m3.py "$f" "build/ptx/block32_e4m3_f$f.ptx"
done

# Every emitter invocation in build_shaders.ps1 has to be here. A short list is not a
# build failure on its own: the host resolves kernels by name at run time, so a missing
# one surfaces there as "cannot read PTX kernel ..." the first time that dispatch is
# reached — a whole model in, on the GPU box, with nothing pointing back at this script.
# 78 is what the ps1 emits; if the two drift, fix this script rather than the number.
EXPECTED_PTX=78
ptx_count=$(ls build/ptx/*.ptx 2>/dev/null | wc -l)
[ "$ptx_count" -eq "$EXPECTED_PTX" ] || {
  echo "PTX: built $ptx_count of $EXPECTED_PTX kernels. build_shaders.ps1 is the list;" >&2
  echo "a missing kernel fails at run time with 'cannot read PTX kernel', not here." >&2
  exit 1
}
echo "PTX -> build/ptx ($ptx_count kernels)"

# --- host --------------------------------------------------------------------
# VK_ENABLE_BETA_EXTENSIONS must reach volk.c as well as src/: volk.h gates the
# VK_NV_cuda_kernel_launch entry points behind it, so without it on this one file
# volk never defines the pointers the sources reference and the link fails with
# five undefined references. The PowerShell build gets this for free by compiling
# volk.c in the same cl invocation as everything else.
"$CC" -O2 -DVK_ENABLE_BETA_EXTENSIONS -c tools/volk/volk.c -o build/obj/volk.o \
  -I"$root/tools/volk" -I"$root/tools/Vulkan-Headers/include"

objs=()
for f in src/*.cpp; do
  o="build/obj/$(basename "${f%.cpp}").o"
  "$CXX" "${flags[@]}" "${inc[@]}" -c "$f" -o "$o" &
  objs+=("$o")
  while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do wait -n || { echo "compile failed" >&2; exit 1; }; done
done
wait

"$CXX" "${objs[@]}" build/obj/volk.o -o build/dlss5vk -pthread -ldl
echo "built $root/build/dlss5vk"
