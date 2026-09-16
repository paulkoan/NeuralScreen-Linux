# M0 findings — the first gate run on the RTX 4080 SUPER

**Where:** `test-results/20260916T044806Z/` (pushed from the GPU box)
**Verdict:** FAIL — `NVSDK_NGX_D3D12_Init -> 0xBAD00001`
**But the important half passed.**

The gate and the tests need to be read separately: the pytest suite never ran on
the GPU box, and the M0 result is not the dead end the script's own verdict
implies.

---

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