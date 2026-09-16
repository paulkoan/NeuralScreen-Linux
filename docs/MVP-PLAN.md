# NeuralScreen Linux — MVP Plan (capture → NR pass → display)

**Goal:** one loop. A frame goes in, the DLSS5 neural pass runs on it, the frame
comes out on screen. Nothing else.

**Non-goals for the MVP** (add later, in this order): optical-flow motion guides,
menu/overlay UI, hotkeys, tray, recording, screenshots, window mode, GFN
window-follow, presets, i18n, Spout, PipeWire/Wayland capture, multi-monitor.

The MVP is a *separate, small* code path (`minimal/`). It does not modify or
depend on the existing Windows-derived modules, so nothing that works today can
break while we prove the core.

---

## Confidence: what is verified vs. assumed

**Verified on the build box (headless, no GPU, no Wine):**

- `native/nvngx.dll` is a PE32+ **executable**, not a DLL. It statically imports
  `SpoutDX.dll`, `d3d11`, `d3d12`, `dxgi`, `D3DCOMPILER_47`, `dwmapi`, `ole32`,
  `USER32`, `ADVAPI32`, MSVC runtime. → `SpoutDX.dll` and `Spout.dll` must be
  beside it at launch. They are, and they are tracked in git.
- The worker `LoadLibraryW`s `nvngx_dlssnr.dll` from its own directory
  (`NS_NR_DLL` overrides). That 159 MB file is gitignored — **you must supply it.**
- `--test` mode exists and is a self-contained gate (see M0).
- Wire-protocol struct sizes match the C++ `static_assert`s exactly:
  header 64 B, frame 24 B, result 28 B, shm 88 B. Same numbers both sides.
- The `--live` **pipe path** is real: `FRAME_MAGIC` + 24-byte header, then colour
  and motion inline; the worker answers `OUT_MAGIC` (28 B) plus pixels.
- Capture (`mss`/X11) and SDL2 presentation both run headless under Xvfb here.

**Assumed / unproven — the actual risks:**

- **Will NGX initialise at all under Wine + VKD3D on your RTX box?** Unproven.
  This is the largest risk and the reason M0 exists. Everything else is cheap if
  this fails.
- Will `D3D12CreateDevice` succeed under VKD3D-proton on your driver?
- Iceberg risk: DLSS5-NR is a *leaked* runtime (310.8.0). Its support matrix is
  RTX 20–50 with sm_75/86/89/120 kernels; your card's compute capability must be
  in that set.
- Pipe-path throughput at 1440p/4K is untested. Fine for correctness; may be too
  slow for real use — that is what shared memory is for, and it is a later task.

---

## Architecture (MVP)

```
  minimal/capture.py ──RGBA frame──▶ minimal/worker.py ──▶ wine nvngx.dll --live
            ▲                                                      │
            │                    OUT_MAGIC + processed RGBA ◀──────┘
            │
  minimal/loop.py ────▶ minimal/display.py ─▶ SDL2 window
```

- `minimal/capture.py` — X11 screen capture via `mss`, returns `(H, W, 4)` uint8
  **RGBA**. No PipeWire yet.
- `minimal/worker.py` — launches the worker (`native/run_worker.sh` by default,
  overridable so tests can point at the mock), sends the header, sends frames,
  reads results. Reuses `protocol.py`'s `WorkerReader` and `send_frame` — that
  code already matches the C++ byte for byte.
- `minimal/display.py` — SDL2 borderless/streaming-texture window. Headless mode
  for tests.
- `minimal/loop.py` — wires the three together; `--frames N` runs a bounded loop.
- `minimal/__main__.py` — `python -m minimal`.

**Transport decision:** pipe only. No `SharedFrameBuffer` in the MVP — it uses
the Windows-only `mmap(..., tagname=...)` kwarg and Wine's named-mapping
namespace is not POSIX shm. The pipe path is the one that works; optimise later.

**Motion vectors:** zero motion at work resolution for M2 (frozen MV). Real
optical flow is M5. This is enough to prove the pass runs and the picture comes
back.

---

## Milestones — each one is a test, not an opinion

### M0 — Environment gate (runs on your box) ◀ **start here**

Script: `tools/m0_env_gate.sh`.

Runs `wine native/nvngx.dll --test`. This needs no game, no display window and no
Python: it builds a D3D12 device, creates NGX feature 18, and runs 300 evaluates
on a synthetic 640×360 pattern.

**PASS** = exit 0 **and** `dlss5-feed-host.log` contains
`[pure] direct feature 18 ready` **and** `--test finished: N/300` with `N >= 250`.

If this fails, stop the port and read the log — the failure code names the stage
(`Init_NGX` return, `D3D12CreateDevice` HRESULT, `no NVIDIA adapter found`).
Nothing downstream is worth building until this passes.

### M1 — Pipeline skeleton against a mock worker (runs here)

`tests/mock_worker.py` speaks the same binary protocol as the real worker and
applies a deterministic transform (channel swap + brightness), so the whole
Python pipeline can be exercised end to end with no GPU.

Tests: protocol struct sizes vs. the C++ `static_assert`s; header/frame/result
round-trip; capture returns correctly-shaped RGBA; display presents without error;
loop over N frames returns N distinct processed frames.

### M2 — One real frame through the real worker (your box)

`python -m minimal --frames 1 --save-before before.png --save-after after.png`.
**PASS** = same dimensions, `after != before`, no protocol desync, worker exit 0.

### M3 — Live loop with display (your box)

`python -m minimal`. Capture → NR pass → fullscreen SDL2 window, bounded by
`--frames` or a quit key. **PASS** = visible processed desktop, clean exit.

### M4 — Teardown

Worker exits on stdin EOF, no orphaned `wine` process, no stuck shm. Test:
start, stop, `pgrep -f nvngx` is empty.

### M5+ — after the MVP works

Real motion vectors (`guides.py` optical flow), then shared memory for speed,
then the existing UI/hotkeys/recording modules.

---

## Test-driven workflow

Every milestone is written as a failing test first, then made to pass.

- **Unit tests run here** (no GPU, no Wine): `tools/run_tests.sh`
- **Integration tests run on your box** and report through the same channel.

### Results channel

`tools/run_tests.sh --report` writes `test-results/<UTC-timestamp>/` containing
`report.md` (human summary + PASS/FAIL per test) and `raw/` (full logs, including
`dlss5-feed-host.log`). You commit and push that directory; I read it directly.
For one-liners you can paste, but logs travel as files so nothing is lost to
truncation.

`tools/m0_env_gate.sh` writes into the same `test-results/` tree, so M0 and the
test suite land in one place.

---

## What I need from you to run M0

1. `native/nvngx_dlssnr.dll` present on your box (159 MB, from the v1.6.0 release
   archive — it is gitignored and does not come down with a clone).
2. Wine + VKD3D-proton installed.
3. Run `tools/m0_env_gate.sh` and push the resulting `test-results/` directory.