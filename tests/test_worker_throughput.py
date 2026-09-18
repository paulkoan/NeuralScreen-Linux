"""The throughput harness, and the protocol invariants it depends on.

The worker itself cannot be run here (no Wine, no GPU), so what these cover is
everything upstream of it: that the harness builds a stream the worker will
accept, and the two facts that make that true.
"""

from __future__ import annotations

import io
import struct
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import protocol  # noqa: E402
from minimal.worker import stream_header  # noqa: E402

THROUGHPUT = REPO / "experiments" / "worker_throughput"
PARAMS = {"profile": 1, "preset": 0, "style": 1, "auto_mask": 0,
          "ui_correction": 0, "intensity": 1.0, "local_tone": 1.0,
          "local_structure": 1.0, "skin_structure": 1.0}


class Sink:
    """What send_frame sees: it only ever touches .stdin."""

    def __init__(self, buf):
        self.stdin = buf


def frame_bytes(index: int = 0) -> bytes:
    import numpy as np
    buf = io.BytesIO()
    rgba = np.zeros((2, 2, 4), dtype=np.uint8)
    motion = np.zeros((2, 2, 2), dtype=np.float16)
    protocol.send_frame(Sink(buf), index, rgba, motion, reset=index == 0, pts=0)
    return buf.getvalue()


def test_a_frame_message_starts_with_the_hosts_tag():
    """The worker reads ONE byte, then branches: 'B' is a build message, 'F' is a
    frame. It does that because the two share no prefix, so the first byte of the
    magic IS the tag — and a stream whose first byte is neither dies immediately
    with no useful error. Pinned because nothing else would catch it."""
    got = frame_bytes()
    assert got[:1] == b"F", (
        f"a frame message must start with the tag 'F', got {got[:1]!r}")
    assert struct.unpack_from(protocol.FRAME_FMT, got)[0] == protocol.FRAME_MAGIC


def test_the_header_cannot_be_mistaken_for_a_frame_or_build_message():
    """The header goes out before the tag loop, so it must not look like a
    message that loop would branch on."""
    header = stream_header(64, 64, 2, PARAMS)
    assert header[:1] not in (b"F", b"B"), (
        "the header must not collide with the message tags")
    assert struct.unpack_from(protocol.HEADER_FMT, header)[0] == protocol.VIDEO_MAGIC


def test_a_frame_is_eight_bytes_per_pixel_in_and_four_back():
    """This is what makes the pipe floor computable, and it is the number the
    verdict turns on: 4 bytes of colour + 2 float16 motion channels in, 4 out."""
    import numpy as np
    assert np.dtype(np.float16).itemsize == 2
    px = 2 * 2
    got = len(frame_bytes()) - struct.calcsize(protocol.FRAME_FMT)
    assert got == px * 8, f"expected 8 bytes/pixel, frame carried {got / px}/pixel"


def test_the_header_is_built_in_one_place():
    """The harness has to produce a stream the worker accepts; a second copy of
    the header layout would drift, and a rejected header kills the run on frame
    0 — which has already happened once, from an even-rounding bug."""
    src = (REPO / "minimal" / "worker.py").read_text()
    assert "stream_header(" in src, "the Worker must use the shared builder"
    assert "struct.pack(\n            HEADER_FMT" not in src, (
        "the header is packed inline again — that is the second copy")


def test_the_feeder_rejects_a_bad_size_without_touching_wine(tmp_path):
    """A smoke test that needs no Wine: the argument check must come first."""
    r = subprocess.run([sys.executable, str(THROUGHPUT / "feed.py"),
                        "--size", "notasize"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "not WxH" in r.stderr


def test_the_runner_is_valid_bash_and_uses_the_shared_tail():
    runner = THROUGHPUT / "run.sh"
    assert subprocess.run(["bash", "-n", str(runner)],
                          capture_output=True).returncode == 0
    text = runner.read_text()
    assert "report.sh" in text and "push_report" in text
    assert "GIT_ASKPASS=" not in text, "auth belongs in the shared tail"
    # Both sizes, because one cannot separate a slow worker from a slow pipe.
    assert "1280x720" in text and "2560x1440" in text


def test_the_runner_is_executable():
    assert (THROUGHPUT / "run.sh").stat().st_mode & 0o111
    assert (THROUGHPUT / "feed.py").stat().st_mode & 0o111