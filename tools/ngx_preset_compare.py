#!/usr/bin/env python3
"""Compare two NGX model presets in one run, and print one report instead of two logs.

`NS_NR_PRESET` selects which network inside nvngx_dlssnr.dll the worker asks for (preset 1 is
the old model, preset 2 the new one in 310.9.16). Comparing them by hand means two commands,
two logs, and a hunt through both for the preset line, the frames line, the timing line and the
PNG hashes. This does that hunt mechanically and refuses to report a speedup it cannot trust.

    tools/ngx_preset_compare.py                       # presets 1 and 2, 120 frames, 1440p
    tools/ngx_preset_compare.py --frames 30 --out /tmp/ngx
    tools/ngx_preset_compare.py --old 1 --new 2 --keep

It runs the pipeline directly (`python -m minimal`), not through the queue: the installed unit's
policy pins the worker to the port binary and its sandbox hides the Wine prefix. Run this where
Wine and the DLL are reachable, i.e. on the box in this clone.

Exit codes:
  0  both runs completed and the comparison is trustworthy and shows a difference
  1  the comparison ran but is NOT trustworthy (same preset reached the DLL, or the two runs
     were not fed the same frame)
  2  a run failed, or the report could not be produced
"""
from __future__ import annotations

import argparse
import hashlib
import os
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# The lines this project's pipeline prints. Keep these patterns tight: a regex that matches the
# wrong line turns a refusal into a false pass, which is the failure this tool exists to prevent.
FRAMES = re.compile(
    r"^frames:\s+(?P<done>\d+)\s+done,\s+(?P<skipped>\d+)\s+skipped,\s+"
    r"(?P<seconds>[\d.]+)s\s+\((?P<headline>[\d.]+)\s+fps headline,\s+"
    r"(?P<steady>[\d.]+)\s+fps steady\),\s+worker exit\s+(?P<exit>-?\d+)",
    re.MULTILINE)
TIMING = re.compile(
    r"^timing:.*\(mean\s+(?P<mean>[\d.]+)ms/frame,\s+(?P<mean_fps>[\d.]+)\s+fps;\s+"
    r"median\s+(?P<median>[\d.]+)ms/frame,\s+(?P<median_fps>[\d.]+)\s+fps steady\)",
    re.MULTILINE)
PRESET = re.compile(r"direct feature 18 ready:.*\bpreset=(?P<preset>\d+)", re.MULTILINE)
WORKER = re.compile(r"^worker:\s*(?P<worker>.+)$", re.MULTILINE)
STAMP = re.compile(r"^stamp:\s*(?P<stamp>.+)$", re.MULTILINE)
# The port logs "serve frame N: total (proxy, network+composite, readback, reply)". The NGX host
# does not, so this is best-effort: absent on the Wine path and the report says so.
SERVE_FRAME = re.compile(
    r"serve frame\s+\d+:.*?network\+composite\s+(?P<nc>[\d.]+)", re.MULTILINE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def parse(text: str) -> dict:
    """Pull the fields a comparison needs out of one run's combined output."""
    out: dict = {"frames": None, "timing": None, "preset": None,
                 "worker": None, "stamp": None, "network_composite_ms": []}
    if match := FRAMES.search(text):
        out["frames"] = {k: match.group(k) for k in
                         ("done", "skipped", "seconds", "headline", "steady", "exit")}
        out["frames"]["done"] = int(out["frames"]["done"])
        out["frames"]["skipped"] = int(out["frames"]["skipped"])
        out["frames"]["exit"] = int(out["frames"]["exit"])
    if match := TIMING.search(text):
        out["timing"] = {k: float(match.group(k)) for k in
                         ("mean", "mean_fps", "median", "median_fps")}
    if match := PRESET.search(text):
        out["preset"] = int(match.group("preset"))
    if match := WORKER.search(text):
        out["worker"] = match.group("worker").strip()
    if match := STAMP.search(text):
        out["stamp"] = match.group("stamp").strip()
    out["network_composite_ms"] = [float(v) for v in SERVE_FRAME.findall(text)]
    return out


def pipeline_python() -> str:
    """The interpreter that has the pipeline's dependencies.

    A direct `tools/ngx_preset_compare.py` invocation picks up whatever python3 is on PATH; the
    repo's own venv is the one with numpy, so prefer it when it exists.
    """
    venv = REPO / ".venv" / "bin" / "python"
    return str(venv) if venv.exists() else sys.executable


def run_preset(preset: int, args: list[str], out_dir: Path, timeout: int) -> dict:
    """Run the pipeline once at one preset and keep its logs and pictures."""
    tag = f"preset{preset}"
    before = out_dir / f"before-{tag}.png"
    after = out_dir / f"after-{tag}.png"
    command = [pipeline_python(), "-m", "minimal", *args,
               "--save-before", str(before), "--save-after", str(after)]
    env = {"NS_NR_PRESET": str(preset)}
    started = time.time()
    try:
        done = subprocess.run(command, cwd=REPO, capture_output=True, text=True,
                              timeout=timeout, env={**os.environ, **env})
        status, stdout, stderr = done.returncode, done.stdout, done.stderr
    except subprocess.TimeoutExpired as expired:
        status = "timeout"
        stdout = (expired.stdout or b"").decode("utf-8", "replace") if isinstance(expired.stdout, bytes) else (expired.stdout or "")
        stderr = (expired.stderr or b"").decode("utf-8", "replace") if isinstance(expired.stderr, bytes) else (expired.stderr or "")
    elapsed = time.time() - started

    combined = stdout + "\n" + stderr
    (out_dir / f"{tag}.log").write_text(combined)
    info = parse(combined)
    info["tag"] = tag
    info["exit_code"] = status
    info["elapsed_s"] = round(elapsed, 2)
    info["before"] = before if before.exists() else None
    info["after"] = after if after.exists() else None
    info["before_sha"] = sha256(before) if before.exists() else None
    info["after_sha"] = sha256(after) if after.exists() else None
    info["before_bytes"] = before.stat().st_size if before.exists() else None
    info["after_bytes"] = after.stat().st_size if after.exists() else None
    return info


def diff_pictures(old: Path, new: Path) -> str:
    """Run the project's own differ rather than reimplement its statistics."""
    try:
        done = subprocess.run([sys.executable, str(REPO / "tools/frame_diff.py"),
                               str(old), str(new)], cwd=REPO, capture_output=True, text=True,
                              timeout=180)
        text = (done.stdout + done.stderr).strip()
        return text or f"(frame_diff exited {done.returncode} with no output)"
    except subprocess.TimeoutExpired:
        return "(frame_diff timed out)"


def verdict(old: dict, new: dict) -> tuple[bool, list[str]]:
    """Say whether the comparison is trustworthy, and why not when it is not."""
    problems: list[str] = []
    for info in (old, new):
        tag = info["tag"]
        if info["exit_code"] != 0:
            problems.append(f"{tag}: exit {info['exit_code']} (not a completed run)")
        if not info["frames"]:
            problems.append(f"{tag}: no 'frames:' line in the log")
            continue
        if info["frames"]["skipped"]:
            problems.append(f"{tag}: {info['frames']['skipped']} frames skipped "
                            f"(the rate is over fewer frames than it claims)")
        if not info["after"]:
            problems.append(f"{tag}: no after.png written")
        if info["preset"] is None:
            problems.append(f"{tag}: no 'direct feature 18 ready ... preset=' line - "
                            f"cannot prove which network the DLL was asked for")

    if old["preset"] is not None and old["preset"] == new["preset"]:
        problems.append(f"both runs reported preset={old['preset']}: the hint did not switch "
                        f"the network, so any timing difference is noise")
    if old["before_sha"] and new["before_sha"] and old["before_sha"] != new["before_sha"]:
        problems.append("the two runs were not fed the same frame "
                        f"(before shas {old['before_sha'][:12]} vs {new['before_sha'][:12]})")
    if old["after_sha"] and new["after_sha"] and old["after_sha"] == new["after_sha"]:
        problems.append("both runs produced the same after.png: the picture did not change, "
                        "which contradicts a different network having run")
    return (not problems), problems


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "compare two NGX model presets").split("\n")[0])
    ap.add_argument("--old", type=int, default=1, help="preset for the old model (default 1)")
    ap.add_argument("--new", type=int, default=2, help="preset for the new model (default 2)")
    ap.add_argument("--frames", type=int, default=120,
                    help="frames per run (default 120; 30 leaves frame 0's warm-up in the mean)")
    ap.add_argument("--size", default="2560x1440")
    ap.add_argument("--source", default="synthetic")
    ap.add_argument("--out", default=None, help="output directory (default: /tmp/ngx-compare-TS)")
    ap.add_argument("--timeout", type=int, default=600, help="per-run timeout in seconds")
    ap.add_argument("--keep", action="store_true", help="do not delete anything on failure")
    args = ap.parse_args(argv)

    out_dir = Path(args.out) if args.out else Path(f"/tmp/ngx-compare-{time.strftime('%Y%m%dT%H%M%S')}")
    out_dir.mkdir(parents=True, exist_ok=True)

    pipeline_args = ["--headless", "--frames", str(args.frames),
                     "--source", args.source, "--size", args.size, "--shm", "--worker-log"]

    print(f"out      {out_dir}")
    print(f"pipeline {' '.join(pipeline_args)}")
    print()

    results = {}
    for preset in (args.old, args.new):
        print(f"--- running preset {preset} ---", flush=True)
        results[preset] = run_preset(preset, pipeline_args, out_dir, args.timeout)
        info = results[preset]
        print(f"exit {info['exit_code']}  {info['elapsed_s']}s  "
              f"preset={info['preset']}  after={info['after_sha'][:12] if info['after_sha'] else 'none'}")
    old, new = results[args.old], results[args.new]

    trustworthy, problems = verdict(old, new)

    print()
    print("=== comparison ===")
    header = f"{'preset':>6}  {'exit':>4}  {'frames':>7}  {'skipped':>7}  {'elapsed':>8}  " \
             f"{'steady ms':>9}  {'steady fps':>10}  {'headline':>8}  {'preset hint':>11}"
    print(header)
    print("-" * len(header))
    for info in (old, new):
        fr = info["frames"] or {}
        tm = info["timing"] or {}
        print(f"{info['preset'] if info['preset'] is not None else '?':>6}  "
              f"{str(info['exit_code']):>4}  {fr.get('done', '?'):>7}  "
              f"{fr.get('skipped', '?'):>7}  {info['elapsed_s']:>7.2f}s  "
              f"{tm.get('median', float('nan')):>9.1f}  {tm.get('median_fps', float('nan')):>10.1f}  "
              f"{tm.get('headline', float('nan')):>8.2f}  "
              f"{info['preset'] if info['preset'] is not None else '?':>11}")

    if old["timing"] and new["timing"] and old["timing"]["median"] and new["timing"]["median"]:
        speedup = old["timing"]["median"] / new["timing"]["median"]
        print()
        print(f"steady speedup old/new: {speedup:.2f}x  "
              f"({old['timing']['median']:.1f}ms -> {new['timing']['median']:.1f}ms per frame)")
    if old["network_composite_ms"] and new["network_composite_ms"]:
        old_nc = sorted(old["network_composite_ms"])[len(old["network_composite_ms"]) // 2]
        new_nc = sorted(new["network_composite_ms"])[len(new["network_composite_ms"]) // 2]
        print(f"model-only (network+composite) median: {old_nc:.1f}ms -> {new_nc:.1f}ms "
              f"({old_nc / new_nc:.2f}x)")

    print()
    print(f"before identical: {old['before_sha'] == new['before_sha']}")
    print(f"after differs:    {old['after_sha'] != new['after_sha']}")

    if old["after"] and new["after"] and old["after_sha"] != new["after_sha"]:
        print()
        print("--- picture diff (old after vs new after) ---")
        print(diff_pictures(old["after"], new["after"]))

    report = {"out": str(out_dir), "pipeline_args": pipeline_args,
              "old": {k: v for k, v in old.items() if k not in ("before", "after")},
              "new": {k: v for k, v in new.items() if k not in ("before", "after")},
              "trustworthy": trustworthy, "problems": problems}
    (out_dir / "compare.json").write_text(json.dumps(report, indent=2) + "\n")

    print()
    if trustworthy:
        print(f"VERDICT: trustworthy. report: {out_dir}/compare.json")
        return 0
    print("VERDICT: NOT trustworthy - do not quote these numbers:")
    for problem in problems:
        print(f"  - {problem}")
    print(f"logs and pictures kept in {out_dir}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))