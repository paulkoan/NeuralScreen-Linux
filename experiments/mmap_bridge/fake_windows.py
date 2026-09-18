#!/usr/bin/env python3
"""The Windows side of the bridge handshake, in Python.

It exists so the protocol can be exercised without Wine. bridge_check.py's
`--windows-cmd` can point at this instead of at wine+bridge_win.exe, which
means the same file, the same layout and the same state machine run natively and
a test can assert them. Then a failure under Wine is about Wine — about whether
the mapped pages really are shared — and not about my handshake.

It is deliberately the same state machine as bridge_win.c: report ready, wait
for the native side's pattern, verify every byte, answer with our own pattern.
"""

from __future__ import annotations

import mmap
import os
import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from bridge_check import (  # noqa: E402
    DONE, LEN_OFF, MAGIC, MAGIC_OFF, NATIVE_BYTE, NATIVE_WROTE, PAYLOAD_OFF,
    ROUND_OFF, STATE_OFF, WIN_BYTE, WIN_READY, WIN_WROTE,
)


def rd32(buf, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def wr32(buf, off: int, value: int) -> None:
    struct.pack_into("<I", buf, off, value & 0xFFFFFFFF)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: fake_windows.py <native-path> [flush]", file=sys.stderr)
        return 2
    do_flush = len(argv) > 1 and argv[1] == "flush"
    path = Path(argv[0])
    if not path.is_file():
        print(f"fake_windows: no such file: {path}", file=sys.stderr)
        return 1

    size = path.stat().st_size
    fd = os.open(path, os.O_RDWR)
    mm = mmap.mmap(fd, size, prot=mmap.PROT_READ | mmap.PROT_WRITE,
                   flags=mmap.MAP_SHARED)
    try:
        if mm[MAGIC_OFF:MAGIC_OFF + 4] != MAGIC.encode():
            print("fake_windows: bad magic — the native side had not written the "
                  "file when we mapped it", file=sys.stderr)
            return 1
        length = rd32(mm, LEN_OFF)
        if length == 0 or length > size - PAYLOAD_OFF:
            print(f"fake_windows: implausible payload_len {length}", file=sys.stderr)
            return 1

        print(f"fake_windows: mapping is live, payload_len {length}", flush=True)
        wr32(mm, STATE_OFF, WIN_READY)
        if do_flush:
            mm.flush()

        rounds = 0
        mismatches = 0
        deadline = time.monotonic() + 60.0
        while time.monotonic() < deadline:
            state = rd32(mm, STATE_OFF)
            if state == DONE:
                break
            if state != NATIVE_WROTE:
                time.sleep(0.0005)
                continue

            round_no = rd32(mm, ROUND_OFF)
            payload = mm[PAYLOAD_OFF:PAYLOAD_OFF + length]
            bad = length - payload.count(NATIVE_BYTE)
            if bad:
                mismatches += 1
                print(f"fake_windows: round {round_no}: {bad} of {length} bytes "
                      f"were not 0x{NATIVE_BYTE:02X}", file=sys.stderr)

            t0 = time.monotonic()
            mm[PAYLOAD_OFF:PAYLOAD_OFF + length] = bytes([WIN_BYTE]) * length
            if do_flush:
                mm.flush()
            took = time.monotonic() - t0
            rounds += 1
            print(f"fake_windows: round {round_no}: read {length} bytes, wrote "
                  f"{length}, {1000 * took:.2f} ms", flush=True)
            wr32(mm, STATE_OFF, WIN_WROTE)
            if do_flush:
                mm.flush()
        else:
            print("fake_windows: timed out waiting for the native side",
                  file=sys.stderr)
            return 1

        print(f"fake_windows: {rounds} rounds, {mismatches} with mismatches")
        return 1 if mismatches else 0
    finally:
        mm.close()
        os.close(fd)


if __name__ == "__main__":
    sys.exit(main())