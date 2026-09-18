#!/usr/bin/env python3
"""The native half of the shared-file bridge test.

Answers one question: can a native Linux process and a Wine process see each
other's writes to the same memory-mapped file? If not, the own-host pathway is
dead, because the worker's input paths are a pipe and a Windows *named section*,
and named sections are not reachable from native Linux. A file might be.

The constants come from bridge_layout.h by parsing it, so the C side and this
side cannot drift apart — the lesson from the worker's launch environment, which
was written down twice and had to be brought back under a test.

Usage:
    bridge_check.py [--bytes N] [--rounds N] [--keep]

Exit codes: 0 the pages were shared in both directions, 1 they were not (or a
timeout), 2 bad usage or missing prerequisites.
"""

from __future__ import annotations

import argparse
import mmap
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def parse_layout(path: Path) -> dict[str, object]:
    """Read NSB_* constants out of the C header.

    Deliberately a parser rather than a copy: two copies of a layout is how the
    worker's environment drifted, and a test enforces that this parse works and
    yields sane values.
    """
    out: dict[str, object] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line.startswith("#define"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        name = parts[1]
        value = parts[2].split("/*")[0].strip()
        if not name.startswith("NSB_"):
            continue
        if value.startswith('"'):
            out[name] = value.strip('"')
        else:
            # Strip the C integer suffixes (16u, 0x57u, 1L) then evaluate the
            # arithmetic with no builtins available.
            cleaned = re.sub(r"[uUlL]+\b", "", value).strip()
            out[name] = int(eval(cleaned, {"__builtins__": {}}, {}))  # noqa: S307
    return out


LAYOUT = parse_layout(HERE / "bridge_layout.h")


def _c(name: str) -> int:
    """An integer constant from the parsed header.

    Checked at import, so a header this parser cannot read fails here with the
    name in the message rather than as a type error deep inside the handshake.
    """
    value = LAYOUT[name]
    if not isinstance(value, int):
        raise TypeError(f"{name} in bridge_layout.h is not an integer: {value!r}")
    return value


MAGIC = str(LAYOUT["NSB_MAGIC"])
HDR = _c("NSB_HDR_BYTES")
MAGIC_OFF = _c("NSB_MAGIC_OFF")
STATE_OFF = _c("NSB_STATE_OFF")
ROUND_OFF = _c("NSB_ROUND_OFF")
LEN_OFF = _c("NSB_LEN_OFF")
PAYLOAD_OFF = _c("NSB_PAYLOAD_OFF")
CAPACITY = _c("NSB_CAPACITY")
FRESH = _c("NSB_FRESH")
NATIVE_WROTE = _c("NSB_NATIVE_WROTE")
WIN_WROTE = _c("NSB_WIN_WROTE")
DONE = _c("NSB_DONE")
WIN_READY = _c("NSB_WIN_READY")
NATIVE_BYTE = _c("NSB_NATIVE_BYTE")
WIN_BYTE = _c("NSB_WIN_BYTE")

FRAME_1440P = 2560 * 1440 * 4


def z_path(linux_path: Path) -> str:
    """The Windows path for a Linux one. Wine maps / as Z:\\ by default."""
    return "Z:" + str(linux_path).replace("/", "\\")


def rd32(buf, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def wr32(buf, off: int, value: int) -> None:
    struct.pack_into("<I", buf, off, value & 0xFFFFFFFF)


def wait_state(buf, want, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while rd32(buf, STATE_OFF) != want:
        if time.monotonic() > deadline:
            return False
        time.sleep(0.0005)
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bridge_check",
                                 description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--bytes", type=int, default=FRAME_1440P,
                    help=f"payload bytes (default {FRAME_1440P} = one "
                         f"2560x1440 RGBA frame)")
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--dir", default="/tmp/nsb_bridge")
    ap.add_argument("--keep", action="store_true",
                    help="keep the file afterwards (it is 16MB)")
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--flush", action="store_true",
                    help="msync after every write. Off by default because "
                         "coherence does not need it — two MAP_SHARED mappings "
                         "of one file are the same physical pages — and it "
                         "forces writeback, which dominated the first version's "
                         "numbers (14ms for a 3MB copy that should take 0.3ms)")
    ap.add_argument("--windows-cmd", default=None,
                    help="command for the Windows side, with {exe}, {path} and "
                         "{zpath} placeholders. Defaults to 'wine <exe> <zpath>'. "
                         "Pointing it at fake_windows.py runs the same handshake "
                         "natively, so a test can cover the protocol without "
                         "Wine — and a failure under Wine is then about Wine")
    args = ap.parse_args(argv)

    if args.bytes < 4096 or args.bytes > CAPACITY:
        print(f"bad --bytes: {args.bytes} is outside 4096..{CAPACITY}", file=sys.stderr)
        return 2

    workdir = Path(args.dir)
    workdir.mkdir(parents=True, exist_ok=True)
    path = workdir / "frame.bin"
    size = HDR + args.bytes
    zpath = z_path(path)

    exe = HERE / "bridge_win.exe"
    if args.windows_cmd:
        # The handshake must be testable without Wine. Pointing this at
        # fake_windows.py runs the same file, the same layout and the same state
        # machine natively — which leaves Wine responsible for exactly one
        # thing, page sharing, instead of for the protocol as well.
        cmd = [part.format(exe=str(exe), path=str(path), zpath=zpath)
               for part in shlex.split(args.windows_cmd)]
    else:
        if not exe.is_file():
            print(f"the Windows half is not built: {exe}\n"
                  f"  build it with: x86_64-w64-mingw32-gcc -O2 -o {exe} "
                  f"{HERE / 'bridge_win.c'}", file=sys.stderr)
            return 2
        wine = shutil.which("wine") or shutil.which("wine64")
        if wine is None:
            print("wine is not on PATH (or pass --windows-cmd)", file=sys.stderr)
            return 2
        cmd = [wine, str(exe), zpath]

    # Both sides take the same flag, so the two are compared under the same
    # conditions rather than one of them silently paying a writeback per round.
    if args.flush:
        cmd.append("flush")
    real_wine = args.windows_cmd is None

    print("=" * 66)
    print(" shared-file bridge: can Wine and native Linux share mapped pages?")
    print("=" * 66)
    print(f"  file:     {path}  ({size / 1e6:.1f} MB)")
    print(f"  payload:  {args.bytes / 1e6:.1f} MB per round ({args.rounds} rounds)")
    print(f"  windows:  {z_path(path)}")

    with open(path, "wb") as fh:
        fh.truncate(size)

    fd = os.open(path, os.O_RDWR)
    mm = mmap.mmap(fd, size, prot=mmap.PROT_READ | mmap.PROT_WRITE,
                   flags=mmap.MAP_SHARED)
    try:
        mm[MAGIC_OFF:MAGIC_OFF + 4] = MAGIC.encode()
        wr32(mm, LEN_OFF, args.bytes)
        wr32(mm, ROUND_OFF, 0)
        wr32(mm, STATE_OFF, FRESH)
        if args.flush:
            mm.flush()

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True)
        print(f"  windows:  {' '.join(cmd)}")
        print(f"  pid:      {proc.pid}")
        print()
        if not wait_state(mm, WIN_READY, args.timeout):
            print("  FAIL: the Windows side never reported its mapping ready. "
                  "Its output follows:", file=sys.stderr)
            proc.terminate()
            print(proc.communicate(timeout=10)[0], file=sys.stderr)
            return 1
        print("  the Windows side has the mapping. Exchanging frames.")
        print()

        ok = True
        round_times: list[float] = []
        fill_times: list[float] = []
        for i in range(args.rounds):
            t0 = time.monotonic()
            mm[PAYLOAD_OFF:PAYLOAD_OFF + args.bytes] = bytes([NATIVE_BYTE]) * args.bytes
            if args.flush:
                mm.flush()
            t1 = time.monotonic()

            wr32(mm, ROUND_OFF, i + 1)
            wr32(mm, STATE_OFF, NATIVE_WROTE)
            if args.flush:
                mm.flush()

            if not wait_state(mm, WIN_WROTE, args.timeout):
                print(f"  round {i + 1}: FAIL — the Windows side never answered "
                      f"(state {rd32(mm, STATE_OFF)})", file=sys.stderr)
                ok = False
                break
            t2 = time.monotonic()

            got = mm[PAYLOAD_OFF:PAYLOAD_OFF + args.bytes]
            wrong = got.count(WIN_BYTE)
            if wrong != args.bytes:
                bad = args.bytes - wrong
                print(f"  round {i + 1}: FAIL — {bad} of {args.bytes} bytes were "
                      f"not 0x{WIN_BYTE:02X}; the pages are not shared",
                      file=sys.stderr)
                ok = False
                break

            fill_times.append(t1 - t0)
            round_times.append(t2 - t0)
            # Rates labelled for what they are. The first version divided bytes
            # by 1e6 by seconds and called the result GB/s, which overstated it
            # by 1000x.
            one_way = args.bytes / (t1 - t0) / 1e6
            both = 2 * args.bytes / (t2 - t0) / 1e6
            print(f"  round {i + 1:2d}: write {1000 * (t1 - t0):6.2f}ms "
                  f"({one_way:7.0f} MB/s one way)   "
                  f"round trip {1000 * (t2 - t0):6.2f}ms ({both:7.0f} MB/s both "
                  f"ways)")

        wr32(mm, STATE_OFF, DONE)
        if args.flush:
            mm.flush()
        out = proc.communicate(timeout=30)[0]
        print()
        print("  the Windows side said:")
        for line in out.strip().splitlines():
            print(f"    {line}")

        print()
        print("=" * 66)
        if not ok:
            print(" RESULT: FAIL — the pages were NOT shared both ways.")
            print(" The own-host pathway depends on this and cannot proceed "
                  "without it.")
            return 1

        # The claim has to match what actually ran. The first version announced
        # "a native process and a Wine process share these pages" even when
        # --windows-cmd had replaced Wine with a Python stand-in, which is the
        # kind of unearned claim this whole area keeps having to walk back.
        if real_wine:
            print(" RESULT: PASS — a native process and a Wine process share "
                  "these pages in both directions.")
        else:
            print(" RESULT: PASS — the handshake works end to end. This run did "
                  "NOT involve Wine.")
            print(f"         the second process was: {' '.join(cmd)}")
            print("         so the layout and the protocol are proven; that Wine "
                  "shares the pages is NOT proven by this run.")

        mean_round = sum(round_times) / len(round_times)
        mean_fill = sum(fill_times) / len(fill_times)
        print()
        print(f"  {args.bytes / 1e6:.1f} MB written and returned in "
              f"{1000 * mean_round:.2f}ms mean over {args.rounds} rounds "
              f"({2 * args.bytes / mean_round / 1e6:.0f} MB/s both ways)")
        print(f"  of which {1000 * mean_fill:.2f}ms is our own write "
              f"({args.bytes / mean_fill / 1e6:.0f} MB/s one way)")
        if args.flush:
            print("  (with --flush, so every round pays a writeback. The real "
                  "implementation should not: coherence does not need it.)")
        else:
            print("  (no msync per round: two MAP_SHARED mappings of one file are "
                  "the same physical pages, so a per-frame flush would be paid "
                  "for nothing)")
        print()
        print("  for scale: a pipe read measured ~1100 MB/s on the analysis box,")
        print("  and the MVP's 2560x1440 floor with NGX skipped is ~85ms a frame.")
        return 0
    finally:
        mm.close()
        os.close(fd)
        if not args.keep:
            try:
                path.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(main())