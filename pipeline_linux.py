"""Worker lifecycle for Linux — launch, restart, and tear down the Wine worker.

Replaces pipeline.py's start_worker / restart_worker / shutdown_worker with
versions that launch the NGX worker under Wine via native/run_worker.sh instead
of running it directly on Windows.

All cross-platform protocol logic (WorkerReader, SharedFrameBuffer negotiation,
header packing) is kept as-is — only the subprocess.Popen call changes.
"""

from __future__ import annotations

import os
import struct
import subprocess
import sys
import threading
import time

from paths import NATIVE_DIR, WORKER_EXE
from protocol import (HEADER_FMT, VIDEO_MAGIC, SharedFrameBuffer,
                      WorkerReader, _negotiate_shm)


# ---------------------------------------------------------------------------
# Constants — same as the original pipeline.py
# ---------------------------------------------------------------------------

RESTART_COOLDOWN = 0.5      # seconds, before applying a deferred setting
RESTART_WARMUP = 10         # warmup frames after a resolution change
RACK_TIMEOUT = 20.0         # seconds to wait for RACK after RNSZ
MAX_CONSECUTIVE_RESTARTS = 3
AUTO_REVIVE_BACKOFF = 30.0  # seconds


# ---------------------------------------------------------------------------
# Stderr drain — same as the original, but without Win32-specific filtering
# ---------------------------------------------------------------------------

def _drain_stderr(worker, logs: list[str], stop: threading.Event) -> None:
    """Background drain of the worker's stderr.

    Prevents the pipe buffer from filling up (which would hang the worker).
    One thread per worker; finishes on EOF or the stop event.
    """
    try:
        for raw in iter(worker.stderr.readline, b""):
            if stop.is_set():
                break
            line = raw.decode("utf-8", "replace").rstrip()
            logs.append(line)
            if len(logs) > 2000:
                del logs[: len(logs) - 2000]
            # Forward lines tagged with phase markers to stdout
            if os.environ.get("NS_PHASE") == "1" or any(
                tag in line for tag in ("[present]", "[spout]", "[arch]",
                                        "[pure]", "[host]", "[cap]", "[dda]",
                                        "[pw]")
            ):
                print(line)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Worker launch — Wine variant
# ---------------------------------------------------------------------------

_RUN_WORKER_SH = NATIVE_DIR / "run_worker.sh"


def start_worker(
    params: dict,
    width: int,
    height: int,
    warmup: int,
    full_w: int = 0,
    full_h: int = 0,
    shm: SharedFrameBuffer | None = None,
) -> tuple[subprocess.Popen, list[str], WorkerReader, threading.Event]:
    """Start the NGX worker under Wine in --live mode and send the header.

    Uses native/run_worker.sh instead of launching nvngx.dll directly.

    width/height = work resolution (the NGX feature).
    full_w/full_h = input frame size (the worker resizes on the GPU).

    Returns (worker, logs, reader, stop).
    """
    if not _RUN_WORKER_SH.is_file():
        raise FileNotFoundError(
            f"worker launcher not found: {_RUN_WORKER_SH}\n"
            "Ensure native/run_worker.sh exists and is executable."
        )

    cmd = ["bash", str(_RUN_WORKER_SH)]
    env = os.environ.copy()
    env.setdefault("WINEPREFIX", os.path.expanduser("~/.neuralscreen/wine"))

    worker = subprocess.Popen(
        cmd,
        cwd=str(NATIVE_DIR),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    logs: list[str] = []
    stop = threading.Event()
    threading.Thread(target=_drain_stderr, args=(worker, logs, stop),
                     daemon=True).start()

    out_w = full_w if full_w else width
    out_h = full_h if full_h else height
    reader = WorkerReader(worker, out_w, out_h, shm)

    header = struct.pack(
        HEADER_FMT,
        VIDEO_MAGIC, width, height, int(warmup), 0,
        params["profile"], params["preset"], params["style"],
        params["auto_mask"], params["ui_correction"],
        params["intensity"], params["local_tone"],
        params["local_structure"], params["skin_structure"],
        int(full_w), int(full_h),
    )
    worker.stdin.write(header)
    worker.stdin.flush()

    if shm is not None:
        _negotiate_shm(worker, reader, shm)

    return worker, logs, reader, stop


# ---------------------------------------------------------------------------
# Worker restart
# ---------------------------------------------------------------------------

def restart_worker(
    worker: subprocess.Popen,
    params: dict,
    width: int,
    height: int,
    warmup: int,
    full_w: int = 0,
    full_h: int = 0,
    stop: threading.Event | None = None,
    shm: SharedFrameBuffer | None = None,
) -> tuple[subprocess.Popen, list[str], WorkerReader, threading.Event]:
    """Restart the worker at a new resolution.

    2-second pause between shutdown and start to let the old worker release
    GPU resources (NGX D3D12 device, ~165 MB + nvngx_dlssnr.dll).
    """
    shutdown_worker(worker, stop)
    time.sleep(2.0)
    return start_worker(params, width, height, warmup, full_w, full_h, shm)


# ---------------------------------------------------------------------------
# Worker shutdown
# ---------------------------------------------------------------------------

def shutdown_worker(
    worker: subprocess.Popen,
    stop: threading.Event | None = None,
) -> None:
    """Graceful shutdown: close stdin (EOF -> worker exits), wait 10s.

    On timeout, terminate then kill.
    """
    if worker.poll() is not None:
        if stop is not None:
            stop.set()
        return
    if stop is not None:
        stop.set()
    try:
        if worker.stdin and not worker.stdin.closed:
            worker.stdin.close()
    except OSError:
        pass
    try:
        code = worker.wait(timeout=10)
        print(f"[main] worker exited cleanly (code {code})")
    except subprocess.TimeoutExpired:
        print("[main] worker did not exit within 10 s - forcing termination")
        worker.terminate()
        try:
            worker.wait(timeout=5)
        except subprocess.TimeoutExpired:
            worker.kill()


# ---------------------------------------------------------------------------
# Pipeline teardown and rebuild
# ---------------------------------------------------------------------------

def teardown_pipeline(st) -> None:
    """Stop everything sized to the current width/height.

    Worker, shared memory, and running recording — all built for one
    frame size and cannot survive a change.
    """
    if st.recorder is not None:
        try:
            st.recorder.close()
        except Exception as exc:
            print(f"[main] failed to close recording: {exc}", file=sys.stderr)
        st.recorder = None
    st.pending_shot = None
    shutdown_worker(st.worker, st.worker_stop)
    try:
        st.shm.close()
    except Exception:
        pass


def rebuild_pipeline(st, note: str) -> None:
    """Build the worker, shm, and overlay for the current size.

    Reads st.width/height/work_w/work_h and rebuilds everything that
    depends on them, resetting per-worker flags.
    """
    st.display.enter_switch_mode(st.output_rgba, *st.capture.resolution)
    menu_was_open = st.display.menu.visible
    full_w = st.width if (st.work_w != st.width or st.work_h != st.height) else 0
    full_h = st.height if (st.work_w != st.width or st.work_h != st.height) else 0
    st.shm = SharedFrameBuffer(st.width, st.height)
    st.worker, st.worker_logs, st.reader, st.worker_stop = start_worker(
        st.params, st.work_w, st.work_h, st.warmup, full_w, full_h, st.shm,
    )
    # Soft resize
    recreated = False
    try:
        st.display.resize(st.width, st.height)
    except Exception as exc:
        print(f"[main] soft resize failed ({exc}) - recreating window")
        st.cfg["menu_offset"] = [int(st.display.menu.offset[0]),
                                 int(st.display.menu.offset[1])]
        st.cfg["menu_scale"] = round(st.display.menu.user_scale, 2)
        st.cfg["menu_height"] = (None if st.display.menu.user_height is None
                                 else int(st.display.menu.user_height))
        try:
            st.display.close()
        except Exception:
            pass
        st.display = Display(st.width, st.height,
                             fullscreen=bool(st.cfg["fullscreen"]))
        recreated = True
    st.display.set_excluded_from_capture(st.window_hwnd is None)
    st.display.set_lang(st.lang)
    st.display.menu.set_hotkeys(hotkey_labels(st.hotkey_bindings))
    saved_theme = st.cfg.get("theme")
    if isinstance(saved_theme, str) and saved_theme in ("light", "dark"):
        st.display.menu.set_state({"theme": saved_theme})
    st.display.menu.set_state({"lang": st.lang})
    if recreated:
        st.display.menu.set_user_scale(float(st.cfg.get("menu_scale", 1.0)))
        saved_offset = st.cfg.get("menu_offset")
        if isinstance(saved_offset, (list, tuple)) and len(saved_offset) == 2:
            st.display.menu.offset = [int(saved_offset[0]),
                                      int(saved_offset[1])]
        saved_height = st.cfg.get("menu_height")
        if isinstance(saved_height, (int, float)) and saved_height > 0:
            st.display.menu.user_height = int(saved_height)
    if menu_was_open:
        st.display.menu.set_state(settings_io.menu_payload(st))
        st.display.menu.visible = True
        st.display.set_menu_opaque(True)
        st.display.set_menu_input(True)
        if st.window_hwnd is not None:
            st.display.set_fullscreen_layer(st.mon_w, st.mon_h)

    # Guides and buffers follow the new resolution
    import numpy as np
    from guides import TemporalGuideGenerator
    st.guides = TemporalGuideGenerator(st.work_w, st.work_h,
                                       emit_small=st.motion_small)
    st.buf_full = np.empty((st.height, st.width, 4), dtype=np.uint8)
    # Pipeline flags - the new worker knows nothing
    st.present_mode = False
    st.present_attempted = False
    st.dda_mode = False
    st.dda_attempted = False
    st.gray_active = False
    st.motion_small = False
    st.motion_attempted = False
    st.out_shm = False
    st.out_attempted = False
    st.gpu_ok = None
    st.frame_index = 0
    st.pts = 0
    st.work_frame = None
    st.output_rgba = None
    settings_io.save_menu_layout(st)
    print(f"[main] pipeline rebuilt: {st.width}x{st.height}, "
          f"work {st.work_w}x{st.work_h} - {note}")
    st.display.alert(note, duration=6.0)


def switch_monitor(st, new_monitor: int | str) -> None:
    """Switch capture/output monitor - a full pipeline restart."""
    if isinstance(new_monitor, str):
        from capture_linux import list_monitors
        # Try to resolve by devicename; fall back to index 0
        resolved = None
        for idx, name in list_monitors():
            if name == new_monitor:
                resolved = idx
                break
        if resolved is None:
            print(f"[main] monitor {new_monitor!r} is not connected",
                  file=sys.stderr)
            return
        new_monitor = resolved
    if new_monitor == st.monitor:
        return
    print(f"[main] monitor change: {st.monitor} -> {new_monitor}")
    teardown_pipeline(st)
    try:
        st.capture.close()
    except Exception:
        pass
    st.monitor = new_monitor
    st.cfg["monitor"] = st.monitor
    from capture_linux import ScreenCapture
    try:
        st.capture = ScreenCapture(monitor_idx=st.monitor)
    except Exception as exc:
        print(f"[main] monitor {st.monitor} failed to open: {exc}",
              file=sys.stderr)
        st.capture = ScreenCapture(monitor_idx=0)
        st.monitor = st.capture.monitor_idx if hasattr(st.capture, 'monitor_idx') else 0
        st.cfg["monitor"] = st.monitor
        st.display.alert(UI_STRINGS[st.lang]["mon_fail"])
    st.width, st.height = st.capture.resolution
    st.work_w, st.work_h = _work_size(st.width, st.height, st.work_scale)
    rebuild_pipeline(st, f"Monitor {st.monitor}: {st.width}x{st.height}")


def switch_window(st, hwnd: int) -> None:
    """Point capture at one window (hwnd) or back at the desktop (0)."""
    import channels
    from i18n import STRINGS as UI_STRINGS
    from settings_io import _work_size
    from protocol import send_dda

    if hwnd and not st.want_dda:
        st.display.alert(UI_STRINGS[st.lang]["win_fail"])
        print("[main] window mode needs capture in the worker "
              "(capture_in_worker is off)", file=sys.stderr)
        return
    st.display.enter_switch_mode(st.output_rgba, *st.capture.resolution)
    if hwnd:
        # Under Linux there is no IsIconic — assume visible
        try:
            aw, ah = channels.probe_window_capture(st, hwnd)
        except Exception as exc:
            try:
                send_dda(st.worker, st.width, st.height)
            except Exception:
                pass
            st.display.alert(UI_STRINGS[st.lang]["win_fail"])
            print(f"[main] the worker cannot capture that window: {exc}",
                  file=sys.stderr)
            st.display.exit_switch_mode()
            return
        if aw < 64 or ah < 64:
            send_dda(st.worker, st.width, st.height)
            print(f"[main] the window is {aw}x{ah} - too small to process",
                  file=sys.stderr)
            st.display.alert(UI_STRINGS[st.lang]["win_fail"])
            st.display.exit_switch_mode()
            return
        teardown_pipeline(st)
        st.window_hwnd = int(hwnd)
        st.width, st.height = int(aw), int(ah)
        note = UI_STRINGS[st.lang]["win_mode_on"]
    else:
        teardown_pipeline(st)
        st.window_hwnd = None
        st.width, st.height = st.capture.resolution
        note = UI_STRINGS[st.lang]["win_mode_off"]
    st.work_w, st.work_h = _work_size(st.width, st.height, st.work_scale)
    st.follow_pos = None
    st.follow_resize = None
    from platform_linux import window_frame_rect
    rect = window_frame_rect(hwnd) if hwnd else None
    st.follow_size = rect[2:] if rect else None
    rebuild_pipeline(st, note)


def apply_spout(st, enabled: bool) -> None:
    """Toggle Spout2 bridge (restarts worker)."""
    st.cfg["spout"] = bool(enabled)
    os.environ["NS_SPOUT"] = "1" if enabled else "0"
    settings_io.save_menu_layout(st)
    print(f"[main] Spout2 output: {'on' if enabled else 'off'} - restarting")
    teardown_pipeline(st)
    rebuild_pipeline(st, "Spout2" + (" ON" if enabled else " OFF"))


# Late imports used by functions above — avoid circular deps at module level.
# These modules are imported here (lazily within functions) because they
# import pipeline_linux themselves through the state object chain.
from settings_io import _work_size, hotkey_labels, settings_io  # noqa: E402, F811