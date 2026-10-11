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
| PTX kernels | **78 generated** by `scripts/ptx/*.py` (pure Python, portable as-is) |
| host | **compiles and links** — `src/*.cpp` + `volk.c`, gcc/g++ 14.2, `-std=c++20` |
| artifact | `build/dlss5vk`, 600 KB |
| running it | reaches `vkCreateInstance`, fails `-9` (VK_ERROR_INCOMPATIBLE_DRIVER) — **this box has no Vulkan driver**, which is the expected boundary |

So the entire build is portable, and the only thing that needs the GPU box is *running*
it.

## The fixes, in the order they were found

The first four are all the same shape: something MSVC accepts and gcc does not.
The last two are mine, and the sixth is the one that cost a round trip on the box.

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
6. **`scripts/build_linux.sh` a third time — the PTX list stopped early.** The script's
   emitter invocations are a copy of `build_shaders.ps1`, and it was copied from a partial
   read of that file: the last two loops were missing, so **12 of 78 kernels were never
   generated** — the five `block32_e4m3_f{2,66,74,130,48}` fused 32-channel blocks and the
   seven `gemmv_e4m3_K*_s1_m96` split-512 GEMMs. The build reported success, because a
   short list is not a build failure: the host resolves kernel files by name when a
   dispatch is first reached, so it appeared on the GPU box as
   `error: cannot read PTX kernel ./build/shaders/../ptx/block32_e4m3_f74.ptx`, with nothing
   pointing back at the script. It now emits all 78 and **checks the count**, so the same
   drift fails here instead.

Nothing in `src/` needed a behavioural change. The patch is `linux-port.patch`.

## Building it on the box

```
git clone https://github.com/maanHimself/OpenDLSS-NR /home/paul/dev/OpenDLSS-NR
bash /path/to/NeuralScreen-Linux/experiments/opendlss_port/apply_to_port.sh /home/paul/dev/OpenDLSS-NR
(cd /home/paul/dev/OpenDLSS-NR && bash scripts/build_linux.sh)   # fetches tools/, then shaders + PTX + host
(cd /home/paul/dev/OpenDLSS-NR && ./build/dlss5vk stamp)          # what that binary was built from
```

**Use the script, not a hand-typed `git apply`.** It is idempotent, and that is not a
nicety: the patch *adds* files, so a second `git apply` refuses with

```
error: src/serve.cpp: already exists in working directory
```

after which `scripts/build_linux.sh` is not there to run (`bash: scripts/build_linux.sh:
No such file or directory`) and the pipeline goes on to start the *previous* build. That
happened, and the run's console said nothing about it — surprising timings from code that
existed in no checkout. The script derives the files to clear from the patch itself
instead of from a list someone typed, applies it, and records the patch's commit in
`.ns-patch-id`, which the build bakes into the binary.

Every mode that matters is then stamped, and the pipeline prints it before it runs:

```
version: repo 616c258 (clean) · worker built from patch e17393354d6e at port 9d08f41 · in sync
```

and, when they disagree, a second line that says `OUT OF SYNC` and names both patches.
`dlss5vk stamp` prints the same thing on its own, with no device and no model.

It prints three counts, and all three matter: `shaders -> build/shaders (13 modules)`,
`PTX -> build/ptx (78 kernels)`, `built .../build/dlss5vk`. A PTX count below 78 now stops
the build (see fix 6) instead of surfacing later as `cannot read PTX kernel`.

Nothing else to fetch: the script clones `Vulkan-Headers v1.4.363` and
`volk vulkan-sdk-1.4.357.0` into `tools/` — the same tags `fetch_tools.ps1` pins — if
they are not already there. It takes `GLSLANG=` if the distro's glslang is not on PATH,
`JOBS=` for the parallel compile, `CXX=`/`CC=` for a different toolchain. **The glslang
version matters**: the shaders require `GL_EXT_float_e4m3` (9 uses) and
`GL_NV_cooperative_matrix2` (4), plus `GL_KHR_cooperative_matrix` and
`GL_EXT_shader_explicit_arithmetic_types`. 16.6.0 is what upstream pins; a distro
glslang older than that will fail on the FP8 shaders specifically.

## Running it as the pipeline's worker

`dlss5vk serve` speaks the wire format of `native/dlss5-feed-host64.cpp` — the same bytes
`protocol.py` packs and unpacks — so the pipeline can point at it instead of
`wine nvngx.dll --live`, with nothing else changed:

```
NS_WORKER_CMD="/home/paul/dev/OpenDLSS-NR/build/dlss5vk serve --model /home/paul/dev/odl-model" \
  uv run python -m minimal ...
```

`Worker.start` writes the stream header, `send` writes colour + motion inline, the reader
expects `OUT1` — all three already match, so `NS_WORKER_CMD` is the whole integration.

Verified without a GPU, on the real protocol (`tests/test_native_serve.py`, and by hand
against the built binary): the header is parsed and the work size taken from it, two
bypassed frames came back byte-identical, `SHMI` is refused with `ok=0` (the documented
fallback — the client keeps sending down the pipe), an unknown command is answered rather
than ignored, and a closed stream ends the process with exit 0.

What it does **not** do, and says so instead of misbehaving:

- **No NGX upscaling.** `fullWidth`/`fullHeight` must be 0 or the work size, so a
  `--work-scale` run is rejected at the header rather than served wrong-sized frames.
- **No shared-memory channel.** SHMI is refused; the MVP never asks for it (`Worker.start`
  passes no shm), so frames stay on the pipe and the ~45ms `send` stays until the
  transport itself changes.
- **No temporal history.** The pipeline sends a zero motion field every frame
  (`minimal/loop.py`: "The MVP has no real motion vectors"), so the features are
  `preprocess.comp`'s first-frame ones — lanes 7-9 are the current proxy, not a
  reprojected previous output — and the composite is the no-history formula `parity`
  checks a fixture against. Motion is read and ignored, not silently trusted.

The model directory is the one input to this path nobody can look at: it comes out of
NVIDIA's DLL through `extract.py`, and the port's loader verifies every stage against the
manifest's `sha256` before it runs anything. Two things about that are worth knowing
before it bites:

- **The hashes are uppercase.** `src/sha256.h` formats with `0123456789ABCDEF` and `Model`
  compares the strings exactly, so a manifest written with `hashlib.hexdigest()` describes
  the bytes correctly and is still rejected with `serve: stage SHA-256 mismatch: stage00` —
  a message that names a stage and no reason. `extract.py` writes uppercase now (it did
  not, which is how this was found: turning the check on rejected every model we had ever
  extracted, and `parity`/`verify` load with verification on by default).
- **Check the directory before a run, not after.** `experiments/opendlss_weights/check_model.py
  <dir>` recomputes the hashes and checks the structural claims the manifest makes about
  itself — every tensor inside its stage, the tensors of a stage tiling it exactly — with
  no device involved.

Two knobs and one open question:

- `DLSS5VK_SERVE_SEED` (default 0) is the noise seed. Fixed by default: with no history to
  blend against, a different noise field every frame would only make the detail shimmer.
- `preprocess.comp` builds lane 10 as `style / 128`, so the header's `style` is a 1/128
  fixed-point fraction and the pipeline's default of `1` lands at ~0.008 — the neutral end.
  Whether that matches what NGX does with the same number is untested.
- `intensity` has no equivalent on this path. A run that sets it away from 1.0 is told so
  on stderr rather than having it quietly ignored.

## Measured on the GPU box (RTX 4080 SUPER, KDE/Wayland)

| run | result |
|---|---|
| `bench --width 2560 --height 1440` | **9.960 ms** median, 9.787 ms min, 249 dispatches (PTX route) |
| the same with every `DLSS5VK_PTX_*=0` | 15.799 ms median, 15.507 ms min — the PTX route is worth 5.8ms, 37% |
| for scale, the NGX worker under Wine | 28.6 ms per 1440p frame, from its own log |

`bench` is GPU time for the network with synthetic input: it measures the pass, not the
pipeline, and it says nothing about whether the pixels are right.

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

- **That the served pixels are right.** It runs — `bench` and `serve` both execute the
  whole graph on the box — but nothing has compared its output against the original. The
  next step is a frame through both paths side by side, not a bit-exact gate.
- **Bit-exactness, and why it is not the next step.** `parity` compares against recorded
  captures of the original, which the repository does not ship; we would have to record
  our own from the NGX path. The tolerance branch for an RGBA8 capture reads *recorded
  16-lane features*, and three of those lanes are seed-derived Gaussian noise:
  `native/dlss5-feed-host64.cpp` sets `LocalToneStrength`, `LocalStructureStrength`,
  `SkinStructureStrength`, `Style` and `UseAutoMask` — the conditioning — but **no seed**,
  so NGX picks its own noise and the input side cannot be reconstructed from it. A seed
  sweep is the experiment that would settle it (the manifest's seed is one JSON field);
  until then, bit-exactness is blocked behind an unknown, not behind effort.
- **The conditioning mapping.** Our knobs reach `preprocess.comp`'s lanes by name
  (`style` as 1/128, `local_tone` and friends as strengths, `auto_mask` switching what the
  last three lanes mean), but whether our neutral values are the port's neutral values is
  untested. That is a calibration question, and it shows up as a look difference.
- **The model directory.** `experiments/opendlss_weights/extract.py --out` emits one from
  the DLL (153 tensors, 71 blocks, 140.84 MiB). Its *lengths* match upstream's documented
  layout exactly, and the port's loader accepts it and runs the whole network — which is
  not the same as the *values* being right, since `bench` never looks at them.
