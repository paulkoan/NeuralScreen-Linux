#!/usr/bin/env python3
"""Is the GPU box quiet? A timing run is only worth reading if it is.

The 1440p numbers have moved by 6 ms between runs of the same config (29.1 ms and 35.3 ms an
hour apart), and nothing in a run's own output says whether something else was using the card.
This prints the card's state, the clocks it is actually running at, and any process holding it.

    tools/gpu_status.py                 # one reading, human readable
    tools/gpu_status.py --json          # the same, machine readable
    tools/gpu_status.py --watch 20      # sample for 20s, report the worst, for bracketing a run
    tools/gpu_status.py --busy-util 25  # the bar, in per cent; the runner takes it from the policy
    tools/gpu_status.py --require-idle  # exit 1 when busy, so a harness can refuse the run

It reads nvidia-smi (the usual case here), falls back to rocm-smi, and says UNKNOWN rather than
guessing when neither is present. It never writes anything and never touches the card.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time

# Above this, someone else is working on the card. Idle desktops sit at 0-5%: the compositor
# blips, and a Wayland session blips more. It was 15% until a live source was wanted: a browser
# playing video - the closest thing to a GeForce Now stream this box can be pointed at - costs
# real decode time on the card and is the thing under test rather than a contender with it, so a
# bar at 15% would have refused the runs that matter most. 25% is the level the human judged
# noise; a sample taken between 15 and 25 is contended, so its number is comparable with other
# samples taken under the same browser and not with the quiet baseline.
BUSY_UTIL = 25.0
# VRAM held by anything other than the desktop counts even at 0% utilisation - it is a claim
# on the card that a benchmark will contend with.
DESKTOP_PROCESSES = ("Xorg", "Xwayland", "kwin", "kwin_wayland", "plasmashell", "gnome-shell",
                     "systemd-logind", "sddm", "gdm")


def short_name(cmdline: str) -> str:
    """A game's process name is its whole command line, and Wine's is a Windows path.

    nvidia-smi reports the full argv, which buries the answer: two kilobytes of Chromium switches,
    or a Steam path through a directory with spaces in it. Take the executable if the line names
    one, otherwise the first token, basename only.
    """
    cmdline = (cmdline or "").strip()
    if not cmdline:
        return "(unreadable command line)"
    exe = re.search(r"([^\\/]+\.exe)", cmdline, re.IGNORECASE)
    if exe:
        return exe.group(1)[:60]
    first = cmdline.split()[0]
    return first.split("\\")[-1].split("/")[-1][:60]


def run(cmd: list[str], timeout: int = 15) -> str:
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout


def nvidia_smi() -> dict | None:
    if shutil.which("nvidia-smi") is None:
        return None
    fields = "name,uuid,utilization.gpu,memory.used,memory.total,clocks.sm,clocks.max.sm," \
             "temperature.gpu,power.draw,power.limit,pstate"
    out = run(["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"])
    if not out.strip():
        return None
    values = [v.strip() for v in out.strip().splitlines()[0].split(",")]

    def num(text):
        try:
            return float(text)
        except ValueError:
            return None

    names = [f.strip() for f in fields.split(",")]
    row = dict(zip(names, values))
    gpu = {
        "vendor": "nvidia",
        "name": row["name"],
        "uuid": row["uuid"],
        "util_percent": num(row["utilization.gpu"]),
        "mem_used_mib": num(row["memory.used"]),
        "mem_total_mib": num(row["memory.total"]),
        "clock_sm_mhz": num(row["clocks.sm"]),
        "clock_max_sm_mhz": num(row["clocks.max.sm"]),
        "temp_c": num(row["temperature.gpu"]),
        "power_w": num(row["power.draw"]),
        "power_limit_w": num(row["power.limit"]),
        "pstate": row["pstate"],
    }
    procs = run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
                 "--format=csv,noheader,nounits"])
    apps = []
    for line in procs.strip().splitlines():
        # The command line can contain commas, so split only as far as the memory figure.
        pid, _, rest = line.partition(",")
        cmdline, _, mem = rest.rpartition(",")
        if pid.strip():
            apps.append({"pid": pid.strip(), "name": short_name(cmdline.strip()),
                         "cmdline": cmdline.strip(), "mem_mib": num(mem)})
    gpu["compute_apps"] = apps
    return gpu


def rocm_smi() -> dict | None:
    if shutil.which("rocm-smi") is None:
        return None
    out = run(["rocm-smi", "--showuse", "--showtemp", "--showpower", "--json"])
    try:
        data = json.loads(out)
    except ValueError:
        return None
    card = next(iter(data.values()), {})
    return {"vendor": "amd", "name": card.get("Card series", "?"),
            "util_percent": _num(card.get("GPU use (%)")), "compute_apps": [],
            "mem_used_mib": None, "mem_total_mib": None, "clock_sm_mhz": None,
            "clock_max_sm_mhz": None, "temp_c": _num(card.get("Temperature (Sensor edge) (C)")),
            "power_w": _num(card.get("Average Graphics Package Power (W)")),
            "power_limit_w": None, "pstate": None, "uuid": None}


def _num(text):
    try:
        return float(str(text).strip())
    except (TypeError, ValueError):
        return None


def verdict(gpu: dict | None, busy_util: float = BUSY_UTIL) -> tuple[str, list[str]]:
    """IDLE, WARN or BUSY, with the reasons that led there.

    BUSY means something is taking compute time now, and a timing run beside it is worthless.
    WARN means another process is *resident* - holding VRAM without contending - which does not
    slow a frame by itself, but can wake up mid-run. A card sitting at a low SM clock is neither:
    clocks drop when nothing runs, so that is reported as a note, not a verdict.

    `busy_util` is the bar, in per cent. WARN carries the utilisation too, because "passes the
    gate" and "passes it by 20 points" are different kinds of number and only one of them is
    comparable with a run taken on a quiet card.
    """
    if gpu is None:
        return "UNKNOWN", ["no nvidia-smi or rocm-smi on this machine"]
    busy, resident = [], []
    util = gpu.get("util_percent")
    if util is not None and util >= busy_util:
        busy.append(f"utilization {util:.0f}%")
    for app in gpu.get("compute_apps") or []:
        name = app.get("name") or ""
        if any(d in name for d in DESKTOP_PROCESSES):
            continue
        label = f"{name} (pid {app.get('pid')}, {app.get('mem_mib')} MiB)"
        (busy if util is not None and util >= busy_util else resident).append(label)
    if busy:
        return "BUSY", busy + ([f"also resident: {r}" for r in resident])
    if resident:
        return "WARN", [f"resident but not contending: {r}" for r in resident]
    return "IDLE", []


def sample(seconds: int) -> dict:
    """Worst reading over `seconds` - a run is only as clean as its busiest moment."""
    worst = None
    deadline = time.time() + seconds
    while True:
        gpu = nvidia_smi() or rocm_smi()
        if gpu is not None and (worst is None or (gpu.get("util_percent") or 0)
                                > (worst.get("util_percent") or 0)):
            worst = gpu
        if time.time() >= deadline:
            return worst or {"vendor": "?", "name": "?", "util_percent": None,
                             "compute_apps": []}
        time.sleep(1.0)


def main() -> int:
    args = sys.argv[1:]
    seconds = 0
    if "--watch" in args:
        seconds = int(args[args.index("--watch") + 1])
    # The bar is a property of the machine and of what is meant to be running on it, so it is
    # settable rather than compiled in: the runner passes the policy's value, and a person can
    # ask the question "would this have passed at 15%" without editing the file.
    busy_util = BUSY_UTIL
    if "--busy-util" in args:
        busy_util = float(args[args.index("--busy-util") + 1])
    gpu = sample(seconds) if seconds > 0 else (nvidia_smi() or rocm_smi())
    state, why = verdict(gpu, busy_util)

    if "--json" in args:
        print(json.dumps({"verdict": state, "reasons": why, "samples_seconds": seconds,
                          "busy_util": busy_util, "gpu": gpu}, indent=2))
    elif gpu is None:
        print("GPU status: UNKNOWN - no nvidia-smi or rocm-smi on this machine")
    else:
        print(f"GPU status: {state}"
              + (f" - {'; '.join(why)}" if why else " - nothing else is using the card"))
        print(f"  {gpu['name']}  util {gpu.get('util_percent')}%  "
              f"mem {gpu.get('mem_used_mib')}/{gpu.get('mem_total_mib')} MiB  "
              f"sm {gpu.get('clock_sm_mhz')}/{gpu.get('clock_max_sm_mhz')} MHz  "
              f"{gpu.get('temp_c')}C  {gpu.get('power_w')}W  {gpu.get('pstate')}")
        for app in gpu.get("compute_apps") or []:
            print(f"  holds the card: {app['name']} pid {app['pid']} {app['mem_mib']} MiB")
        if seconds:
            print(f"  worst of {seconds} samples")
    if "--require-idle" in args and state != "IDLE":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
