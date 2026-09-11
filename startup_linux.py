"""Startup for Linux — get from a config file to a running pipeline.

Replaces Windows startup.py: no DPI awareness, no WASAPI, no nvapi64,
no Win32 registry probes. GPU detection uses nvidia-smi via gpuinfo_linux.

Two halves, same order as the original:
  configure()  — read the config and decide what to do
  bring_up()   — make it exist: worker, overlay, hotkeys, guides
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading

import numpy as np

from capture_linux import ScreenCapture, list_monitors
from display_linux import Display
from gpuinfo_linux import describe as gpu_describe, probe as gpu_probe
from guides import TemporalGuideGenerator
from hotkeys_linux import (register_global_hotkey, unregister_all,
                           poll_x11_events)
from i18n import STRINGS as UI_STRINGS
from paths import BASE_DIR
from pipeline_linux import start_worker
from protocol import SharedFrameBuffer, WorkerReader
from recorder import VideoRecorder
from settings_io import (APP_VERSION, _work_size, hotkey_labels, load_config,
                         load_presets, resolve_params)


# --- Log to a file instead of the console ----------------------------------
# Under Linux we run from a terminal — print works.  If launched without a
# terminal (e.g. via systemd or a desktop launcher), we still redirect to
# a log file.
LOG_PATH = BASE_DIR / "NeuralScreen.log"


def _init_logging() -> None:
    """Redirect stdout/stderr into NeuralScreen.log (utf-8)."""
    try:
        log_file = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
        sys.stdout = log_file
        sys.stderr = log_file
    except Exception:
        pass


def _log_environment(cfg: dict) -> None:
    """Print the environment header: version, OS, GPU."""
    import platform
    print(f"[env] NeuralScreen {APP_VERSION} | "
          f"{platform.system()} {platform.release()} | "
          f"{platform.platform()}")
    try:
        g = gpu_probe()
        print(f"[env] GPU: {gpu_describe(g)}")
    except Exception:
        pass
    print(f"[env] lang: {cfg.get('lang', 'en')} | "
          f"profile: {cfg.get('profile', '?')} | "
          f"work_scale: {cfg.get('work_scale', '?')}")


def _apply_nr_dll(cfg: dict) -> None:
    """The swappable runtime — NS_NR_DLL in the environment."""
    if cfg.get("nr_dll"):
        os.environ["NS_NR_DLL"] = str(cfg["nr_dll"])


def _apply_spout_env(cfg: dict) -> None:
    """Spout2 bridge flag — NS_SPOUT in the environment."""
    os.environ["NS_SPOUT"] = "1" if cfg.get("spout") else "0"


def _apply_gpu_env(cfg: dict) -> None:
    """Which GPU index the worker runs on — NS_GPU in the environment."""
    gpu = cfg.get("gpu")
    if gpu is None:
        os.environ.pop("NS_GPU", None)
    else:
        os.environ["NS_GPU"] = str(int(gpu))


def configure(st) -> None:
    """Read the config and decide what the program is going to do.

    Sets the config, NR parameters, presets, monitor, and resolution.
    Creates the capture object to get the real monitor resolution.
    """
    st.cfg = load_config(st.cfg_path)
    st.params = resolve_params(st.cfg)
    st.presets = load_presets(st.cfg)
    _apply_nr_dll(st.cfg)
    _log_environment(st.cfg)

    st.width, st.height = int(st.cfg["width"]), int(st.cfg["height"])
    monitor_cfg = st.cfg["monitor"]
    if isinstance(monitor_cfg, str):
        # Resolve devicename to index
        resolved = None
        for idx, name in list_monitors():
            if name == monitor_cfg:
                resolved = idx
                break
        if resolved is None:
            print(f"[main] monitor {monitor_cfg!r} not connected - using 0",
                  file=sys.stderr)
            resolved = 0
        st.monitor = resolved
    else:
        st.monitor = int(monitor_cfg)

    st.warmup = int(st.cfg["warmup"])
    st.work_scale = float(st.cfg["work_scale"])
    st.nr_small = bool(st.cfg.get("nr_small", False))
    os.environ["NS_NR_SMALL"] = "1" if st.nr_small else "0"
    _apply_spout_env(st.cfg)
    _apply_gpu_env(st.cfg)
    st.lang = str(st.cfg["lang"])

    # Real monitor resolution overrides config
    st.capture = ScreenCapture(monitor_idx=st.monitor)
    st.mon_w, st.mon_h = st.capture.resolution if hasattr(st.capture, 'resolution') else (0, 0)
    # If the capture doesn't expose resolution directly, try grabbing once
    if st.mon_w == 0 or st.mon_h == 0:
        try:
            frame = st.capture.grab()
            st.mon_h, st.mon_w = frame.shape[:2]
        except Exception:
            st.mon_w, st.mon_h = st.width, st.height
    if (st.mon_w > 0 and st.mon_h > 0
            and (st.mon_w, st.mon_h) != (st.width, st.height)):
        print(f"[main] monitor {st.monitor} is {st.mon_w}x{st.mon_h} "
              f"(config: {st.width}x{st.height}), taking the real resolution")
        st.width, st.height = st.mon_w, st.mon_h

    print(f"[main] NeuralScreen - profile {st.cfg['profile']!r}, "
          f"resolution {st.width}x{st.height}, monitor {st.monitor}")
    print(f"[main] NGX params: {st.params}")
    print(f"[main] work_scale {st.work_scale:.2f} (NGX "
          f"{int(st.width * st.work_scale)}x{int(st.height * st.work_scale)})")

    # Null-initialise the runtime handles
    st.worker: subprocess.Popen | None = None
    st.reader: WorkerReader | None = None
    st.worker_stop: threading.Event | None = None
    st.shm: SharedFrameBuffer | None = None
    st.display: Display | None = None
    st.hotkeys: list[tuple] | None = None
    st.recorder: VideoRecorder | None = None


def bring_up(st) -> None:
    """Make it exist: worker, overlay, hotkeys, guides, state defaults.

    Runs inside main's try/finally — everything created here is torn down
    there. No tray icon, no taskbar window on Linux.
    """
    import importlib

    st.work_w, st.work_h = _work_size(st.width, st.height, st.work_scale)
    full_w = st.width if (st.work_w != st.width or st.work_h != st.height) else 0
    full_h = st.height if (st.work_w != st.width or st.work_h != st.height) else 0

    # Shared memory for input frame
    st.shm = SharedFrameBuffer(st.width, st.height)

    # GPU detection
    gpu_info = gpu_probe()
    st.gpu_text = gpu_describe(gpu_info)
    st.gpu_ok: bool | None = None
    print(f"[main] GPU: {st.gpu_text or 'unknown'}")

    effective_warmup = st.warmup
    # No arch_group on Linux — skip Blackwell detection; keep warmup as-is
    st.worker, st.worker_logs, st.reader, st.worker_stop = start_worker(
        st.params, st.work_w, st.work_h, effective_warmup, full_w, full_h,
        st.shm,
    )
    print(f"[main] worker started (pid {st.worker.pid}), header sent "
          f"({st.work_w}x{st.work_h})")
    print(f"[main] capturing monitor {st.monitor}")

    # Display overlay
    st.display = Display(st.width, st.height,
                         fullscreen=bool(st.cfg["fullscreen"]))
    st.display.set_lang(st.lang)
    st.startup_menu = bool(st.cfg.get("open_menu_on_start", True))
    st.split_pos = min(1.0, max(0.0, float(st.cfg.get("split", 0.0))))

    # Menu state from config
    st.display.menu.set_user_scale(float(st.cfg.get("menu_scale", 1.0)))
    saved_theme = st.cfg.get("theme")
    if isinstance(saved_theme, str) and saved_theme in ("light", "dark"):
        st.display.menu.set_state({"theme": saved_theme})
    saved_offset = st.cfg.get("menu_offset")
    if isinstance(saved_offset, (list, tuple)) and len(saved_offset) == 2:
        st.display.menu.offset = [int(saved_offset[0]),
                                  int(saved_offset[1])]
    saved_height = st.cfg.get("menu_height")
    if isinstance(saved_height, (int, float)) and saved_height > 0:
        st.display.menu.user_height = int(saved_height)
    print(f"[main] output window {st.display.width}x{st.display.height}")

    # Command queue (replaces tray_commands)
    st.tray_commands = queue.Queue()
    st.shot_paths = queue.Queue()
    st.shot_dialog_open = False

    # Global hotkeys via X11 (XGrabKey) — directly fired into the queue
    from hotkeys_linux import register_global_hotkey, unregister_all
    hotkey_overrides = st.cfg.get("hotkeys")
    if not isinstance(hotkey_overrides, dict):
        hotkey_overrides = {}

    # Build bindings using the cross-platform hotkeys module
    from hotkeys import build_bindings, describe as describe_hotkeys
    from commands import COMMAND_MAP  # noqa: F401 — ensures commands are importable
    st.hotkey_bindings = build_bindings(hotkey_overrides)
    st.hotkeys = []  # track registered combos

    def _make_callback(cmd: str):
        """Wrap a command string so the hotkey pushes it into the queue."""
        def _cb(_name):
            st.tray_commands.put(cmd)
        return _cb

    for cmd, combo in st.hotkey_bindings.items():
        try:
            register_global_hotkey(combo, _make_callback(cmd))
            st.hotkeys.append(combo)
        except (ValueError, RuntimeError) as exc:
            print(f"[main] hotkey {combo} failed: {exc}", file=sys.stderr)

    if st.hotkeys:
        print(f"[main] hotkeys registered: {', '.join(st.hotkeys)} "
              f"({describe_hotkeys(st.hotkey_bindings)})")

    st.display.menu.set_hotkeys(hotkey_labels(st.hotkey_bindings))

    # Guides
    st.guides = TemporalGuideGenerator(st.work_w, st.work_h)
    st.buf_full = np.empty((st.height, st.width, 4), dtype=np.uint8)

    # State defaults
    st.paused = False
    st.worker_failed = False
    st.frame_index = 0
    st.pts = 0
    st.output_rgba = None
    st.want_present = bool(st.cfg.get("worker_present", True))
    st.want_motion_small = bool(st.cfg.get("motion_on_gpu", True))
    st.want_dda = bool(st.cfg.get("capture_in_worker", True))
    st.want_out_shm = bool(st.cfg.get("pixels_in_shm", True))
    st.record_audio = bool(st.cfg.get("record_audio", True))  # stub on Linux
    st.out_shm = False
    st.out_attempted = False
    st.motion_small = False
    st.motion_attempted = False
    st.present_mode = False
    st.present_attempted = False
    st.dda_mode = False
    st.dda_attempted = False
    st.window_hwnd = None
    st.last_foreground = 0
    st.follow_pos = None
    st.follow_resize = None
    st.mon_w, st.mon_h = st.width, st.height
    st.gray_active = False
    st.pending_shot = None
    st.recorder = None
    st.work_frame = None
    st.running = True
    st.last_restart = 0.0
    st.pending_apply = None
    st.next_auto_revive = 0.0
    st.consecutive_restarts = 0
    st.guide_fails = 0