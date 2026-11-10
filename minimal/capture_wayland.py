"""Wayland screen capture through the XDG Desktop Portal + PipeWire.

`minimal/capture.py` is X11/`mss`. On Wayland that is not merely slow, it is
wrong: the XWayland root window is black, so every frame arrives empty and the
whole pipeline looks broken when only the capture is. Measured on a KDE Plasma
Wayland session, both the "before" and "after" frames were pure black.

This backend gets frames from the compositor properly:

    portal handshake -> PipeWire fd + node  (minimal/portal.py)
      -> `pipewiresrc` (GStreamer) -> RGBA -> a pipe (default) or a memfd
      -> bytes -> numpy (H, W, 4)

The transport at the end of that chain is a choice (`--capture-transport pipe|shm`), made in
`_pipeline_args` and read in `grab`/`_read_frame`. `pipe` is the default and is what every
number in the plan was measured on; `shm` gives the chain a memfd instead of stdout, so the
frame is written into shared memory and read out of it rather than moved through the kernel's
pipe buffer. At 1080p the pipe carried 8.3 MB a frame for 5.1 ms of a 30.5 ms frame (1.6 GB/s,
pipe speed) and it has been at Linux's 1 MiB cap since the capture leg was priced, so the
transport is the only headroom left on this leg. The two routes are meant to be compared, not
swapped blind: the pipe stays the default until a window run proves the other one.

GStreamer is used through `gst-launch-1.0` rather than PyGObject: it keeps the
dependency to one pure-Python package (jeepney) instead of requiring
gobject-introspection bindings to be built, and the pipeline is visible in `ps`
while it runs, which is worth a lot when something does not work.

The interface matches `Capture` exactly — `.resolution`, `.grab()`, `.close()` —
so nothing downstream knows which backend is in use.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import fcntl
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

# The pipe buffer the pipeline's frames arrive through. The kernel default is 64 KiB, and at
# 2560x1440 that paces the whole capture leg: one RGBA frame is 14.7 MB, so the producer and
# the consumer take turns 230 times a frame. Measured on this box, same drain loop, one frame
# at a time from a stocked pipe: 12.70 ms/frame at 64 KiB, 8.90 ms at 1 MiB. 1 MiB is
# /proc/sys/fs/pipe-max-size on stock Linux, so ask for exactly that and accept less.
PIPE_BYTES = 1 << 20

# Where the frames go, chosen with `--capture-transport`. `pipe` is the default and is unchanged:
# the chain ends in `fdsink fd=1` and `grab` reads the frame out of the subprocess pipe. `shm`
# ends the chain in `fdsink fd=<memfd>` instead, so the frame is written into shared memory and
# read from there - one pread of the whole frame rather than ~8 reads through a 1 MiB pipe at the
# cap - and the reader's own offset arithmetic is what marks each frame's end.
PIPE = "pipe"
SHM = "shm"
TRANSPORTS = (PIPE, SHM)

# fallocate(2)'s flags for giving consumed pages back without moving the file's size.
FALLOC_FL_KEEP_SIZE = 0x01
FALLOC_FL_PUNCH_HOLE = 0x02

PAGE_BYTES = os.sysconf("SC_PAGE_SIZE")

_LIBC: "ctypes.CDLL | None" = None


def _libc() -> "ctypes.CDLL":
    """libc, for fallocate - os has no wrapper for the hole-punching flags."""
    global _LIBC
    if _LIBC is None:
        _LIBC = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
    return _LIBC


def _punch_hole(fd: int, offset: int, length: int) -> None:
    """fallocate(fd, PUNCH_HOLE|KEEP_SIZE, offset, length), or OSError with the kernel's errno."""
    ctypes.set_errno(0)
    rc = _libc().fallocate(ctypes.c_int(fd),
                           ctypes.c_int(FALLOC_FL_PUNCH_HOLE | FALLOC_FL_KEEP_SIZE),
                           ctypes.c_longlong(offset), ctypes.c_longlong(length))
    if rc != 0:
        raise OSError(ctypes.get_errno(), "fallocate(PUNCH_HOLE) refused")


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
    """Grab a screen or a single window on Wayland via the portal, as RGBA.

    Note on `monitor_idx`: the portal's SelectSources hands the choice to the
    user through a dialog, so which screen we get is their answer, not ours.
    The index is reported for the log and is otherwise not authoritative on
    this backend. The same is true of a window: the user picks it.

    `source` is SOURCE_MONITOR (a whole screen) or SOURCE_WINDOW (one window).
    A window is the cheaper thing to capture — the compositor's cost scales with
    the pixels — and it is what a game stream wants, since the desktop around
    the game is not being watched. Two consequences worth knowing:

      * The size is the one the run names (`--size`, or NEURALSCREEN_SIZE through the
        launcher) when it names one, and the compositor's reported size otherwise. Our
        pipeline forces the run's size in its caps, so a named size smaller than the screen
        is how the pass is run internally at 1080p and presented up at 1440p; a window
        resized afterwards is scaled back to the named size rather than seen at its new size.
        Renegotiating needs the per-frame size and a reader that can follow it; until then a
        resize stretches.
      * On a fractional-scaled display the portal may report logical dimensions
        while streaming pixels, and the frame's real size then differs from
        `width`/`height`. `grab` checks what arrives against what it expects and
        says so rather than handing back a mangled frame.
    """

    # The transport defaults, on the class as well as in __init__: a double built without
    # __init__ (a test's fake pipeline, or a caller duck-typing this class) is then on the pipe
    # route rather than raising AttributeError the first time it grabs a frame.
    transport = PIPE
    shm_poll = 0.0002
    shm_timeout = 30.0
    _shm_fd = None
    _frame_offset = 0
    _punch_failed = False

    def __init__(self, monitor_idx: int = 0, *, source: int = SOURCE_MONITOR,
                 gst: str = GST_LAUNCH, timeout: float = 120.0, log=print,
                 video_scale: bool = True, width: int | None = None,
                 height: int | None = None, transport: str = PIPE,
                 shm_poll: float = 0.0002, shm_timeout: float = 30.0):
        if transport not in TRANSPORTS:
            raise CaptureError(
                f"unknown capture transport {transport!r}: expected one of "
                f"{', '.join(TRANSPORTS)}")
        self.transport = transport
        self.shm_poll = float(shm_poll)
        self.shm_timeout = float(shm_timeout)
        self.monitor_idx = monitor_idx
        self.source = int(source)
        self.video_scale = bool(video_scale)
        self._log = log
        self._gst = gst
        self._proc: subprocess.Popen | None = None
        self._stderr: Path | None = None
        # Set by every grab: how long the first byte took, then the rest.
        # Present from construction so a caller can read them unconditionally.
        self.last_wait = 0.0
        self.last_read = 0.0
        # What the kernel granted for the frame pipe, for the report.
        self.pipe_bytes = 0
        # The shared-memory route's own state: the memfd the chain writes into, and how far into
        # it the reader has got (its own frame boundaries - the writer only ever moves forward).
        self._shm_fd: int | None = None
        self._frame_offset = 0
        self._punch_failed = False

        usable, why = requirements()
        if not usable:
            raise CaptureError(f"Wayland capture is not available: {why}")

        try:
            self._sc = open_screencast(types=self.source, timeout=timeout, log=log)
        except PortalError as exc:
            raise CaptureError(str(exc)) from exc

        reported_w, reported_h = int(self._sc.width), int(self._sc.height)
        requested = (int(width), int(height)) if (width and height) else None
        if requested:
            # A named size is the run's frame size, whatever the compositor reported. The gst
            # pipeline names it in its caps and videoscale produces it, so the request is
            # enforceable and it is the only way the pass can run internally at 1080p on a
            # 1440p screen and let the present scale the result back up - the largest lever
            # measured towards 60 fps. It also makes --size mean what its help says. The
            # reported size is the default when nobody names one; both are pinned by a test.
            self.width, self.height = requested
            if reported_w <= 0 or reported_h <= 0:
                self._log(f"  window stream reports no size; using the requested "
                          f"{self.width}x{self.height}")
            elif (reported_w, reported_h) != requested:
                self._log(f"  the portal reports {reported_w}x{reported_h}; this run asks for "
                          f"{self.width}x{self.height} and the pipeline scales to it")
        elif reported_w > 0 and reported_h > 0:
            self.width, self.height = reported_w, reported_h
        else:
            self._sc.close()
            raise CaptureError(
                "the portal did not report a stream size. A window stream often arrives "
                "as 0x0 (the compositor reports a size for a screen, not for a window), "
                "and the frame size has to be named: pass --size WxH, the size the window "
                "is running at — for a fullscreen game client that is the screen size")

        self._start_pipeline()

    def _pipeline_args(self) -> list[str]:
        """The pipeline, in one place so a failure can be read against it.

        videoscale is deliberate, and it is also a third pass over the frame:
        the chain already copies through PipeWire, converts format and writes
        down the pipe, and at 2560x1440 the whole thing measures 33% of a core —
        about 42ms of CPU per frame — which is the same order as the penalty the
        worker pays in `send` when the source is the portal rather than a
        synthetic card. `video_scale=False` drops it so that cost can be
        compared; the risk is that the portal's reported size and the stream's
        actual size disagree — fractional scaling on Plasma is the easy way to
        hit this — and then caps negotiation fails instead of scaling. That
        failure is loud and names itself, which is the trade.

        `queue max-size-buffers=1 leaky=downstream` keeps us on the newest frame
        instead of chewing through a backlog: this is a mirror, not a recording.
        Where it sits is the point, and it sits *before* the convert/scale pair.
        At the end of the chain the drop happened downstream of both expensive
        elements, so every frame the compositor produced was converted and scaled
        and only then discarded - `r2026-11-08-1080p-window-b` spent 8.52 s of CPU
        across a 9.50 s window (90% of one core) to present 120 frames, with a
        core busy while the worker wanted it for its own 21.71 ms frame. Ahead of
        the pair the queue holds raw PipeWire buffers and the expensive elements
        see only the frames the pipe actually takes. The caps do not move, so no
        pixel changes; `docs/M0-FINDINGS.md` carries the prediction - `capture
        cpu:` falls while the frame time does not rise.

        Only the chain's *end* depends on the transport: `fdsink fd=1` writes each frame into
        our stdout pipe, `fdsink fd=<memfd>` writes it into shared memory instead. Both take the
        same RGBA caps, so the two routes are one variable apart and a run of each is comparable.
        """
        caps = (f"video/x-raw,format=RGBA,width={self.width},height={self.height},"
                f"pixel-aspect-ratio=1/1")
        args = [
            self._gst, "-q",
            "pipewiresrc", f"fd={self._sc.fd}", *self._sc.pipewire_target,
            # Before the expensive pair, not after them. See the note above.
            "!", "queue", "max-size-buffers=1", "leaky=downstream",
            "!", "videoconvert",
        ]
        if self.video_scale:
            args += ["!", "videoscale"]
        args += [
            "!", caps,
        ]
        if self.transport == SHM:
            if self._shm_fd is None:
                raise CaptureError(
                    "the shared-memory capture has no memfd to write frames into")
            args += ["!", "fdsink", f"fd={self._shm_fd}", "sync=false"]
        else:
            args += ["!", "fdsink", "fd=1"]
        return args

    def _start_pipeline(self) -> None:
        # The child needs the PipeWire fd. pass_fds both marks it inheritable
        # for the child and keeps every other descriptor out of it.
        fd = self._sc.fd
        err_fd, err_path = tempfile.mkstemp(prefix="nsl-gst-", suffix=".log")
        os.close(err_fd)          # only the path is wanted; the descriptor itself would leak
        self._stderr = Path(err_path)
        err = open(self._stderr, "wb")
        try:
            try:
                self._proc = self._spawn(err, fd)
            except OSError as exc:
                if self.transport != SHM:
                    self._sc.close()
                    raise CaptureError(f"could not start {self._gst}: {exc}") from exc
                # Said out loud, once, and then the pipe route, which works. A shared-memory
                # chain that cannot start must not cost the run - but it must not be silent
                # either, because the timings would then be read as the new transport's.
                self._log(f"  ! shared-memory capture did not start ({exc}); "
                          f"falling back to the pipe")
                self._close_shm()
                self.transport = PIPE
                try:
                    self._proc = self._spawn(err, fd)
                except OSError as exc:
                    self._sc.close()
                    raise CaptureError(f"could not start {self._gst}: {exc}") from exc
        finally:
            # The child holds its own copy; keeping ours open would leak one
            # descriptor per capture for as long as the process lives.
            err.close()
        if self.transport == PIPE:
            self._enlarge_pipe()
        else:
            self._log(f"  transport: shared memory (memfd fd={self._shm_fd}); "
                      f"one pread per frame")
        self._log(f"  pipeline pid {self._proc.pid}: "
                  f"{' '.join(self._pipeline_args())}")

    def _spawn(self, err, pw_fd: int) -> subprocess.Popen:
        """Start the gst chain, on whichever transport is in force.

        On the shared-memory route the frame never enters a pipe: the memfd is created here, the
        chain is handed it, and `grab` reads the frame out of it. stdout goes to /dev/null so the
        child cannot deadlock on a pipe nobody drains.
        """
        if self.transport == SHM:
            self._shm_fd = self._open_memfd()
            return subprocess.Popen(
                self._pipeline_args(),
                stdout=subprocess.DEVNULL,
                stderr=err,
                pass_fds=(pw_fd, self._shm_fd),
            )
        return subprocess.Popen(
            self._pipeline_args(),
            stdout=subprocess.PIPE,
            stderr=err,
            pass_fds=(pw_fd,),
        )

    @staticmethod
    def _open_memfd() -> int:
        """The memory file the chain writes frames into.

        memfd_create rather than a path under /dev/shm: it has no name for anything else to find
        or collide with, and the kernel frees it when the last descriptor to it closes - so a
        capture that dies cannot leave a frame of a game sitting in shared memory.
        """
        try:
            return os.memfd_create("nsl-capture", 0)
        except AttributeError as exc:      # Python < 3.8
            raise OSError("this Python has no os.memfd_create (3.8+)") from exc

    def _enlarge_pipe(self) -> None:
        """Ask for a buffer big enough that the pipe does not pace the capture.

        Best-effort and logged, not required: the request can be refused (the limit is
        /proc/sys/fs/pipe-max-size and growing beyond it needs privileges), and a capture
        that runs at the old speed is still a working capture. F_SETPIPE_SZ returns the
        size actually granted, which is what gets logged.
        """
        stream = self._proc.stdout if self._proc is not None else None
        if stream is None:
            return
        try:
            before = fcntl.fcntl(stream.fileno(), fcntl.F_GETPIPE_SZ)
            after = fcntl.fcntl(stream.fileno(), fcntl.F_SETPIPE_SZ, PIPE_BYTES)
        except (OSError, ValueError) as exc:
            # ValueError as well as OSError: fcntl rejects a bad descriptor before it ever
            # reaches the kernel, so a closed pipe raises ValueError, and a resize that
            # cannot even be attempted must leave a working capture behind, not end it.
            self._log(f"  pipe buffer unchanged ({exc}); the capture will run at the "
                      f"64 KiB default")
            return
        self.pipe_bytes = int(after)
        if after == before:
            self._log(f"  pipe buffer {before // 1024} KiB (unchanged)")
        else:
            self._log(f"  pipe buffer {before // 1024} -> {after // 1024} KiB")

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
        if self.transport == SHM:
            # On this route the frames come from the memfd, not from the child's stdout, so what
            # has to be alive is the memory file.
            if self._shm_fd is None:
                raise CaptureError("the shared-memory capture is not running")
        elif self._proc is None or self._proc.stdout is None:
            raise CaptureError("the capture pipeline is not running")
        need = self.width * self.height * 4
        self.last_wait = None
        self.last_read = None

        t0 = time.monotonic()
        frame = self._read_frame(need)
        total = time.monotonic() - t0

        if self.last_wait is None:      # no chunk ever arrived — cannot happen
            self.last_wait, self.last_read = total, 0.0
        else:
            self.last_read = total - self.last_wait
        return frame

    def cpu_seconds(self) -> float | None:
        """CPU time the capture pipeline has used, or None if it is not running.

        This is the chain's own cost — PipeWire delivery, videoconvert,
        videoscale, the pipe — and it is invisible in the grab time. Measured
        in the MVP, the same 2560x1440 frame cost `send` 114.2ms arriving
        through the portal against 67.3ms produced synthetically, and none of
        that difference showed up in the capture leg. If this comes back near a
        core, that work is competing with the worker rather than waiting for it.
        """
        from minimal.cpu import process_cpu_seconds

        proc = self._proc
        return process_cpu_seconds(proc.pid if proc is not None else None)

    @property
    def pipeline_pid(self) -> int | None:
        return self._proc.pid if self._proc is not None else None

    def _read_frame(self, need: int) -> np.ndarray:
        """Read exactly `need` bytes, or explain why we could not.

        The pipeline writing an unexpected number of bytes is the normal shape
        of a caps negotiation failure, so the error carries the pipeline's own
        stderr: GStreamer names the problem, and paraphrasing it would only lose
        the detail.
        """
        if self.transport == SHM:
            return self._read_frame_shm(need)
        got = 0
        stream = self._proc.stdout if self._proc is not None else None
        if stream is None:
            raise CaptureError("the capture pipeline is not running")
        # Read into the frame's own buffer. Building bytes and then viewing them cost a
        # second copy of all 14.7 MB (measured: 6.74 ms/frame this way against 8.71 through
        # a chunk list and b"".join at a 1 MiB pipe, and 10.56 against 12.49 at the default).
        frame = np.empty((self.height, self.width, 4), dtype=np.uint8)
        view = memoryview(frame).cast("B")
        # readinto1, not readinto: readinto blocks for the WHOLE request the way read does
        # and would swallow the wait/read split this loop exists to report. readinto1
        # returns as soon as some data has arrived.
        read_into = getattr(stream, "readinto1", None)
        if read_into is None:
            read_into = getattr(stream, "readinto", stream.read)
        # When the first chunk comes back is when the frame started arriving —
        # the difference between the compositor being slow and our copy being
        # slow. read1 (not read) because read blocks for the WHOLE request, which
        # hides the split entirely.
        t0 = time.monotonic()
        while got < need:
            read = read_into(view[got:])
            # read could be bytes (the stream.read fallback) or a count; count either.
            count = len(read) if isinstance(read, (bytes, bytearray)) else read
            if not count:
                raise CaptureError(
                    "the PipeWire pipeline ended before a whole frame arrived "
                    f"({got} of {need} bytes).\n" + self._stderr_tail())
            if isinstance(read, (bytes, bytearray)):
                view[got:got + count] = read
            if self.last_wait is None:
                self.last_wait = time.monotonic() - t0
            got += count
        return frame

    def _read_frame_shm(self, need: int) -> np.ndarray:
        """One frame out of the memfd, at the offset the chain's writer has reached.

        The chain is a sequential writer into a memory file: its file position only moves forward,
        so frame N begins at N * need and the reader's own arithmetic is what marks the boundary.
        That is the whole reason this route is a single process - there is no framing to invent
        and no second gst process to read a socket - and it is what the pipe cannot offer, because
        a pipe hides the boundary until the byte count runs out.

        The split `grab` reports is kept. `last_wait` is the time until the frame is in the file
        (the writer's clock: the compositor's, our convert/scale, ours for the pipe version), and
        `last_read` is the extraction - one pread of the whole frame, where the pipe route loops
        ~8 reads through the 1 MiB buffer. Only the frame's own bytes are copied, out of memory
        rather than out of a kernel pipe buffer.

        Waiting is a poll because a memory file has no readiness: reads never block, they just
        return what is there. The interval is a parameter (`shm_poll`) so the cost of noticing a
        frame early can be traded against CPU, and the deadline is a parameter too, because a
        chain that dies mid-run would otherwise leave `grab` spinning forever.
        """
        fd = self._shm_fd
        if fd is None:
            raise CaptureError("the shared-memory capture has no memfd")
        offset = self._frame_offset
        t0 = time.monotonic()
        deadline = t0 + self.shm_timeout
        while True:
            try:
                size = os.fstat(fd).st_size
            except OSError as exc:
                raise CaptureError(
                    f"the shared-memory capture's memfd is unusable: {exc}") from exc
            if size >= offset + need:
                break
            if time.monotonic() > deadline:
                raise CaptureError(
                    f"the pipeline wrote no whole frame into shared memory within "
                    f"{self.shm_timeout:.0f}s ({max(0, size - offset)} of {need} bytes of the "
                    f"frame at offset {offset}).\n" + self._stderr_tail())
            time.sleep(self.shm_poll)
        self.last_wait = time.monotonic() - t0

        frame = np.empty((self.height, self.width, 4), dtype=np.uint8)
        view = memoryview(frame).cast("B")
        got = 0
        while got < need:
            chunk = os.pread(fd, need - got, offset + got)
            if not chunk:
                raise CaptureError(
                    f"the shared-memory frame ended early ({got} of {need} bytes at "
                    f"offset {offset}).\n" + self._stderr_tail())
            view[got:got + len(chunk)] = chunk
            got += len(chunk)
        self._frame_offset = offset + need
        self._release_pages(offset, need)
        return frame

    def _release_pages(self, offset: int, length: int) -> None:
        """Give the consumed frame's pages back to the kernel.

        The writer's position only advances, so the memfd grows for as long as the capture runs
        and a 1080p session at 30 fps would hold 8.3 MB a frame in memory. PUNCH_HOLE with
        KEEP_SIZE zeroes the consumed region without moving the file's size, so it cannot race a
        writer that has already passed it - only bytes below the writer's position are punched,
        and it never returns to them. Best effort: a kernel or filesystem that refuses leaves a
        correct but memory-hungry run, which is worth one line rather than an exception, and the
        flag stops it trying the same failing call every frame.
        """
        fd = self._shm_fd
        if fd is None or self._punch_failed:
            return
        start = offset - (offset % PAGE_BYTES)
        end = (offset + length) - ((offset + length) % PAGE_BYTES)
        if end <= start:          # a frame smaller than a page has nothing whole to give back
            return
        try:
            _punch_hole(fd, start, end - start)
        except OSError as exc:
            self._punch_failed = True
            self._log(f"  ! consumed frames are no longer being released from shared memory "
                      f"({exc}); the run's memory grows with the frames")

    def _close_shm(self) -> None:
        """Drop our descriptor on the memfd; the kernel frees the file with the last one."""
        if self._shm_fd is not None:
            try:
                os.close(self._shm_fd)
            except OSError:
                pass
            self._shm_fd = None

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
        self._close_shm()
        sc = getattr(self, "_sc", None)
        if sc is not None:
            sc.close()

    def __enter__(self) -> "PortalCapture":
        return self

    def __exit__(self, *exc) -> None:
        self.close()