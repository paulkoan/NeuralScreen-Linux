#!/usr/bin/env python3
"""Standalone Wayland capture probe — no Wine, no GPU, no worker.

    tools/wayland_probe.py                 # check everything, then capture 3 frames
    tools/wayland_probe.py --frames 10     # more frames
    tools/wayland_probe.py --save-frame f.png
    tools/wayland_probe.py --check-only    # prerequisites only, no dialog

Why this is separate from the MVP: capture and the neural pass are independent
questions, and mixing them cost a round — with a black capture, "the pass is
broken" and "we are feeding it black" produce identical evidence. This proves
the capture on its own, and it needs nothing but the desktop.

The last step is the one that matters. It reports per-channel standard deviation
of the frames it read: a Wayland session that is capturing correctly gives a
frame with structure, and the failure this whole exercise started with was two
frames that were uniformly black. `--save-frame` writes one out to look at.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Must happen before the third-party imports below: the shebang resolves to
# whatever `python3` is on PATH, and without the venv activated that interpreter
# has neither numpy nor jeepney. See tools/venv_boot.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from venv_boot import reexec_into_repo_venv  # noqa: E402

reexec_into_repo_venv(__file__, modules=("numpy", "jeepney"))

sys.path.insert(0, str(REPO))

PASS, FAIL, WARN, INFO = "  \033[32m✓\033[0m", "  \033[31m✗\033[0m", "  \033[33m!\033[0m", "  ·"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="wayland_probe", description=__doc__.split("\n")[0])
    ap.add_argument("--frames", type=int, default=3, help="frames to read (default 3)")
    ap.add_argument("--save-frame", metavar="PATH", help="write the first frame as a PNG")
    ap.add_argument("--check-only", action="store_true",
                    help="prerequisites only; do not open the portal or prompt")
    ap.add_argument("--timeout", type=float, default=120.0,
                    help="seconds to wait for the screen-selection dialog")
    args = ap.parse_args(argv)

    problems = 0

    def ok(msg):
        print(f"{PASS} {msg}")

    def bad(msg):
        nonlocal problems
        problems += 1
        print(f"{FAIL} {msg}")

    def warn(msg):
        print(f"{WARN} {msg}")

    def info(msg):
        print(f"{INFO} {msg}")

    print("=" * 62)
    print(" Wayland capture probe")
    print("=" * 62)

    # --- 1. the session -----------------------------------------------------
    print("\n--- 1. session ---")
    session = os.environ.get("XDG_SESSION_TYPE", "")
    info(f"XDG_SESSION_TYPE   {session or '<unset>'}")
    info(f"XDG_CURRENT_DESKTOP {os.environ.get('XDG_CURRENT_DESKTOP', '<unset>')}")
    info(f"WAYLAND_DISPLAY    {os.environ.get('WAYLAND_DISPLAY', '<unset>')}")
    info(f"DISPLAY            {os.environ.get('DISPLAY', '<unset>')}")
    info(f"XDG_RUNTIME_DIR    {os.environ.get('XDG_RUNTIME_DIR', '<unset>')}")
    if session != "wayland" and not os.environ.get("WAYLAND_DISPLAY"):
        warn("not a Wayland session — the X11/`--source screen` backend is the right one here")
    else:
        ok("Wayland session")
    if not os.environ.get("XDG_RUNTIME_DIR"):
        bad("XDG_RUNTIME_DIR is unset; the session bus and PipeWire both need it")

    # --- 2. python side -----------------------------------------------------
    print("\n--- 2. python dependencies ---")
    try:
        import jeepney
        ok(f"jeepney {jeepney.__version__} (D-Bus with fd passing)")
    except ImportError:
        bad("jeepney is missing — pip install jeepney")

    # --- 3. gstreamer -------------------------------------------------------
    print("\n--- 3. gstreamer ---")
    gst = shutil.which("gst-launch-1.0")
    if gst:
        ok(f"gst-launch-1.0: {gst}")
    else:
        bad("gst-launch-1.0 is missing — Arch: gstreamer, Debian: gstreamer1.0-tools")
    if shutil.which("gst-inspect-1.0"):
        proc = __import__("subprocess").run(
            ["gst-inspect-1.0", "pipewiresrc"], capture_output=True, text=True)
        if proc.returncode == 0:
            ok("pipewiresrc element present")
        else:
            bad("gst-inspect-1.0 cannot find pipewiresrc — Arch: gst-plugin-pipewire, "
                "Debian: gstreamer1.0-pipewire")
    else:
        warn("gst-inspect-1.0 not found; cannot check for pipewiresrc")

    # --- 4. the portal ------------------------------------------------------
    print("\n--- 4. xdg desktop portal ---")
    from minimal import portal
    usable, why = portal.available()
    if usable:
        ok(why)
    else:
        bad(why)
    version = portal.screencast_version() if usable else 0
    if version:
        if version >= 6:
            ok(f"interface version {version} — streams will be targeted by "
               f"pipewire-serial (node ids are deprecated for this)")
        else:
            warn(f"interface version {version} — no pipewire-serial; "
                 f"falling back to node id targeting")

    if args.check_only:
        print()
        print("=" * 62)
        if problems:
            print(f" RESULT: {problems} problem(s) above — fix those first")
            return 1
        print(" RESULT: prerequisites OK (--check-only, no portal call made)")
        return 0

    if not usable:
        print()
        print("=" * 62)
        print(" RESULT: BLOCKED — the prerequisites above must pass first")
        return 2

    # --- 5. the handshake ---------------------------------------------------
    print("\n--- 5. ScreenCast handshake ---")
    print("     A dialog will appear asking which screen to share.")
    print("     Choose one, and remember the choice can be revoked later.")
    print()
    try:
        sc = portal.open_screencast(timeout=args.timeout, log=info)
    except portal.PortalError as exc:
        bad(f"handshake failed: {exc}")
        print()
        print("=" * 62)
        print(" RESULT: FAIL — the portal handshake did not complete")
        return 1

    ok(f"session   {sc.session_path}")
    ok(f"node      {sc.node_id}   serial {sc.serial}")
    ok(f"size      {sc.width}x{sc.height}")
    ok(f"target    {' '.join(sc.pipewire_target)}")
    ok(f"pipewire fd {sc.fd}")

    # --- 6. frames ----------------------------------------------------------
    print("\n--- 6. reading frames ---")
    import numpy as np
    from minimal.capture import CaptureError
    from minimal.capture_wayland import PortalCapture

    class _Attached(PortalCapture):
        """Reuse the pipeline from the session we already negotiated."""
        def __init__(self, sc, **kw):     # noqa: D107 - deliberately not the base init
            self.monitor_idx = kw.get("monitor_idx", 0)
            self._log = kw.get("log", info)
            self._gst = kw.get("gst", "gst-launch-1.0")
            self._proc = None
            self._stderr = None
            self._sc = sc
            self.width, self.height = int(sc.width), int(sc.height)
            self._start_pipeline()

    cap = None
    try:
        cap = _Attached(sc, log=info)
        frames = []
        for i in range(max(1, args.frames)):
            frame = cap.grab()
            frames.append(frame)
            rgb = frame[..., :3].astype(np.float32)
            print(f"     frame {i}: {frame.shape[1]}x{frame.shape[0]} "
                  f"mean {rgb.mean():6.1f}  std {rgb.std():6.2f}  "
                  f"per-channel std {[round(float(rgb[..., c].std()), 1) for c in range(3)]}")
        ok(f"read {len(frames)} frame(s)")
    except CaptureError as exc:
        bad(f"reading frames failed: {exc}")
        print()
        print("=" * 62)
        print(" RESULT: FAIL — the portal worked, the PipeWire read did not")
        return 1
    finally:
        if cap is not None:
            cap._proc = None          # frames came through; keep sc's fd for sc.close()
            cap.close()
        sc.close()

    # --- verdict on the pixels ---------------------------------------------
    print("\n--- 7. did we actually capture anything? ---")
    last = frames[-1][..., :3].astype(np.float32)
    std = float(last.std())
    blank = std < 0.5
    info(f"last frame: mean {last.mean():.1f}  std {std:.2f}")
    if blank:
        bad("the frame is flat — the compositor accepted the session but is "
            "handing back an empty image")
        problems += 1
    else:
        ok(f"the frame has content (std {std:.2f})")

    if args.save_frame:
        from minimal.capture import save_png
        save_png(args.save_frame, frames[-1])
        ok(f"wrote {args.save_frame} (opaque PNG, 3 channels)")

    print()
    print("=" * 62)
    if blank:
        print(" RESULT: FAIL — capture produced a blank frame")
        return 1
    print(" RESULT: PASS — Wayland capture works, with real pixels.")
    if args.save_frame:
        print(f" Next: look at {args.save_frame}. Then run")
    else:
        print(" Next: re-run with --save-frame /tmp/shot.png and look at it, then run")
    print("   python -m minimal --source wayland --frames 30 --save-before b.png --save-after a.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())