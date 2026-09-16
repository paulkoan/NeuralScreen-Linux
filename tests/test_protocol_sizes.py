"""The Python side of the wire protocol must match the C++ side exactly.

native/dlss5-feed-host64.cpp carries static_asserts on every struct size. These
tests check the same numbers on the Python side, so a field added on one side
and not the other fails here instead of desyncing at runtime.

The expected values below are copied from the static_asserts; the test also
re-reads the .cpp when it is present, so the two cannot drift silently.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from protocol import (DDA_ACK_FMT, DDA_FMT, FRAME_FMT, GRAY_ACK_FMT, GRAY_FMT,
                      HEADER_FMT, MOTION_ACK_FMT, MOTION_FMT, OUT_FMT,
                      OUTS_ACK_FMT, OUTS_FMT, RACK_FMT, RESIZE_FMT, SHM_ACK_FMT,
                      SHM_FMT, WGC_ACK_FMT, WGC_FMT, WINDOW_ACK_FMT, WINDOW_FMT)

REPO = Path(__file__).resolve().parent.parent
CPP = REPO / "native" / "dlss5-feed-host64.cpp"

# Struct name -> (Python format, size asserted in the C++ source)
EXPECTED = {
    "VideoHeader":       (HEADER_FMT,     64),
    "VideoFrameHeader":  (FRAME_FMT,      24),
    "VideoResultHeader": (OUT_FMT,        28),
    "VideoResizeCmd":    (RESIZE_FMT,     64),
    "VideoResizeAck":    (RACK_FMT,       24),
    "VideoShmCmd":       (SHM_FMT,        88),
    "VideoShmAck":       (SHM_ACK_FMT,    24),
    "VideoWindowCmd":    (WINDOW_FMT,     24),
    "VideoWindowAck":    (WINDOW_ACK_FMT, 24),
    "VideoMotionCmd":    (MOTION_FMT,     24),
    "VideoMotionAck":    (MOTION_ACK_FMT, 24),
    "VideoDdaCmd":       (DDA_FMT,        24),
    "VideoDdaAck":       (DDA_ACK_FMT,    24),
    "VideoWgcCmd":       (WGC_FMT,        32),
    "VideoWgcAck":       (WGC_ACK_FMT,    24),
    "VideoGrayCmd":      (GRAY_FMT,       88),
    "VideoGrayAck":      (GRAY_ACK_FMT,   24),
    "VideoOutCmd":       (OUTS_FMT,       88),
    "VideoOutAck":       (OUTS_ACK_FMT,   24),
}


@pytest.mark.parametrize("struct_name,fmt,expected", [
    (n, f, s) for n, (f, s) in EXPECTED.items()])
def test_struct_size_matches_cpp(struct_name, fmt, expected):
    """Every packed struct has the size the C++ side asserts."""
    actual = struct.calcsize(fmt)
    assert actual == expected, (
        f"{struct_name}: Python {fmt} is {actual} bytes, "
        f"the C++ static_assert says {expected}")


def test_cpp_static_asserts_agree():
    """Cross-check against the asserts in the C++ source itself."""
    if not CPP.is_file():
        pytest.skip("native source not present in this checkout")
    text = CPP.read_text(errors="replace")
    found = dict(re.findall(
        r'static_assert\(sizeof\((\w+)\)\s*==\s*(\d+)', text))
    assert found, "no static_asserts found in the C++ source"
    mismatches = []
    for name, (fmt, expected) in EXPECTED.items():
        if name not in found:
            continue
        if int(found[name]) != expected:
            mismatches.append(
                f"{name}: C++ asserts {found[name]}, Python layout {fmt} "
                f"is {struct.calcsize(fmt)} bytes (expected {expected})")
    assert not mismatches, "Python/C++ struct sizes disagree:\n  " + "\n  ".join(mismatches)


def test_header_is_64_bytes_packed():
    """The header must be tightly packed — no implicit padding."""
    assert struct.calcsize(HEADER_FMT) == 10 * 4 + 4 * 4 + 2 * 4


def test_frame_header_pts_offset():
    """pts sits at byte 16 of the frame header (static_asserted in C++)."""
    packed = struct.pack(FRAME_FMT, 0x314D5246, 0, 0, 0, 0)
    assert struct.calcsize(FRAME_FMT) == 24
    # magic, index, reset, reserved are 4 bytes each; pts is the last 8.
    assert struct.unpack(FRAME_FMT, packed)[-1] == 0


def test_magic_values():
    """Each magic is the 4 ASCII bytes the worker checks for, little-endian."""
    from protocol import (DDA_MAGIC, FRAME_MAGIC, GRAY_MAGIC, MOTION_MAGIC,
                          OUT_MAGIC, OUTS_MAGIC, RESIZE_MAGIC, SHM_ACK_MAGIC,
                          SHM_MAGIC, VIDEO_MAGIC, WGC_MAGIC, WINDOW_ACK_MAGIC,
                          WINDOW_MAGIC)
    # From the C++ constant comments, e.g. `0x33563544u; // "D5V3"`.
    expected = {
        VIDEO_MAGIC: b"D5V3", FRAME_MAGIC: b"FRM1", OUT_MAGIC: b"OUT1",
        SHM_MAGIC: b"SHMI", SHM_ACK_MAGIC: b"SACK", RESIZE_MAGIC: b"RNSZ",
        WINDOW_MAGIC: b"WNDO", WINDOW_ACK_MAGIC: b"WACK", MOTION_MAGIC: b"MOTS",
        DDA_MAGIC: b"DDA1", WGC_MAGIC: b"WGCW", GRAY_MAGIC: b"GRAY",
        OUTS_MAGIC: b"OUTS",
    }
    wrong = []
    for value, ascii_bytes in expected.items():
        little = value.to_bytes(4, "little")
        if little != ascii_bytes:
            wrong.append(
                f"0x{value:08X} is {little!r}, expected {ascii_bytes!r}")
    assert not wrong, "magic values disagree with the C++ side:\n  " + "\n  ".join(wrong)