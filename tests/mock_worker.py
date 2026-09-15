"""A stand-in for the Wine worker that speaks the real binary protocol.

This exists so the entire Python pipeline can be exercised with no GPU and no
Wine. It reads the same 64-byte stream header, then the same 24-byte FRAME_MAGIC
headers with colour and motion inline, and replies with the same 28-byte
OUT_MAGIC result header and pixels — all structures copied from
native/dlss5-feed-host64.cpp (see struct VideoHeader / VideoFrameHeader /
VideoResultHeader and ReadVideoMessage / RunVideo).

It applies a deterministic, easily-asserted transform instead of a neural
network: reverse the colour channels (a no-op for a greyscale test pattern, a
visible change for colour) and add a constant offset. That makes "the pixels
came back through the worker" a property the tests can actually check.

Usage:  python tests/mock_worker.py            # reads the header, serves frames
        python tests/mock_worker.py --fail     # exits non-zero after 1 frame
"""

from __future__ import annotations

import argparse
import struct
import sys

# --- protocol constants, mirrored from native/dlss5-feed-host64.cpp ---------
VIDEO_MAGIC_EXT = 0x33563544   # 'DV5' v3 — 64-byte header with full_w/full_h
VIDEO_MAGIC_LEGACY = 0x32563544  # 'D5V2' — 56-byte header (no full_w/full_h)
FRAME_MAGIC = 0x314D5246       # 'FMR1'
OUT_MAGIC = 0x3154554F         # 'OUT1'
SHM_MAGIC = 0x494D4853         # 'SHMI'
SHM_ACK_MAGIC = 0x4B434153     # 'SACK'

VIDEO_HEADER_LEGACY_SIZE = 56
HEADER_FMT = "<10I4f2I"        # 64 bytes
FRAME_FMT = "<4Iq"             # 24 bytes
OUT_FMT = "<5Iq"               # 28 bytes
SHM_FMT = "<4Iq64s"            # 88 bytes
SHM_ACK_FMT = "<4Iq"           # 24 bytes

FRAME_FLAG_SHM = 0x1
FRAME_FLAG_MOTION_SMALL = 0x4

# The transform the mock applies, so tests can assert the round-trip happened.
CHANNEL_REVERSED = True
BRIGHTNESS_OFFSET = 8


def _read_exact(stream, size: int) -> bytes:
    """Read exactly size bytes, or raise EOFError (mirrors _read_exact in C++)."""
    buf = bytearray()
    while len(buf) < size:
        chunk = stream.read(size - len(buf))
        if not chunk:
            raise EOFError(f"stream closed after {len(buf)}/{size} bytes")
        buf.extend(chunk)
    return bytes(buf)


def _transform(color: bytes) -> bytes:
    """A fake 'neural pass': channel reversal + a brightness offset."""
    if not CHANNEL_REVERSED and BRIGHTNESS_OFFSET == 0:
        return color
    out = bytearray(color)
    for i in range(0, len(out), 4):
        out[i], out[i + 2] = color[i + 2], color[i]
    if BRIGHTNESS_OFFSET:
        for i in range(len(out)):
            if i % 4 != 3:  # leave alpha alone
                out[i] = min(255, out[i] + BRIGHTNESS_OFFSET)
    return bytes(out)


def serve(fail_after: int = 0) -> int:
    stdin, stdout = sys.stdin.buffer, sys.stdout.buffer

    # --- stream header ----------------------------------------------------
    raw = _read_exact(stdin, VIDEO_HEADER_LEGACY_SIZE)
    magic = struct.unpack("<I", raw[:4])[0]
    if magic == VIDEO_MAGIC_EXT:
        raw = raw + _read_exact(stdin, struct.calcsize(HEADER_FMT) - VIDEO_HEADER_LEGACY_SIZE)
    elif magic != VIDEO_MAGIC_LEGACY:
        print(f"mock_worker: bad header magic 0x{magic:08X}", file=sys.stderr)
        return 2

    (magic, width, height, warmup, frame_count, profile, preset, style,
     auto_mask, ui_correction, intensity, local_tone, local_structure,
     skin_structure, full_w, full_h) = struct.unpack(HEADER_FMT, raw)
    print(f"mock_worker: stream {width}x{height} warmup={warmup} "
          f"full={full_w}x{full_h} profile={profile}", file=sys.stderr)

    color_w = full_w or width
    color_h = full_h or height
    frames_served = 0

    # --- frame loop -------------------------------------------------------
    while True:
        try:
            head = _read_exact(stdin, struct.calcsize(FRAME_FMT))
        except EOFError:
            print(f"mock_worker: EOF after {frames_served} frames", file=sys.stderr)
            return 0

        f_magic, index, reset, reserved, pts = struct.unpack(FRAME_FMT, head)

        if f_magic == SHM_MAGIC:
            # SHMI: the real worker opens a named section. The mock reads the
            # rest of the command, refuses politely (ok=0), and carries on with
            # the pipe path — exactly what the real worker does if it cannot map.
            _read_exact(stdin, struct.calcsize(SHM_FMT) - struct.calcsize(FRAME_FMT))
            stdout.write(struct.pack(SHM_ACK_FMT, SHM_ACK_MAGIC, 0, 0, 0, pts))
            stdout.flush()
            print("mock_worker: SHMI refused (pipe path in use)", file=sys.stderr)
            continue

        if f_magic != FRAME_MAGIC:
            print(f"mock_worker: bad frame magic 0x{f_magic:08X}", file=sys.stderr)
            return 2

        small_mv = bool(reserved & FRAME_FLAG_MOTION_SMALL)
        # The mock keeps the motion field at work resolution (it has no MOTS
        # scaler), so a small-motion frame is read at work resolution too and
        # the mismatch is reported rather than silently desyncing.
        if small_mv:
            print("mock_worker: MOTION_SMALL without MOTS — unsupported",
                  file=sys.stderr)
            return 2
        color_bytes = color_w * color_h * 4
        motion_bytes = width * height * 4

        color = _read_exact(stdin, color_bytes)
        _read_exact(stdin, motion_bytes)

        processed = _transform(color)

        stdout.write(struct.pack(OUT_FMT, OUT_MAGIC, index, 1, len(processed), 0, pts))
        stdout.write(processed)
        stdout.flush()

        frames_served += 1
        if fail_after and frames_served >= fail_after:
            print(f"mock_worker: failing after {frames_served} frames (--fail)",
                  file=sys.stderr)
            return 7


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mock_worker")
    p.add_argument("--fail", type=int, default=0, metavar="N",
                   help="exit non-zero after N frames")
    args = p.parse_args(argv)
    return serve(fail_after=args.fail)


if __name__ == "__main__":
    raise SystemExit(main())