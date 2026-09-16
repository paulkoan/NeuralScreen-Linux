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

# The optical-flow resolution a MOTS motion field is sent at; the worker
# upscales it to the work size on the GPU. The protocol never names it, it only
# calls it "~320x180 = the flow field size".
FLOW_W, FLOW_H = 320, 180


def work_size(width: int, height: int, scale: float = 1.0) -> tuple[int, int]:
    """The NGX work resolution for a frame of width x height.

    Mirrors settings_io._work_size, the product's rule, so a measurement here
    means something there. `scale` is the product's `work_scale`: the network
    works on a fraction of the frame and the result is scaled back to full, so
    a smaller scale buys frame rate at the cost of the effect's own resolution.

    Never larger than the source frame, never larger than the 1440p NGX
    ceiling. At 1:1 the frame is used unrounded: rounding to even once turned a
    539-pixel-high window into a 540-high work size — larger than the frame it
    came from — and the worker died on the header. A downscale therefore rounds
    DOWN, and an odd size at 1:1 stays on the path the product verified.
    """
    w, h = int(width), int(height)
    if scale < 1.0:
        w = max(64, int(width * scale) // 2 * 2)
        h = max(64, int(height * scale) // 2 * 2)
    if w > WORK_MAX_W or h > WORK_MAX_H:
        k = min(WORK_MAX_W / w, WORK_MAX_H / h)
        w = max(64, int(w * k) // 2 * 2)
        h = max(64, int(h * k) // 2 * 2)
    return min(w, int(width)), min(h, int(height))


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


# The launch environment the worker needs. One source of truth: the shell
# scripts carry the same string (they have to — bash cannot import it), and
# tests/test_worker_env_consistency.py fails if any of them drift.
#
# Wine must be told to use the NATIVE translation layers. Through its builtins
# two different failures follow, in this order of discovery:
#   0xBAD00001 FAIL_FeatureNotSupported — NGX Core not found at all
#   0xBAD00002 FAIL_PlatformError       — NGX Core loads, but NVAPI cannot
#                                          report the GPU to it
# dxvk-nvapi needs DXVK's dxgi AND d3d11 extension points, and vkd3d-proton's
# d3d12. The driver's nvngx_dlls must load too, hence nvngx_dlssnr native-only.
DLL_OVERRIDES = (
    "d3d12=n,b;d3d12core=n,b;d3d11=n,b;dxgi=n,b;"
    "nvapi64=n,b;nvofapi64=n,b;nvngx_dlssnr=n"
)

# Without this dxvk-nvapi leaves the NGX/DLSS part of NVAPI disabled ("to
# disable DXVK's nvapiHack in DXVK"), and NGX Core's platform check then fails.
ENABLE_NVAPI = "1"


def worker_env(base: dict | None = None, nr_small: bool = False) -> dict:
    """The environment to launch the worker with.

    nr_small is the product's NS_NR_SMALL: the network runs on a scaled-down
    frame and the worker scales the result back up to full size, so the output
    stays full resolution while the neural cost drops with the pixel count. It
    is the only mechanism that actually buys frame rate — handing the network
    the whole screen at a smaller *work* size ("upscaling" mode) does not,
    because it still processes full-res pixels.
    """
    env = dict(os.environ if base is None else base)
    env["WINEDLLOVERRIDES"] = env.get("NS_WINEDLLOVERRIDES", DLL_OVERRIDES)
    env.setdefault("DXVK_ENABLE_NVAPI", ENABLE_NVAPI)
    env.setdefault("WINEPREFIX", os.path.expanduser("~/.neuralscreen/wine"))
    if nr_small:
        env["NS_NR_SMALL"] = "1"
    return env


class Worker:
    """A running NR worker process plus its reader thread and log buffer."""

    def __init__(self, width: int, height: int, work_w: int, work_h: int,
                 params: dict, warmup: int = 2,
                 cmd: list[str] | None = None,
                 cwd: Path | None = None,
                 full_w: int = 0, full_h: int = 0,
                 nr_small: bool = False, motion_small: bool = False):
        self.width, self.height = int(width), int(height)
        self.work_w, self.work_h = int(work_w), int(work_h)
        self.params = params
        # Non-zero means "the colour frame is this big and the work size is
        # something else", which is what the worker needs in order to scale the
        # network's result back up to the full frame. Zero keeps the path the
        # MVP has always used: colour and work are the same size.
        self.full_w, self.full_h = int(full_w), int(full_h)
        self.nr_small = bool(nr_small)
        self.motion_small = bool(motion_small)
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

        full_w/full_h stay 0 on the default path: colour and work are the same
        size and the worker hands back what it was given. With --work-scale they
        carry the real frame size instead, which is what lets the worker scale
        the network's result back up to the full frame — and NS_NR_SMALL=1 in
        the environment is what makes the network actually run on the smaller
        frame. Without that variable a smaller work size changes nothing: the
        feature is handed full-res pixels either way.
        """
        self.proc = subprocess.Popen(
            self.cmd,
            cwd=str(self.cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=worker_env(nr_small=self.nr_small),
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
            self.full_w, self.full_h,
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
            send_frame(self.proc, index, rgba, motion, reset, pts, None,
                       motion_small=self.motion_small)
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