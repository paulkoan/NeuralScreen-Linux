"""Worker lifecycle for the MVP — launch `wine nvngx.dll --live` and talk to it.

Everything about the wire format lives in protocol.py, which already matches
native/dlss5-feed-host64.cpp byte for byte (the C++ side has static_asserts on
every struct size; tests/test_protocol_sizes.py checks the Python side against
the same numbers).

This module only owns the *process*: how to start it, when it is ready, and how
to stop it. The transport is the pipe path (colour and motion inline). Shared
memory is deliberately not used: SharedFrameBuffer relies on
`mmap.mmap(..., tagname=...)`, which is a Windows-only keyword, and Wine's
named-mapping namespace is not POSIX shm — the pipe is the path that works.
"""

from __future__ import annotations

import os
import struct
import subprocess
import threading
import time
from pathlib import Path

from paths import NATIVE_DIR
from protocol import (HEADER_FMT, VIDEO_MAGIC, WorkerReader, send_frame)

# Same caps the original pipeline uses. NGX feature 18 goes silent at 4K
# (verified upstream), so the work resolution is capped at 2560x1440.
WORK_MAX_W = 2560
WORK_MAX_H = 1440

# How long to wait for the worker's first reply before calling it dead.
FIRST_FRAME_TIMEOUT = 60.0


def work_size(width: int, height: int) -> tuple[int, int]:
    """The NGX work resolution for a frame of width x height.

    Same rules as settings_io._work_size, kept local so the MVP does not drag
    the whole settings subsystem in: never larger than the source frame, never
    larger than the 1440p NGX ceiling, and rounded down to even numbers.
    """
    w, h = int(width), int(height)
    if w > WORK_MAX_W or h > WORK_MAX_H:
        k = min(WORK_MAX_W / w, WORK_MAX_H / h)
        w, h = max(64, int(w * k)), max(64, int(h * k))
    w -= w % 2
    h -= h % 2
    return max(64, w), max(64, h)


def default_launcher() -> list[str]:
    """The command that starts the real worker.

    native/run_worker.sh sets WINEPREFIX and execs `wine nvngx.dll --live`.
    Overridable with NS_WORKER_CMD so the tests can point the pipeline at the
    mock worker instead.
    """
    override = os.environ.get("NS_WORKER_CMD")
    if override:
        import shlex
        return shlex.split(override)
    return ["bash", str(NATIVE_DIR / "run_worker.sh")]


class Worker:
    """A running NR worker process plus its reader thread and log buffer."""

    def __init__(self, width: int, height: int, work_w: int, work_h: int,
                 params: dict, warmup: int = 2,
                 cmd: list[str] | None = None,
                 cwd: Path | None = None):
        self.width, self.height = int(width), int(height)
        self.work_w, self.work_h = int(work_w), int(work_h)
        self.params = params
        self.warmup = int(warmup)
        self.cmd = cmd or default_launcher()
        self.cwd = cwd or NATIVE_DIR
        self.logs: list[str] = []
        self._log_stop = threading.Event()
        self.proc: subprocess.Popen | None = None
        self.reader: WorkerReader | None = None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Start the process and send the stream header.

        The header tells the worker the work resolution and the NR parameters.
        full_w/full_h stay 0 (legacy 1:1 path): the MVP works at the frame's own
        resolution, scaled to the NGX ceiling, and lets the worker hand back the
        same size. The upscaling path is a later milestone.
        """
        self.proc = subprocess.Popen(
            self.cmd,
            cwd=str(self.cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
        )
        threading.Thread(target=self._drain_stderr, daemon=True,
                         name="worker-stderr").start()

        # The reader owns a thread reading the worker's stdout for the life of
        # the process. Its width/height are the *output* frame size.
        self.reader = WorkerReader(self.proc, self.width, self.height, None)

        header = struct.pack(
            HEADER_FMT,
            VIDEO_MAGIC, self.work_w, self.work_h, self.warmup, 0,
            self.params["profile"], self.params["preset"], self.params["style"],
            self.params["auto_mask"], self.params["ui_correction"],
            self.params["intensity"], self.params["local_tone"],
            self.params["local_structure"], self.params["skin_structure"],
            0, 0,
        )
        self.proc.stdin.write(header)
        self.proc.stdin.flush()

    def _drain_stderr(self) -> None:
        """Keep the worker's stderr pipe empty or it blocks on a full buffer."""
        assert self.proc is not None and self.proc.stderr is not None
        try:
            for raw in iter(self.proc.stderr.readline, b""):
                if self._log_stop.is_set():
                    break
                line = raw.decode("utf-8", "replace").rstrip()
                self.logs.append(line)
                if len(self.logs) > 4000:
                    del self.logs[: len(self.logs) - 4000]
        except Exception:
            pass

    # -- per-frame ---------------------------------------------------------

    def send(self, index: int, rgba, motion, reset: bool, pts: int = 0) -> None:
        """Send one frame down the pipe (colour + motion inline).

        A dead worker surfaces as BrokenPipeError on the write, which is not a
        useful thing to see in a traceback: it is translated into a plain error
        carrying the worker's last stderr lines, which is where the real cause
        (an NGX failure, a Wine crash) actually lives.
        """
        assert self.proc is not None and self.proc.stdin is not None
        try:
            send_frame(self.proc, index, rgba, motion, reset, pts, None)
        except (BrokenPipeError, OSError) as exc:
            raise RuntimeError(
                f"the worker died while sending frame {index} ({exc}). "
                "Last stderr:\n  " + "\n  ".join(self.logs[-15:] or ["(no output)"])
            ) from exc

    def recv(self, index: int, timeout: float = FIRST_FRAME_TIMEOUT):
        """Wait for the result of frame `index`. None = the worker sent no pixels."""
        assert self.reader is not None
        return self.reader.recv(index, timeout)

    # -- teardown ----------------------------------------------------------

    def stop(self, timeout: float = 10.0) -> int | None:
        """Close stdin (EOF makes the worker clean up NGX and exit), then wait.

        The worker's own cleanup path on EOF releases the D3D12 device and NGX
        before returning, which is why closing the pipe is preferred to kill().
        """
        self._log_stop.set()
        if self.proc is None:
            return None
        try:
            if self.proc.stdin and not self.proc.stdin.closed:
                self.proc.stdin.close()
        except OSError:
            pass
        try:
            return self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            try:
                return self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                return self.proc.wait(timeout=5)

    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def wait_for_alive(self, seconds: float = 5.0) -> bool:
        """True if the worker is still running after `seconds` (startup smoke)."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if not self.is_alive():
                return False
            time.sleep(0.05)
        return self.is_alive()