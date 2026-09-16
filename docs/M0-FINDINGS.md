# M0 findings — the gate runs on the RTX 4080 SUPER

Two runs so far. The error code is walking forward, which is the point of the
gate: each failure names the next missing piece.

| run | result | meaning |
|---|---|---|
| `20260916T044806Z` | `0xBAD00001` FAIL_FeatureNotSupported | NGX Core not found at all |
| `20260916T051433Z` | `0xBAD00002` FAIL_PlatformError | NGX Core now loads; NVAPI cannot report the GPU to it |
| `20260916T063248Z` | `0xBAD00002` still, but NVAPI now *explains itself* | DXVK's dxgi.dll was never installed — the setup had only been run with `--check` |
| `20260916T064324Z` | `0xBAD00002` unchanged | a dxgi.dll **was** present, so the install was skipped — but it was Wine's builtin, not DXVK's |
| `20260916T065756Z` | `0xBAD00004` FAIL_FeatureNotFound | **init and feature 18 create now succeed**; the failure has moved to evaluate |

**What the first run proved and the second confirmed** — the expensive half:

```
[host] adapter 0: NVIDIA GeForce RTX 4080 SUPER vendor=0x10DE
[pure] standalone D3D12 device ready; no swapchain or carrier modules
```

Wine runs the PE with all its static imports, DXGI enumerates the card at vendor
`0x10DE` (the worker rejects anything else), and `D3D12CreateDevice` succeeds.
D3D12 over Wine + VKD3D works on this machine. That was the risk that could have
killed the port outright; it is cleared.

---

# Round 5 — M0 answers YES, and the failure moves to evaluate

The DXVK fix landed and it was the unlock. From `20260916T065756Z`:

```
✓ wine: wine-11.17 (Staging)          ✓ GPU: RTX 4080 SUPER, 615.71.09, cc 8.9
✓ installed DXVK dxgi.dll (5.2M)      ✓ installed vkd3d-proton d3d12core.dll (5.7M)
     after: DXVK v3.1.1 / vkd3d-proton 3.0.1 / dxvk-nvapi v0.9.2

info:nvapi64:DXVK-NVAPI v0.9.2 NVAPI gcc 16.1.0 x86_64 release (nvngx.dll)
info:nvapi64:NvAPI Device: NVIDIA GeForce RTX 4080 SUPER (615.71.9)
info:nvapi64:<-NvAPI_Initialize: OK
[host] NVSDK_NGX_D3D12_Init -> 0x00000001 (Success)
[pure] direct DLSSNR Init_Ext -> 0x00000001 (Success)
[pure] direct feature 18 ready: 640x360 preset=0 result=0x00000001
[host] evaluate failed 0xBAD00004 (?)
[host] --test finished: 0/300 evaluates succeeded
```

**The make-or-break question is answered: NGX initialises under Wine, and feature
18 is created.** Every previous round failed at or before init. This is the first
run that got past it, and `0xBAD00002` is gone.

## The new failure: 0xBAD00004 FAIL_FeatureNotFound

The host's own `NgxResultName` table has no case for it, hence the `(?)`. NVIDIA's
header settles it (`NVIDIA/DLSS`, `include/nvsdk_ngx_defs.h`):

```
NVSDK_NGX_Result_FAIL_FeatureNotFound = NVSDK_NGX_Result_Fail | 4,   // 0xBAD00004
```

"Feature not found" for a feature that was created successfully two lines earlier
is worth reading closely, because **create and evaluate do not go to the same
place**:

| step | symbol | comes from |
|---|---|---|
| create | `g_nr_create` | `GetProcAddress(nvngx_dlssnr.dll, "NVSDK_NGX_D3D12_CreateFeature")` |
| evaluate | `NVSDK_NGX_D3D12_EvaluateFeature_C` | the SDK helper's Core entry point |

`NGX_D3D12_EVALUATE_DLSS_EXT` is a `static inline` in the SDK's
`nvsdk_ngx_helpers_d3d.h`: it packs the eval params into the parameter block and
its last line is a call to `NVSDK_NGX_D3D12_EvaluateFeature_C` — the **Core**
entry, not the NR runtime's. So the handle is registered with one runtime and
evaluated by the other, and the Core does not know it.

This also explains the one loose end from round 1: the host's import table has
**no NGX symbols at all** (`objdump -p native/nvngx.dll` — 25 DLLs, none of them
NGX). Every NGX entry point is resolved by name at runtime, which is why
`NVSDK_NGX_D3D12_*` shows up as string literals in the binary.

## The experiment

`NS_NGX_VIA_CORE=1` is upstream's own switch (see the comment above the
`NS_NGX_VIA_CORE` block in `dlss5-feed-host64.cpp`): it routes create *and*
evaluate through NGX Core. If the mismatch above is the whole story, via-core
should get past evaluate — and it also tests upstream's stated goal of dropping
the "the process must be named nvngx.dll" constraint.

So the gate now takes `--via-core`, and `run_tests.sh --report --m0` runs **both
variants in one report**:

| artifact | variant |
|---|---|
| `raw/m0_gate.txt` | direct (default) |
| `raw/m0_gate_via_core.txt` | `NS_NGX_VIA_CORE=1` |
| `raw/via-core/` | that variant's own env + worker log |

Both exit codes are printed in the run's stdout.

## Confidence

Init and feature creation are **verified**, not inferred: both report
`0x00000001 (Success)` with the GPU named by NVAPI. The evaluate diagnosis is
**inferred** from the two call sites and confirmed against NVIDIA's header for
the result code; the variant run is what will settle it.

If via-core also fails at evaluate, the next suspects are the `[arch] patch`
(`architecture 0x190 (spoofed to the DLL's accepted value)` — the host already
patches NGX's view of the GPU, which is a strong smell) and the eval params
struct: `Evaluate()` fills `NVSDK_NGX_D3D12_DLSS_Eval_Params`, which is the
super-resolution shape, for what is feature 18.

## Also fixed this round

`run_tests.sh` copied `native/dlss5-feed-host.log` into `raw/` **before** the
gate produced it, so every report listed the worker log as an artifact it did
not carry. It is now copied after the gate, for both variants.

---

# Round 4 — presence is not provenance (kept)

The round-3 fix worked (the setup applied: `copied nvngx.dll -> system32`,
`4/4 registry values written`), but `0xBAD00002` did not move. The setup said:

```
✓ dxgi.dll present (248K)      ✓ d3d11.dll present (460K)
✓ d3d12core.dll present (52K)  ✓ DXVK dxgi.dll + d3d11.dll already present
```

…and dxvk-nvapi still said *"Querying Vulkan entry point from DXGI factory
failed, please ensure that DXVK's dxgi.dll (version 2.1 or newer) is present"*.

Both statements were true. There **was** a `dxgi.dll` in `system32` — it was
just **not DXVK's**. Downloading the pinned releases settles it:

| file | the pinned release | what was in the prefix |
|---|---|---|
| DXVK `dxgi.dll` | 5,414,926 B (5.4 MB) | 248K |
| DXVK `d3d11.dll` | 7,483,406 B (7.4 MB) | 460K |
| vkd3d-proton `d3d12core.dll` | 5,963,790 B (5.9 MB) | 52K |
| dxvk-nvapi `nvapi64.dll` | 2.0 MB | 2.0 MB ✓ |

Those are Wine's builtins. The check was `[ -s "$SYS32/$f" ]` — file exists,
therefore fine — so the installer skipped the very files it existed to install.
Same class of mistake as round 3 (a diagnostic that could not see what it was
looking for), one layer down.

## The fix: identify the layers, don't just find them

Each layer is now identified by markers taken from the real binaries, verified
against them before landing:

| layer | marker | version |
|---|---|---|
| DXVK | `strings dxgi.dll \| grep DXVK` — 34 hits in 3.1.1, 0 in anything else | `v3.1.1`, and it must be ≥ 2.1 as dxvk-nvapi requires |
| vkd3d-proton | `strings d3d12core.dll \| grep vkd3d-proton` — 161 hits | `3.0.1` |
| dxvk-nvapi | `strings nvapi64.dll \| grep DXVK-NVAPI` | `v0.9.2` |

Anything failing that test is installed or reinstalled, and the setup says which
test failed and why (including the size comparison, so "that is Wine's builtin"
is a claim with a number behind it). `--force-layers` reinstalls all three
regardless, for when the check itself is suspect.

The replaced DLLs are kept as `*.bak_replaced` rather than overwritten silently.

## Also in this round

`tools/run_tests.sh --push` commits `test-results/<timestamp>/` and pushes it.
Scoping was verified in a throwaway repository: it commits the report directory
and nothing else, and on a failed push it says so and leaves the commit local
instead of reporting success.

## Confidence

The failure is now pinned by file size, not inference: the wrong DLLs are
identifiable and the right ones are downloadable and identifiable. If those
three markers pass and `NvAPI_Initialize` still fails, the next suspects are the
override actually taking effect at load time and Wine's own `vulkan-1`.

---

# Round 3 — `0xBAD00002`, and NVAPI finally says why (kept)

The round-2 changes took effect: dxvk-nvapi loaded (`DXVK-NVAPI v0.9.2 ... x86_64
release (nvngx.dll)`) and `DXVK_ENABLE_NVAPI=1` was clearly in force, because it
was logging at all. Then it stated the cause itself:

```
nvapi64:Querying Vulkan entry point from DXGI factory failed, please ensure
         that DXVK's dxgi.dll (version 2.1 or newer) is present
nvapi64:<-NvAPI_Initialize: NVIDIA or other suitable device not found or
         initialization failed
```

**DXVK was never installed.** dxvk-nvapi reaches the Vulkan entry point through
DXVK's `dxgi.dll` extension points; without that file `NvAPI_Initialize` fails,
NGX Core gets no platform answer, and init returns `0xBAD00002`. `tools/
wine_ngx_setup.sh --check` showed it plainly — `vkd3d-proton missing`, and no
DXVK files at all — but its section 4 was skipped as a check.

That was a **workflow bug in my own harness**, not a missing piece of
understanding. `tools/run_tests.sh --report --m0` ran the setup with `--check`,
so following my own instructions diagnosed the prefix without ever configuring
it. The gate then reported the same `0xBAD00002` with nothing saying the setup
had never been applied.

Fixes:

- `run_tests.sh --m0` now runs `wine_ngx_setup.sh` **without** `--check` (it is
  idempotent), snapshots the prefix afterwards, and stores the setup output as
  `raw/wine_ngx_setup.txt`.
- The setup script reports the presence of every layer file in **both** modes.
  A `--check` that silently omitted that is how this went unnoticed for a round.
- The gate was reading only `dlss5-feed-host.log` for its NVAPI section, so it
  printed "no NVAPI output at all" while the answer sat in Wine's console — the
  worker's stage logs and dxvk-nvapi's `nvapi64:` lines go to different streams.
  It now captures both.
- The gate detects that exact dxvk-nvapi message and quotes the fix back.
- `tests/test_worker_env_consistency.py` now also covers
  `tools/wine_ngx_setup.sh`, and it immediately earned its keep: it failed on
  this change because the setup script never mentioned `DXVK_ENABLE_NVAPI`.

## What to run now

```bash
git pull
tools/wine_ngx_setup.sh          # no --check: this is the step that installs DXVK
tools/m0_env_gate.sh
```

or simply `tools/run_tests.sh --report --m0`, which now does both.

## Confidence

Higher than round 2, because this failure was not inferred — dxvk-nvapi printed
the cause and the missing file was independently visible in the setup snapshot.
It is still not proven until the gate exits 0. If `NvAPI_Initialize` succeeds
and init passes, the next thing to watch is **feature 18 create**, where the
CuBIN path needs dxvk-nvapi ≥ 0.9.2 against vkd3d-proton ≥ 3.0.1.

---

# Round 2 — `0xBAD00002` FAIL_PlatformError (kept)

Round 1's diagnosis was right and its fix worked: the registry entry took effect
(`NGXCore registry: FullPath REG_SZ Z:\usr\lib\nvidia\wine`), and the error moved
on. Round 2 is a *different* failure, not a repeat.

`0xBAD00002` at the init stage means NGX Core loaded and ran, then asked the
platform about the GPU and did not get a usable answer. Under Wine that answer
has to come from **dxvk-nvapi**, and dxvk-nvapi's requirements are explicit in
its own README (`## Wine / Wine-Staging`):

- copy `nvapi64.dll` / `nvofapi64.dll` into the prefix's `system32`
- **copy `nvngx.dll` / `_nvngx.dll` into `system32`** (round 1 did this)
- ensure **DXVK**'s `dxgi.dll` is installed and used — *"Using Wine's D3D11 or
  DXGI implementation will fail"*
- **set `DXVK_ENABLE_NVAPI=1`** — *"to disable DXVK's nvapiHack in DXVK"*

Round 1's overrides covered `d3d12,d3d12core,nvapi64,dxgi` but **not `d3d11`**,
and `DXVK_ENABLE_NVAPI` was never set — the GPU box's environment dump confirms
it: the variable is simply absent.

`native/run_worker.sh` and `tools/m0_env_gate.sh` now set:

```
WINEDLLOVERRIDES="d3d12=n,b;d3d12core=n,b;d3d11=n,b;dxgi=n,b;nvapi64=n,b;nvofapi64=n,b;nvngx_dlssnr=n"
DXVK_ENABLE_NVAPI=1
DXVK_NVAPI_LOG_LEVEL=info        # so NvAPI_Initialize shows up in the output
```

and `tools/wine_ngx_setup.sh` now **installs** the layers rather than only
reporting them — DXVK `3.1.1`, vkd3d-proton `3.0.1`, dxvk-nvapi `0.9.2` (the
versions the reference project pins; `0.9.2` is the one that passes 64-bit CuBIN
calls to vkd3d-proton `3.0.1+`, which matters at feature-create).

The gate now prints every `NvAPI_*` line it sees. If NVAPI never answered, that
is the next thing to chase, and it will say so instead of leaving us to infer it.

## Confidence

Round 1 was a hypothesis confirmed by the change in error code. Round 2 is the
same kind of step: the binding constraint moved from "NGX Core missing" to
"NGX Core cannot see the platform", and dxvk-nvapi is the only thing under Wine
that can supply the platform answer. It is still not proven until the gate exits
0.

---

## Round 1 detail (kept — the reasoning is still what round 2 builds on)

**Where:** `test-results/20260916T044806Z/` (pushed from the GPU box)
**Verdict:** FAIL — `NVSDK_NGX_D3D12_Init -> 0xBAD00001`

The gate and the tests need to be read separately: the pytest suite never ran on
the GPU box (`No module named pytest`), and the M0 result was not the dead end
the script's own verdict implied.

## What passed (this is the expensive part)

Everything up to NGX was healthy, on Wine 11.17 Staging, driver 615.71.09,
RTX 4080 SUPER (compute capability 8.9 — inside the runtime's sm_75/86/89/120
kernel set):

```
[host] adapter 0: NVIDIA GeForce RTX 4080 SUPER vendor=0x10DE
[host] DRED settings unavailable (settings1=0x80004002, settings=0x80004002)
[pure] standalone D3D12 device ready; no swapchain or carrier modules
```

- Wine runs the PE, with all its static imports (`SpoutDX.dll` → `Spout.dll`)
- **Windows DXGI adapter enumeration works**: the NVIDIA card is seen, vendor
  `0x10DE` (the worker rejects anything else)
- **`D3D12CreateDevice` works** — a real D3D12 device on the NVIDIA adapter
- `--test` mode is reachable and the worker runs its own banner

That clears the two risks that would have killed the port outright. D3D12 on top
of Wine + VKD3D on this machine works.

## What failed, and why

```
[host] NVSDK_NGX_D3D12_Init -> 0xBAD00001 (?)
[host] Init_with_ProjectID  -> 0xBAD00001 (?)
[host] NGX unavailable
0024:fixme:d3dkmt:NtGdiDdDDIQueryAdapterInfo type 48 not handled.
```

`0xBAD00001` is `FAIL_FeatureNotSupported`. **At the init stage it does not mean
"unsupported GPU"** — the card is supported. It means NGX Core was never found.

`native/nvngx.dll` statically links NVIDIA's own NGX loader. Its strings name the
three paths it tries:

```
NGXGetPathUsingQAI
NGXGetPathFromRegistry
NGXCore not found next to the application
```

Under Wine only one of the three can possibly work:

| path | why it fails |
|---|---|
| `NGXGetPathUsingQAI` | needs the D3DKMT adapter query — that is the `type 48 not handled` line above. Unimplemented in Wine. |
| "next to the application" | name collision. The worker's own file **is** `nvngx.dll`, so the loader finds a module with no exports. |
| `NGXGetPathFromRegistry` | **the only one left** — and nothing had written the key. |

Two further pieces were missing from the launcher:

- `WINEDLLOVERRIDES` only set `nvngx_dlssnr=n`. Without
  `d3d12,d3d12core,nvapi64,dxgi` as native-first, Wine loads its **builtin**
  d3d12 (old vkd3d) and builtin nvapi64, and NGX cannot reach the physical GPU
  through them.
- `DISPLAY` must be set. DXVK cannot create a Vulkan instance without one.

## The fix

`tools/wine_ngx_setup.sh`:

1. find the driver's NGX bridge DLLs. **On Arch `nvidia-utils` already ships
   them** at `/usr/lib/nvidia/wine/{nvngx,_nvngx}.dll` — nothing to download.
   Elsewhere they come from the matching `.run` (`--extract-only`).
2. copy them into the prefix's `system32` and into a dedicated bridge directory
   (dedicated because of the name collision above — never next to the worker).
3. write the four registry values the loader consults:
   ```
   HKLM\SOFTWARE\NVIDIA Corporation\Global\NGXCore                    FullPath
   HKLM\SOFTWARE\NVIDIA Corporation\Global\NGXCore                    NGXPath
   HKLM\System\CurrentControlSet\Services\nvlddmkm\NGXCore             NGXPath
   HKLM\System\CurrentControlSet\Services\nvlddmkm\Parameters\NGXCore  NGXPath
   ```
4. report the translation-layer versions.

Then `native/run_worker.sh` and `tools/m0_env_gate.sh` set:

```
WINEDLLOVERRIDES="d3d12,d3d12core,nvapi64,dxgi=n,b;nvngx_dlssnr=n"
```

## Where this came from

Not guesswork — a project already doing exactly this on Linux, whose findings
match ours line for line:

- **LQCCS/ComfyUI-DLSS5NR-Wine** — DLSS 5 NR (feature 18) on Linux via Wine +
  vkd3d-proton, `docs/FINDINGS.md`. Its §⑤ is the DLL-override trap, §⑦ is the
  NGX-loader trap (same `NGXGetPathUsingQAI` / `NGXGetPathFromRegistry` strings,
  same conclusion: only the registry works), and its `install/setup_prefix.sh`
  is the source of the registry recipe above.
- **bmitch87/DLSS5VKLayer#18** — "CreateFeature(18) returns 0xbad00001 because
  the snippet cannot reach NVAPI — fixed by dxvk-nvapi + DXVK dxgi in the
  managed prefix".

## Still open after this fix

- **dxvk-nvapi ≥ 0.9.2 + vkd3d-proton ≥ 3.0.1.** The reference project needed
  both for 64-bit CuBIN calls; 0.9.1/3.0.0 gave
  `NvAPI_D3D12_CreateCubinComputeShaderExV2: Invalid pointer`. This bites at
  *feature create*, after init — so it is the next thing to look at if init
  succeeds and feature 18 does not.
- **The swapchain path needs a real refresh rate.** The reference project hit an
  integer divide-by-zero in DXVK's dxgi with Xvfb's `0.00 Hz` RandR output and
  fixed it with Xorg + the dummy driver at a real 60 Hz modeline. `--test` opens
  no swapchain, so M0 cannot hit this — but the live display loop (M3) can, and
  that is worth knowing before it looks like a NeuralScreen bug.
- The GPU box's pytest run produced only `No module named pytest`; that venv has
  no pytest. `tools/run_tests.sh` now installs it (or explains how) instead of
  writing an empty report.