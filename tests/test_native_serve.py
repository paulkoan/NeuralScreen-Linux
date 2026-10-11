"""The native worker: `dlss5vk serve` from the OpenDLSS-NR port.

The port is shipped as a patch against someone else's repository, so what can be
checked here without a GPU is exactly what would cost an afternoon on the box:

  * that the wire format this mode claims to speak is the one protocol.py packs
    (a field added on one side and not the other desyncs the stream on frame 0),
  * and, when NS_ODL_NATIVE_BIN points at a built binary, that our own client can
    drive it end to end.

The second one is possible with no GPU because of FRAME_FLAG_BYPASS: the pixels come
back untouched and no device is ever created. Framing, the header parse, the refusal of
commands the mode does not implement and the end-of-stream handshake are all exercised
here. Only the network needs the GPU box.
"""

from __future__ import annotations

import os
import re
import struct
from pathlib import Path

import numpy as np
import pytest

import protocol as wire
from minimal.loop import DEFAULT_PARAMS
from minimal.worker import Worker

REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "experiments" / "opendlss_port" / "linux-port.patch"
NATIVE_BIN = os.environ.get("NS_ODL_NATIVE_BIN")

# The C++ constant -> the value protocol.py defines. A name that disappears from the
# mode makes this fail rather than silently stop checking it.
MAGICS = {
    "kVideoMagic": wire.VIDEO_MAGIC,
    "kFrameMagic": wire.FRAME_MAGIC,
    "kOutMagic": wire.OUT_MAGIC,
    "kShmMagic": wire.SHM_MAGIC,
    "kShmAck": wire.SHM_ACK_MAGIC,
    "kMotionMagic": wire.MOTION_MAGIC,
    "kMotionAck": wire.MOTION_ACK_MAGIC,
    "kWindowMagic": wire.WINDOW_MAGIC,
    "kWindowAck": wire.WINDOW_ACK_MAGIC,
    "kResizeMagic": wire.RESIZE_MAGIC,
    "kResizeAck": wire.RESIZE_ACK_MAGIC,
    "kDdaMagic": wire.DDA_MAGIC,
    "kDdaAck": wire.DDA_ACK_MAGIC,
    "kOutsMagic": wire.OUTS_MAGIC,
    "kOutsAck": wire.OUTS_ACK_MAGIC,
    "kGrayMagic": wire.GRAY_MAGIC,
    "kGrayAck": wire.GRAY_ACK_MAGIC,
    "kWgcMagic": wire.WGC_MAGIC,
    "kWgcAck": wire.WGC_ACK_MAGIC,
}

FLAGS = {
    "kFrameFlagWantPixels": wire.FRAME_FLAG_WANT_PIXELS,
    "kFrameFlagMotionSmall": wire.FRAME_FLAG_MOTION_SMALL,
    "kFrameFlagNoColor": wire.FRAME_FLAG_NO_COLOR,
    "kFrameFlagBypass": wire.FRAME_FLAG_BYPASS,
}

SIZES = {
    "kHeaderBytes": struct.calcsize(wire.HEADER_FMT),
    "kFrameHeaderBytes": struct.calcsize(wire.FRAME_FMT),
    "kOutHeaderBytes": struct.calcsize(wire.OUT_FMT),
    "kAckBytes": struct.calcsize(wire.SHM_ACK_FMT),
    "kShmBytes": struct.calcsize(wire.SHM_FMT),
}


def serve_source() -> str:
    """The serve.cpp the patch adds, out of the patch file itself."""
    text = PATCH.read_text()
    start = text.index("diff --git a/src/serve.cpp")
    rest = text[start:]
    following = rest.find("\ndiff --git ", 10)
    return rest if following < 0 else rest[:following]


def test_the_mode_speaks_the_wire_format_protocol_py_packs():
    """Every magic, flag and header size, against the Python that has to agree.

    The Wine worker's side of this is checked by tests/test_protocol_sizes.py. This is
    the same check for the mode that replaced it: the two are only interchangeable if
    these agree exactly, and a disagreement shows up as a stream that desyncs on the
    first frame rather than as anything that names the field.
    """
    source = serve_source()
    for pattern, expected, what in (
            (r"constexpr uint32_t (k\w+)\s*=\s*(0x[0-9A-Fa-f]+)u?", MAGICS, "magic"),
            (r"constexpr uint32_t (kFrameFlag\w+)\s*=\s*(0x[0-9A-Fa-f]+)u?", FLAGS, "frame flag"),
            (r"constexpr size_t (k\w+Bytes)\s*=\s*(\d+)", SIZES, "header size")):
        found = {name: int(value, 0) for name, value in re.findall(pattern, source)}
        for name, value in expected.items():
            assert name in found, f"{name} is gone from src/serve.cpp (a {what})"
            assert found[name] == value, (
                f"{name} is {found[name]:#x}, protocol.py says {value:#x}: the client and "
                f"the native worker would disagree")


def test_the_mode_is_reachable_from_the_command_line():
    """A mode nobody can invoke is the same as no mode."""
    patch = PATCH.read_text()
    assert "runServe(argc, argv)" in patch and 'strcmp(argv[1], "serve")' in patch, (
        "main.cpp no longer dispatches the serve mode")
    assert "|serve " in patch or "serve --model" in patch, "the usage line should name it"


@pytest.mark.skipif(not NATIVE_BIN,
                    reason="set NS_ODL_NATIVE_BIN to a built dlss5vk to drive the real mode")
def test_our_client_drives_the_native_worker():
    """The integration, on the real protocol, with a real process on the other end.

    NR is off (bypass) so this needs no device: what it proves is the part that would
    otherwise be discovered on the GPU box - the header this client writes, the frame
    it writes and the reply it expects all line up with the mode that reads them.
    """
    width = height = 64
    assert NATIVE_BIN is not None  # the skipif above is the real guard
    worker = Worker(width=width, height=height, work_w=width, work_h=height,
                    params=DEFAULT_PARAMS, warmup=0,
                    cmd=[NATIVE_BIN, "serve", "--model", "/nonexistent-model"], bypass=True)
    worker.start()
    try:
        # Saturated and near-zero values included on purpose: bypass must not touch them,
        # and a pipeline that clamped somewhere would show up here.
        rgba = (np.arange(width * height * 4, dtype=np.int32) % 256).astype(np.uint8).reshape(height, width, 4)
        rgba[0, :, :] = 0
        rgba[-1, :, :] = 255
        motion = np.zeros((height, width, 2), dtype=np.float16)

        for index in (0, 1):
            worker.send(index, rgba, motion, reset=index == 0)
            got_index, frame = worker.recv_any(timeout=30)
            assert got_index == index
            assert frame is not None, "the mode returned no pixels for a bypassed frame"
            assert frame.shape == (height, width, 4)
            assert (frame == rgba).all(), "a bypassed frame came back changed"

        assert any("serve:" in line for line in worker.logs), (
            "the client is not draining the mode's stderr, so its diagnostics are lost")
    finally:
        code = worker.stop()
    assert code == 0, f"the mode exited {code} on a closed stream instead of 0"