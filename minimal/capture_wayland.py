"""Wayland screen capture through the XDG Desktop Portal + PipeWire.

`minimal/capture.py` is X11/`mss`. On Wayland that is not merely slow, it is
wrong: the XWayland root window is black, so every frame arrives empty and the
whole pipeline looks broken when only the capture is. Measured on a KDE Plasma
Wayland session, both the "before" and "after" frames were pure black.

This backend gets frames from the compositor properly:

    portal handshake -> PipeWire fd + node  (minimal/portal.py)
      -> `pipewiresrc` (GStreamer) -> RGBA -> our own stdout pipe
      -> bytes -> numpy (H, W, 4)

GStreamer is used through `gst-launch-1.0` rather than PyGObject: it keeps the
dependency to one pure-Python package (jeepney) instead of requiring
gobject-introspection bindings to be built, and the pipeline is visible in `ps`
while it runs, which is worth a lot when something does not work.

The interface matches `Capture` exactly — `.resolution`, `.grab()`, `.close()` —
so nothing downstream knows which backend is in use.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np

from minimal.capture import CaptureError
from minimal.portal import SOURCE_MONITOR, PortalError, open_screencast

GST_LAUNCH = "gst-launch-1.0"


def requirements() -> tuple[bool, str]:
    """(usable, why not) — checked before we make the user answer a dialog."""
    if shutil.which(GST_LAUNCH) is None:
        return False, f"{GST_LAUNCH} is not installed (Arch: gstreamer; Debian: gstreamer1.0-tools)"
    probe = subprocess.run([GST_LAUNCH.replace("gst-launch", "gst-inspect"),
                            "pipewiresrc"], capture_output=True, text=True)
    if probe.returncode != 0:
        return False, (
            "GStreamer has no pipewiresrc element — install the PipeWire plugin "
            "(Arch: gst-plugin-pipewire; Debian: gstreamer1.0-pipewire)")
    from minimal import portal
    return portal.available()


class PortalCapture:
    """Grab the screen on Wayland via the portal, as RGBA frames.

    Note on `monitor_idx`: the portal's SelectSources hands the choice to the
    user through a dialog, so which screen we get is their answer, not ours.
    The index is reported for the log and is otherwise not authoritative on
    this backend.
    """

    def __init__(self, monitor_idx: int = 0, *, gst: str = GST_LAUNCH,
                 timeout: float = 120.0, log=print):
        self.monitor_idx = monitor_idx
        self._log = log
        self._gst = gst
        self._proc: subprocess.Popen | None = None
        self._stderr: Path | None = None
        # Set by every grab: how long the first byte took, then the rest.
        # Present from construction so a caller can read them unconditionally.
        self.last_wait = 0.0
        self.last_read = 0.0

        usable, why = requirements()
        if not usable:
            raise CaptureError(f"Wayland capture is not available: {why}")

        try:
            self._sc = open_screencast(types=SOURCE_MONITOR, timeout=timeout, log=log)
        except PortalError as exc:
            raise CaptureError(str(exc)) from exc

        self.width = int(self._sc.width)
        self.height = int(self._sc.height)
        if self.width <= 0 or self.height <= 0:
            self._sc.close()
            raise CaptureError(
                "the portal did not report a stream size; cannot size frames")

        self._start_pipeline()

    def _pipeline_args(self) -> list[str]:
        """The pipeline, in one place so a failure can be read against it.

        videoscale is deliberate. The portal's reported size and the stream's
        actual size can disagree — fractional scaling on Plasma is the easy way
        to hit this — and a negotiation failure is a much worse outcome than one
        extra passthrough element.

        `queue max-size-buffers=1 leaky=downstream` keeps us on the newest frame
        instead of chewing through a backlog: this is a mirror, not a recording.
        """
        caps = (f"video/x-raw,format=RGBA,width={self.width},height={self.height},"
                f"pixel-aspect-ratio=1/1")
        return [
            self._gst, "-q",
            "pipewiresrc", f"fd={self._sc.fd}", *self._sc.pipewire_target,
            "!", "videoconvert",
            "!", "videoscale",
            "!", caps,
            "!", "queue", "max-size-buffers=1", "leaky=downstream",
            "!", "fdsink", "fd=1",
        ]

    def _start_pipeline(self) -> None:
        # The child needs the PipeWire fd. pass_fds both marks it inheritable
        # for the child and keeps every other descriptor out of it.
        fd = self._sc.fd
        self._stderr = Path(tempfile.mkstemp(prefix="nsl-gst-", suffix=".log")[1])
        err = open(self._stderr, "wb")
        try:
            self._proc = subprocess.Popen(
                self._pipeline_args(),
                stdout=subprocess.PIPE,
                stderr=err,
                pass_fds=(fd,),
            )
        except OSError as exc:
            self._sc.close()
            raise CaptureError(f"could not start {self._gst}: {exc}") from exc
        finally:
            # The child holds its own copy; keeping ours open would leak one
            # descriptor per capture for as long as the process lives.
            err.close()
        self._log(f"  pipeline pid {self._proc.pid}: "
                  f"{' '.join(self._pipeline_args())}")

    @property
    def resolution(self) -> tuple[int, int]:
        return self.width, self.height

    def grab(self) -> np.ndarray:
        """One frame as (H, W, 4) uint8 RGBA.

        The grab is timed in two halves:

          last_wait  until the frame's first bytes arrive.
          last_read  draining the rest of the frame out of the pipe.

        The reading of those two is not obvious and the first attempt got it
        wrong. `BufferedReader.read(n)` blocks until it has all n bytes, so a
        single read call swallows the whole transfer and `read` comes out as
        0.0ms no matter who is slow — which is exactly what the box reported
        (wait 125.1ms, read 0.0ms). So the loop uses `read1`, which returns as
        soon as data is available, and the two halves separate.

        With read1 the split separates the two cases, verified by driving this
        same loop from a stocked pipe and from a producer that dribbles a frame
        out over 120ms:

          pipe stocked (producer ahead of us)   wait 0.1ms   read  18.9ms
          producer dribbling, ~120ms per frame  wait 0.1ms   read 159.1ms

        So the discriminator is `read`:

          read ~19ms (this box, 2560x1440)  the pipe was stocked and we are
                                            draining it at memory speed, so the
                                            producer is keeping up and the
                                            limit is ours
          read >> that                      the bytes arrived slowly, so the
                                            compositor is the limit

        `wait` is ~0 whenever the producer streams continuously, which it does;
        a large wait means it stalls between frames. The first version of this
        used a plain buffered read and reported read 0.0ms for every case,
        because read(n) blocks for the whole request and swallows the split.
        """
        if self._proc is None or self._proc.stdout is None:
            raise CaptureError("the capture pipeline is not running")
        need = self.width * self.height * 4
        self.last_wait = None
        self.last_read = None

        t0 = time.monotonic()
        buf = self._read_exact(need)
        total = time.monotonic() - t0

        if self.last_wait is None:      # no chunk ever arrived — cannot happen
            self.last_wait, self.last_read = total, 0.0
        else:
            self.last_read = total - self.last_wait
        return np.frombuffer(buf, dtype=np.uint8).reshape(self.height, self.width, 4)

    def _read_exact(self, need: int) -> bytes:
        """Read exactly `need` bytes, or explain why we could not.

        The pipeline writing an unexpected number of bytes is the normal shape
        of a caps negotiation failure, so the error carries the pipeline's own
        stderr: GStreamer names the problem, and paraphrasing it would only lose
        the detail.
        """
        chunks: list[bytes] = []
        got = 0
        stream = self._proc.stdout if self._proc is not None else None
        if stream is None:
            raise CaptureError("the capture pipeline is not running")
        # When the first chunk comes back is when the frame started arriving —
        # the difference between the compositor being slow and our copy being
        # slow. read1 (not read) because read blocks for the WHOLE request, which
        # hides the split entirely.
        read1 = getattr(stream, "read1", None)
        t0 = time.monotonic()
        while got < need:
            chunk = read1(need - got) if read1 is not None else stream.read(need - got)
            if not chunk:
                raise CaptureError(
                    "the PipeWire pipeline ended before a whole frame arrived "
                    f"({got} of {need} bytes).\n" + self._stderr_tail())
            if self.last_wait is None:
                self.last_wait = time.monotonic() - t0
            chunks.append(chunk)
            got += len(chunk)
        return b"".join(chunks)

    def _stderr_tail(self, lines: int = 12) -> str:
        if self._stderr is None or not self._stderr.exists():
            return "(the pipeline wrote no stderr)"
        text = self._stderr.read_text(errors="replace").strip().splitlines()
        if not text:
            return "(the pipeline wrote no stderr)"
        return "pipeline stderr:\n  " + "\n  ".join(text[-lines:])

    def close(self) -> None:
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            if self._proc.stdout is not None:
                try:
                    self._proc.stdout.close()
                except Exception:
                    pass
            self._proc = None
        sc = getattr(self, "_sc", None)
        if sc is not None:
            sc.close()

    def __enter__(self) -> "PortalCapture":
        return self

    def __exit__(self, *exc) -> None:
        self.close()