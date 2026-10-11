"""The native worker's shared-memory channels, spoken by the client's own definitions.

SHMI and OUTS are what take 14.7MB of colour, 14.7MB of motion and 14.7MB of pixels off the
pipe. The network is 12ms of a frame, so that traffic was the largest cost left; through a
mapping the same round trip measured ~2ms.

Both directions are driven here against a real process. NR is off (bypass), so no device is
needed — what this proves is the part that would otherwise be discovered on the GPU box:
the section this client creates is the section the worker opens, the frame it puts there is
the frame that comes back, and a header-only frame is still a frame.
"""
import os
import struct
import subprocess

import numpy as np
import pytest

from protocol import (FRAME_FLAG_BYPASS, FRAME_FLAG_SHM, OUT_BYTES_IN_SHM, OUT_FMT,
                      OUT_MAGIC, SHM_ACK_MAGIC, SHM_FMT, SHM_MAGIC, OUTS_ACK_MAGIC,
                      OUTS_FMT, OUTS_MAGIC, SharedFrameBuffer, send_frame, send_out)

NATIVE_BIN = os.environ.get("NS_ODL_NATIVE_BIN")
W = H = 64
HEADER_FMT = "<10I4f2I"
VIDEO_MAGIC = 0x33563544
FRAME_MAGIC = 0x314D5246


def read_exact(stream, size: int) -> bytes:
    stream = getattr(stream, "stdout", stream)     # a Popen or its stdout, either is fine
    out = b""
    while len(out) < size:
        block = stream.read(size - len(out))
        if not block:
            raise EOFError(f"the worker stopped after {len(out)} of {size} reply bytes")
        out += block
    return out


def ack(worker, expected_magic: int) -> int:
    magic, ok, flags, reserved, pts = struct.unpack("<4Iq", read_exact(worker, 24))
    assert magic == expected_magic, hex(magic)
    return ok


def reply(worker):
    magic, index, ok, body_bytes, ngx, pts = struct.unpack(OUT_FMT, read_exact(worker, struct.calcsize(OUT_FMT)))
    assert magic == OUT_MAGIC and ok == 1, (hex(magic), ok)
    pixels = None if body_bytes == OUT_BYTES_IN_SHM else read_exact(worker, body_bytes)
    return index, body_bytes, pixels


@pytest.mark.skipif(not NATIVE_BIN,
                    reason="set NS_ODL_NATIVE_BIN to a built dlss5vk to drive the real mode")
def test_the_native_worker_reads_the_frame_and_returns_it_through_sections():
    worker = subprocess.Popen([NATIVE_BIN, "serve", "--model", "/nonexistent-model"],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    shm = SharedFrameBuffer(W, H, W, H)
    try:
        # The section the client just created is the one the worker opens by name.
        assert os.path.exists(f"/dev/shm/{shm.name}"), (
            "the client did not create a POSIX section, so shm_open cannot find it")
        worker.stdin.write(struct.pack(HEADER_FMT, VIDEO_MAGIC, W, H, 2, 0, 1, 0, 1, 0, 0,
                                       1.0, 1.0, 1.0, 1.0, 0, 0))
        worker.stdin.write(struct.pack(SHM_FMT, SHM_MAGIC, shm.color_capacity,
                                       shm.motion_capacity, 0, 0, shm.name.encode()))
        worker.stdin.flush()
        assert ack(worker, SHM_ACK_MAGIC) == 1, "the frame channel was refused"
        shm.negotiated = True

        rgba = (np.arange(W * H * 4, dtype=np.int32) % 256).astype(np.uint8).reshape(H, W, 4)
        motion = np.zeros((H, W, 2), dtype=np.float16)

        # 1. The frame goes into the mapping; only its 24-byte header goes down the pipe.
        #    With no OUTS negotiated the pixels still come back inline.
        send_frame(worker, 0, rgba, motion, True, 0, shm=shm, bypass=True)
        index, body_bytes, pixels = reply(worker)
        assert index == 0 and body_bytes == W * H * 4, (index, body_bytes)
        assert np.frombuffer(pixels, np.uint8).reshape(H, W, 4).tolist() == rgba.tolist(), (
            "the frame in the mapping did not come back unchanged")

        # 2. Negotiate the pixel channel: the same frame's answer now lands in the second
        #    section, and the reply says so instead of carrying 16KB.
        shm.open_out(W, H)
        assert os.path.exists(f"/dev/shm/{shm.out_name}")
        send_out(worker, W, H, shm.out_name)
        assert ack(worker, OUTS_ACK_MAGIC) == 1, "the pixel channel was refused"

        rgba2 = (255 - rgba).astype(np.uint8)
        send_frame(worker, 1, rgba2, motion, False, 0, shm=shm, bypass=True)
        index, body_bytes, pixels = reply(worker)
        assert index == 1 and body_bytes == OUT_BYTES_IN_SHM, (index, body_bytes)
        assert pixels is None, "the pixels came down the pipe as well as into the section"
        out = shm.read_out()
        assert out is not None, "the section held a torn frame"
        assert out.tolist() == rgba2.tolist(), "the published frame is not the frame that went in"
        # 3. A frame that declares no motion field, followed by one that does not: the
        #    worker must skip exactly that many bytes, or it reads the next frame's header
        #    as the tail of this frame's motion. Nothing in this mode reads a motion field,
        #    which is what makes leaving it out safe - and a worker that wants one must not
        #    be sent a frame carrying the flag.
        send_frame(worker, 2, rgba, motion, False, 0, shm=shm, bypass=True, no_motion=True)
        index, body_bytes, pixels = reply(worker)
        assert index == 2, index
        send_frame(worker, 3, rgba2, motion, False, 0, shm=shm, bypass=True)
        index, body_bytes, pixels = reply(worker)
        assert index == 3, "the frame after a no-motion frame was misread"
        assert shm.read_out().tolist() == rgba2.tolist(), "the stream lost its alignment"
    finally:
        shm.close()
        worker.stdin.close()
        code = worker.wait(timeout=30)
        stderr = worker.stderr.read().decode("utf-8", "replace")
    assert code == 0, f"the worker exited {code}: {stderr}"
