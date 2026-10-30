#!/usr/bin/env python3
"""Run the NGX gate across presets and paths, and print one table instead of six logs.

The gate answers "does the worker run" for one configuration at a time. When a new DLL arrives
the question is a matrix: which presets and which create/evaluate path fail, and at which stage.
Doing that by hand means six command lines, six paste-ins, and reading the same eight log lines
six times - which is how a real difference gets lost in the repetition.

    tools/ngx_matrix.py                       # presets 0,1,2 x direct, via-core
    tools/ngx_matrix.py --presets 1,2         # only the two named models
    tools/ngx_matrix.py --out /tmp/ngx-matrix # keep every log there

The table's columns are the stages the gate distinguishes: NGX init, feature create, evaluate,
and the 300-evaluate loop. A row that fails at create and a row that fails at evaluate are
different bugs, and the table makes that visible without reading prose.

Exit codes:
  0  every combination passed
  1  the matrix ran and at least one combination failed
  2  the matrix could not run (prerequisites missing, gate not found)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / "tools" / "m0_env_gate.sh"
WORKER_LOG = REPO / "native" / "dlss5-feed-host.log"

INIT = re.compile(r"NVSDK_NGX_D3D12_Init\s*->\s*(?P<code>0x[0-9A-Fa-f]{8})\s*\((?P<name>[^)]*)\)")
CREATE_OK = re.compile(r"direct feature 18 ready:.*?preset=(?P<preset>\d+).*?result=(?P<code>0x[0-9A-Fa-f]{8})")
CREATE_FAIL = re.compile(r"feature 18 create failed\s*(?P<code>0x[0-9A-Fa-f]{8})?\s*\(?(?P<name>[^)]*)\)?")
EVAL_FAIL = re.compile(r"evaluate failed\s*(?P<code>0x[0-9A-Fa-f]{8})\s*\((?P<name>[^)]*)\)")
FINISHED = re.compile(r"--test finished:\s*(?P<good>\d+)/(?P<total>\d+)")
VIA_CORE = re.compile(r"NS_NGX_VIA_CORE=1")
ARCH = re.compile(r"\[arch\] patch installed:.*?architecture\s*(?P<arch>0x[0-9A-Fa-f]+)")


def parse(text: str) -> dict:
    """The stage results a gate run reports, or None for a stage it never reached."""
    out: dict = {"init": None, "create": None, "evaluate": None,
                 "finished": None, "via_core": bool(VIA_CORE.search(text)),
                 "arch": None, "error": None}
    if m := INIT.search(text):
        out["init"] = {"code": m.group("code"), "name": m.group("name").strip()}
    if m := CREATE_OK.search(text):
        out["create"] = {"ok": True, "preset": int(m.group("preset")),
                         "code": m.group("code")}
    elif m := CREATE_FAIL.search(text):
        out["create"] = {"ok": False, "code": (m.group("code") or "").strip(),
                         "name": (m.group("name") or "").strip()}
    if m := EVAL_FAIL.search(text):
        out["evaluate"] = {"ok": False, "code": m.group("code"),
                           "name": m.group("name").strip()}
    if m := FINISHED.search(text):
        out["finished"] = {"good": int(m.group("good")), "total": int(m.group("total"))}
    elif out["create"] and out["create"]["ok"] and not out["evaluate"]:
        # Create succeeded and no failure was logged: the loop should have run. Say so rather
        # than reporting a silent success.
        out["error"] = "created but the gate printed no evaluation summary"
    if m := ARCH.search(text):
        out["arch"] = m.group("arch")
    return out


def verdict(result: dict) -> str:
    """PASS, or the first stage that failed."""
    if result["init"] and not result["init"]["name"].lower().startswith("success"):
        return f"init {result['init']['code']}"
    if result["create"] and not result["create"]["ok"]:
        return f"create {result['create'].get('code') or '?'}"
    if result["evaluate"] and not result["evaluate"]["ok"]:
        return f"evaluate {result['evaluate']['code']}"
    if result["finished"]:
        good, total = result["finished"]["good"], result["finished"]["total"]
        return "PASS" if good >= 0.8 * total else f"loop {good}/{total}"
    return result["error"] or "no verdict"


def wine_path(path: Path) -> str:
    """An absolute Unix path as Wine's Z: drive, which is what LoadLibraryW expects."""
    return "Z:" + str(path).replace("/", "\\")


def find_old_dll() -> Path | None:
    """The 310.8.0 runtime, if the box kept one: the control for every new-DLL failure."""
    for candidate in (REPO / "native" / "nvngx_dlssnr-310.8.0.dll",
                      Path("/home/paul/dev/NeuralScreen-Linux/native/nvngx_dlssnr.dll")):
        if candidate.is_file():
            return candidate
    return None


def run_combo(preset: int, via_core: bool, out_dir: Path, timeout: int, *,
              spoof: int = 1, dll: Path | None = None, label: str = "bundled") -> dict:
    env = {**os.environ, "NS_NR_PRESET": str(preset), "NS_ARCH_SPOOF": str(spoof)}
    if dll is not None:
        env["NS_NR_DLL"] = wine_path(dll)
    command = ["bash", str(GATE)] + (["--via-core"] if via_core else [])
    started = time.time()
    try:
        done = subprocess.run(command, cwd=REPO, capture_output=True, text=True,
                              timeout=timeout, env=env)
        text = done.stdout + "\n" + done.stderr
        code = done.returncode
    except subprocess.TimeoutExpired as expired:
        def as_text(value) -> str:
            if isinstance(value, bytes):
                return value.decode("utf-8", "replace")
            return value or ""
        text = as_text(expired.stdout) + "\n" + as_text(expired.stderr)
        code = "timeout"
    elapsed = round(time.time() - started, 1)
    if WORKER_LOG.exists():
        text += "\n" + WORKER_LOG.read_text(errors="replace")
    tag = f"{label}-p{preset}-{'core' if via_core else 'direct'}-spoof{spoof}"
    (out_dir / f"{tag}.log").write_text(text)
    result = parse(text)
    result.update({"preset": preset, "via_core": via_core, "exit": code,
                   "seconds": elapsed, "tag": tag, "label": label, "spoof": spoof,
                   "dll": str(dll) if dll is not None else "bundled"})
    return result


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--presets", default="0,1,2", help="comma-separated presets (default 0,1,2)")
    ap.add_argument("--via-core", default="0,1", help="comma-separated 0/1 (default 0,1)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--spoof", type=int, default=1,
                    help="NS_ARCH_SPOOF value for the matrix (default 1)")
    ap.add_argument("--baseline", action="store_true",
                    help="run the control set instead: bundled vs old DLL, spoof on/off, "
                         "direct vs core, one preset - the question a new DLL forces")
    args = ap.parse_args(argv)

    if not GATE.is_file():
        print(f"gate not found: {GATE}", file=sys.stderr)
        return 2
    out_dir = Path(args.out) if args.out else Path(f"/tmp/ngx-matrix-{time.strftime('%Y%m%dT%H%M%S')}")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"matrix -> {out_dir}")

    if args.baseline:
        old = find_old_dll()
        combos = [
            {"label": "bundled", "dll": None, "spoof": 1, "preset": 0, "via_core": False},
            {"label": "bundled", "dll": None, "spoof": 0, "preset": 0, "via_core": False},
            {"label": "bundled", "dll": None, "spoof": 1, "preset": 0, "via_core": True},
        ]
        if old is not None:
            combos.append({"label": "old", "dll": old, "spoof": 1, "preset": 0,
                           "via_core": False})
            print(f"control DLL: {old}")
        else:
            print("note: no 310.8.0 DLL found (looked for native/nvngx_dlssnr-310.8.0.dll "
                  "and the dev tree); the control row is omitted")
    else:
        presets = [int(p) for p in args.presets.split(",") if p.strip() != ""]
        core_modes = [c.strip() in ("1", "true", "yes") for c in args.via_core.split(",")]
        combos = [{"label": "bundled", "dll": None, "spoof": args.spoof, "preset": preset,
                   "via_core": via_core}
                  for preset in presets for via_core in core_modes]

    rows = []
    for combo in combos:
        print(f"--- {combo['label']} preset {combo['preset']}, "
              f"{'via core' if combo['via_core'] else 'direct'}, spoof {combo['spoof']} ---",
              flush=True)
        row = run_combo(combo["preset"], combo["via_core"], out_dir, args.timeout,
                        spoof=combo["spoof"], dll=combo["dll"], label=combo["label"])
        rows.append(row)
        print(f"    {verdict(row)}  ({row['seconds']}s)")

    print()
    header = (f"{'dll':>9}  {'preset':>6}  {'path':>7}  {'spoof':>5}  {'init':>12}  "
              f"{'create':>14}  {'evaluate':>14}  {'loop':>7}  verdict")
    print(header)
    print("-" * len(header))
    for row in rows:
        init = row["init"]["name"][:12] if row["init"] else "-"
        create = "ok" if row["create"] and row["create"]["ok"] else (
            row["create"].get("code") or "?" if row["create"] else "-")
        evaluate = row["evaluate"]["code"] if row["evaluate"] else "-"
        loop = f"{row['finished']['good']}/{row['finished']['total']}" if row["finished"] else "-"
        print(f"{row['label']:>9}  {row['preset']:>6}  "
              f"{'core' if row['via_core'] else 'direct':>7}  {row['spoof']:>5}  "
              f"{init:>12}  {create:>14}  {evaluate:>14}  {loop:>7}  {verdict(row)}")

    summary = {"out": str(out_dir), "rows": rows,
               "passed": [r["tag"] for r in rows if verdict(r) == "PASS"]}
    (out_dir / "matrix.json").write_text(json.dumps(summary, indent=2) + "\n")

    failed = [r for r in rows if verdict(r) != "PASS"]
    print()
    if not failed:
        print(f"all {len(rows)} combinations passed. matrix: {out_dir}/matrix.json")
        return 0

    groups: dict[str, list[str]] = {}
    for row in failed:
        groups.setdefault(verdict(row), []).append(row["tag"])
    print(f"{len(failed)} of {len(rows)} failed:")
    for signature, tags in sorted(groups.items()):
        print(f"  {signature}: {', '.join(tags)}")

    if args.baseline:
        old_rows = [r for r in rows if r["label"] == "old"]
        new_rows = [r for r in rows if r["label"] == "bundled"]
        old_pass = any(verdict(r) == "PASS" for r in old_rows)
        new_pass = any(verdict(r) == "PASS" for r in new_rows)
        if old_rows and old_pass and not new_pass:
            print("  -> the old DLL passes in the same harness: the create/evaluate contract")
            print("     changed in 310.9.16, and the host is what needs the fix.")
        elif old_rows and not old_pass and not new_pass:
            print("  -> the old DLL fails too: the harness, prefix or driver changed - not the DLL.")
        no_spoof = [r for r in new_rows if r["spoof"] == 0]
        with_spoof = [r for r in new_rows if r["spoof"] == 1 and not r["via_core"]]
        if no_spoof and with_spoof:
            if any(verdict(r) == "PASS" for r in no_spoof) != any(verdict(r) == "PASS" for r in with_spoof):
                print("  -> the architecture spoof changes the outcome: it is part of the failure.")
            else:
                print("  -> the architecture spoof does not change the outcome: it is not the cause.")
    elif all(verdict(r).startswith("evaluate 0xBAD00004") for r in failed):
        print("  -> create succeeds but the handle is not known to Evaluate. That is a host-side")
        print("     mismatch (create/evaluate registries), not a preset or model problem.")
    elif all(verdict(r).startswith("create 0xBAD0000B") for r in failed):
        print("  -> create itself refuses: the runtime cannot initialise the feature at all.")
    print(f"logs: {out_dir}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
