# OpenDLSS-NR on Linux: it builds, and here is what it took

OpenDLSS-NR (MIT) is a Vulkan reimplementation of the DLSS 5 NR network — the same
71-block network `nvngx_dlssnr.dll` carries — reporting **12.6ms at 2560x1440** for
the whole network on a 4070 SUPER, against the **34.5ms** our worker spends per
1440p frame through NGX under Wine. Its README says "Windows" in the requirements,
so the question was how much of that is the API and how much is the build.

**Answer: none of it is the API.** The tool has no window and no surface — its modes
are `bench`, `profile`, `parity`, `verify`, `shaderinfo` — and only two files mention
Windows at all (`demo/crash_report.cpp`, and `find_vcvars.ps1`). It builds on Linux.

## Verified here, with versions

| step | result |
|---|---|
| glslang 16.6.0 | built from source for this test (`cmake -DENABLE_OPT=OFF`) |
| shaders | **13/13 compile** to SPIR-V, `-V --target-env vulkan1.3` |
| PTX kernels | **66 generated** by `scripts/ptx/*.py` (pure Python, portable as-is) |
| host | **compiles and links** — `src/*.cpp` + `volk.c`, gcc/g++ 14.2, `-std=c++20` |
| artifact | `build/dlss5vk`, 600 KB |
| running it | reaches `vkCreateInstance`, fails `-9` (VK_ERROR_INCOMPATIBLE_DRIVER) — **this box has no Vulkan driver**, which is the expected boundary |

So the entire build is portable, and the only thing that needs the GPU box is *running*
it.

## The four fixes, all of them MSVC-only assumptions

1. **`src/kernels.h` — `= Chain()` as a default argument.** `Chain` has default member
   initializers, so a default argument that constructs one is parsed while `Chain` is
   still incomplete. MSVC accepts it; GCC and clang reject it with
   `default member initializer for 'nr::Kernels::Chain::waitRows' required before the
   end of its enclosing class`. Fixed by declaring `static const Chain& emptyChain()`
   and defaulting to that — same thing to every caller.
2. **`src/vk_context.h` — `memcpy` used without `<cstring>`.** MSVC's headers pull it in
   transitively.
3. **`src/nr_model.h` — the same.** Two headers, four of the nine errors.
4. **`scripts/build_linux.sh` — `VK_ENABLE_BETA_EXTENSIONS` must reach `volk.c`.** The
   PowerShell build compiles `volk.c` in the same `cl` invocation as everything else, so
   the define applies to it too. Separating the compile (which a Makefile or a script
   will do) drops it, and then `volk.h` never declares the
   `VK_NV_cuda_kernel_launch` entry points: five undefined references at link.
5. **`scripts/build_linux.sh` again — it has to fetch `tools/` itself.** `fetch_tools.ps1`
   does that on Windows; the first version of this script assumed it had been done and
   died with `cc1: fatal error: tools/volk/volk.c: No such file or directory`, which names
   the file but not the reason. It now clones the same two pinned tags itself, and refuses
   loudly if it cannot.

Nothing in `src/` needed a behavioural change. The patch is `linux-port.patch`.

## Building it on the box

```
git clone https://github.com/maanHimself/OpenDLSS-NR
cd OpenDLSS-NR
git apply /path/to/linux-port.patch
bash scripts/build_linux.sh                     # fetches tools/, then shaders + PTX + host
```

Nothing else to fetch: the script clones `Vulkan-Headers v1.4.363` and
`volk vulkan-sdk-1.4.357.0` into `tools/` — the same tags `fetch_tools.ps1` pins — if
they are not already there. It takes `GLSLANG=` if the distro's glslang is not on PATH,
`JOBS=` for the parallel compile, `CXX=`/`CC=` for a different toolchain. **The glslang
version matters**: the shaders require `GL_EXT_float_e4m3` (9 uses) and
`GL_NV_cooperative_matrix2` (4), plus `GL_KHR_cooperative_matrix` and
`GL_EXT_shader_explicit_arithmetic_types`. 16.6.0 is what upstream pins; a distro
glslang older than that will fail on the FP8 shaders specifically.

## The GPU side, already checked

`vulkaninfo` on the box reports every extension the project requires:

```
VK_KHR_cooperative_matrix        extension revision 2
VK_NV_cooperative_matrix         extension revision 1
VK_NV_cooperative_matrix2        extension revision 1
VK_EXT_shader_float8             extension revision 1
VK_NV_cuda_kernel_launch         extension revision 2
```

Two caveats before trusting that: an advertised extension is not an enabled feature, so
what needs checking is the *features and properties* — that FP8 works with E4M3/E5M2
components and f16 accumulation at this network's shapes. And `vkBasalt` is loaded as an
implicit layer on this box (twice, from two json files — the loader warns about the
duplicate); it injects a post-processing pass into every Vulkan app, so it should be
disabled before any measurement means anything.

## What is still unverified

- **That it runs correctly on the Linux driver.** Building is not running. The feature
  bits above are the gate.
- **Bit-exactness.** `parity` compares against recorded captures of the original, which
  the repository does not ship. We would have to record our own from the NGX path we
  already have working — which is the one advantage we have over anyone else attempting
  this.
- **The model directory.** `experiments/opendlss_weights/extract.py --out` emits one from
  the DLL (153 tensors, 71 blocks, 140.84 MiB). Its *lengths* match upstream's documented
  layout exactly, but the stage split is ours to define and no byte-level round trip has
  been shown.
