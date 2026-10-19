# DLSS-NR "310.8.16.0" investigation — Q1 answer and Part B disposition

Card: `t_a31be3eb` ("Answer Q1 and write acquisition/measurement spec for 310.8.16.0"),
child of `t_2cab16c2`. Written 2026-10-19 from `/opt/data/neuralscreen-linux` (main).
Answers question 1 from the binary itself; disposes of Part B. **No port run was made and no run
was queued from this card.**

## Part A — Q1 answered

> Is `310.8.16.0` a different build from the bundled one, or is `310.8.0` the README's shorthand
> for a DLL whose full file version is `310.8.16.0`?

**Neither. The bundled DLL's full file version is exactly `310.8.0.0`, and `310.8.16.0` is not a
distinct build.**

### Binary grounding

Artifact: `native/nvngx_dlssnr.dll`
- 165,840,496 bytes, sha256 `dcc0dc2414aedec4a8e084647070383be068554042587180c20c784d4772d36f`
- PE32+ (`0x20b`), 7 sections; RT_VERSION blob 1184 bytes at file offset `0x1149cc0`.

VS_FIXEDFILEINFO (file offset `0x1149ce8`), read with the pure-Python PE parser:

| Field | Raw | Decoded |
|---|---|---|
| `dwSignature` | `0xfeef04bd` | VS_FIXEDFILEINFO |
| `dwFileVersionMS` | `0x01360008` | **310.8.0.0** |
| `dwFileVersionLS` | `0x00000000` | |
| `dwProductVersionMS` | `0x01360008` | **310.8.0.0** |
| `dwProductVersionLS` | `0x00000000` | |

`0x01360008` = 0x0136.0008 = 310.8; `LS` = 0 → **310.8.0.0**. `StringFileInfo` `FileVersion` and
`ProductVersion` both read the string `310,8,0,0`. No field contains `16`.

Reproduce either of:

```
python3 .../t_057cec57/read_version_manual.py native/nvngx_dlssnr.dll
strings -a -el native/nvngx_dlssnr.dll | grep -A1 -E 'FileVersion|ProductVersion'
```

Both give `310,8,0,0`. A scan of the whole 158 MB binary for `310.8.16` (ascii and utf-16) returns
nothing; the only version-shaped strings present are the two `310,8,0,0` values. (Reproduced
independently in this card's run: same sha256, same decoded `FILEVERSION = 310.8.0.0`,
`PRODUCTVERSION = 310.8.0.0`.)

### What the answer rules out / rules in

1. **Ruled out:** "`310.8.0` is shorthand for a DLL whose full version is `310.8.16.0`." The DLL's
   full version is `310.8.0.0`; there is no `16`. The repo's `310.8.0` is exact.
2. **Ruled out:** "`310.8.16.0` is a distinct build." No source — repo, binary, or public leak
   coverage — names it. Its only traceable origin is the human's Telegram DM (2026-10-19 08:42:40
   UTC; see sibling `t_93b39d01`). Public sources name the newer, faster runtime **`310.9.16.0`**
   (WCCFtech, VideoCardz, NoobFeed); "`310.8.16.0`" reads as a conflation of "`310.8.x`" and
   "`310.9.16.0`" — the "16" being the second field of the latter.

### Documentation correction — none required

The card's Part A says "if the two are the same build, the outcome is a documentation correction."
They are not the same build, so no correction fires. Concretely, the repo's version prose is already
correct and does not imply two runtimes:

| File:line | Current wording | Verdict |
|---|---|---|
| `README.md:260` | "...is the leaked **310.8.0** runtime carrying sm_75/86/89/120 kernels (RTX 20-50)" | correct |
| `README.md:264` | "NVIDIA's `nvngx_dlssnr.dll` is the leaked **310.8.0** runtime" | correct |
| `TECHNICAL.md:376` | "The bundled build is the leaked **310.8.0** runtime (from the RankFTW/rhi-repo mirror)" | correct |
| `docs/MVP-PLAN.md:39` | "Iceberg risk: DLSS5-NR is a *leaked* runtime (**310.8.0**)" | correct |

`git log --all -S "310.8.16"` returns zero commits; the string appears in the working tree only in
the triage card `t_2cab16c2` and the claim sheet `docs/dlss-nr-performance-claim-sheet.md`, both of
which already frame it as an unanchored belief. There is nothing to correct in the repo's own prose.

## Part B — not applicable

Part B is conditioned on 310.8.16.0 being a distinct build ("if 310.8.16.0 is a distinct build, a
spec exists for acquiring it..."). Part A establishes it is not. There is no artifact to acquire and
no version to measure against the port's baselines, so **no acquisition/measurement spec is written
here, and no run should be queued from this card** — consistent with the card's scope note.

### Appendix — the measurement side, should the acquisition question resurface as 310.9.16.0

Not required by this card. Recorded only so the reusable half — measuring *any* replacement DLL
against the port's quoted numbers — is written down once. The comparison target is fixed by the
claim sheet `docs/dlss-nr-performance-claim-sheet.md`:

- Metric: worker per-frame `network+composite` ms (`experiments/opendlss_port/linux-port.patch:1498-1501`),
  NOT total frame time and NOT network-only.
- Frames 29 and 59 of a 60-frame run; `--shm --no-motion --send-ahead 2`.
- Work resolution 2560x1440; fixture `fixtures/youtube-1440p.png`
  (sha256 `433847df0701176e548a24fbdd6c7a86b43a8bf473593effa2850f68af94c10f`).
- Box: RTX 4080 SUPER 615.71.09, Arch/KDE, Wayland.
- Acceptance thresholds to beat: **12.2/12.0 ms** (`r2026-10-12-b`) and **12.7/12.2 ms**
  (`r2026-10-12-d`); reference **13.1/13.1 ms** (`r2026-10-11-c`).
- Protocol: drop the candidate `nvngx_dlssnr.dll` into `native/`, record its sha256 and PE version
  resource, extract its PTX kernels as the port does for the bundled one, re-run the identical
  command from `runs/done/r2026-10-12-b/command.txt`, and compare the two worker frames. A number
  without the candidate DLL's sha256 and version resource attached is not comparable.

This appendix is a protocol sketch, not an acquisition plan: nothing here names a download source
for 310.9.16.0, and acquiring a leaked runtime is out of scope for this card.
