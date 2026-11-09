"""What capture transports this box can actually offer - a probe, not an assertion.

The capture chain writes each frame into a pipe (`... ! fdsink fd=1`) and the client reads it. At
1080p that is 8.3 MB a frame and it measures **5.1 ms** of a 30.5 ms frame - about 1.6 GB/s, which
is pipe speed - and the pipe is already at Linux's 1 MiB default cap, so it cannot simply be given
more. The pixel channel is the argument for looking elsewhere: moving *that* from a pipe to shared
memory took the whole frame 39.7 -> 26.4 ms. The capture is the same kind of cost on the other end
of the pipeline and it is the largest single client stage left.

Before anything is built on it, the box has to be able to offer something. Three candidates, all
reachable from where the client already stands:

  * `shmsink` / `shmsrc` (gst-plugins-bad) - the chain writes into a shared segment the client
    reads directly, which removes the pipe's extra copy outright.
  * `memfd_create` + `mmap` - gst keeps writing to an fd, but the fd is memory, so the client reads
    the frame rather than copying it out of a kernel buffer.
  * a larger pipe - only if `fs.pipe-max-size` can be raised, which is a system setting and not
    ours to change.

This test SKIPS either way, deliberately. Whether a plugin is installed is a property of the box,
not a bug in this repo, and a test that goes red when it is absent would block every other code
change the loop wants to make. The skip message carries the findings, so the answer arrives in the
run's own output.
"""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _gst_element_present(element: str) -> str:
    """'yes', 'no', or 'no gst-inspect' - never an exception, this is a probe."""
    exe = shutil.which("gst-inspect-1.0")
    if not exe:
        return "no gst-inspect-1.0"
    try:
        r = subprocess.run([exe, element], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return "gst-inspect failed"
    return "yes" if r.returncode == 0 else "no"


def _try_memfd() -> str:
    """Linux 3.17+. Called for real: the number in a header is not the number in the kernel."""
    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        fd = libc.memfd_create(b"ns-probe", 0)
    except (OSError, AttributeError) as exc:
        return f"unavailable ({type(exc).__name__})"
    if fd < 0:
        return f"unavailable (errno {ctypes.get_errno()})"
    os.close(fd)
    return "yes"


def _pipe_max() -> str:
    try:
        n = int(Path("/proc/sys/fs/pipe-max-size").read_text().strip())
    except (OSError, ValueError):
        return "unreadable"
    return f"{n // 1024} KiB" + (" (at the cap already)" if n <= 1024 * 1024 else "")


def test_the_capture_transport_alternatives_are_reported():
    findings = [
        f"shmsink {_gst_element_present('shmsink')}",
        f"shmsrc {_gst_element_present('shmsrc')}",
        f"memfd_create {_try_memfd()}",
        f"pipe-max-size {_pipe_max()}",
        f"gst-launch-1.0 {'yes' if shutil.which('gst-launch-1.0') else 'ABSENT'}",
    ]
    # One line, because that is what pytest puts in its short summary.
    pytest.skip("capture transports - " + "; ".join(findings))
