"""DLSS 5 Desktop NR — Linux main entry point.

The loop: desktop capture (capture_linux.ScreenCapture) -> motion guides
(guides.TemporalGuideGenerator) -> the NGX worker under Wine -> fullscreen
output (display_linux.Display).

Controls (global hotkeys via XGrabKey + polling):
    Num1          - NR on/off
    Num2          - the settings menu
    Num3          - screenshot
    Num0          - recording
    Num4 / Num6   - processing resolution down / up
    Num5          - process one window instead of the whole screen
    Ctrl+Alt+Q    - quit

Run:
    python3 main_linux.py [--config config.json]
"""

from __future__ import annotations

import argparse
import json
import mmap
import os
import queue
import struct
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path


# Add the script directory to sys.path so local modules work
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
import numpy as np
import pygame  # HUD overlay and menu

from capture_linux import ScreenCapture, list_monitors
from display_linux import Display
from guides import TemporalGuideGenerator
from hotkeys_linux import register_global_hotkey, unregister_all, poll_x11_events
from recorder import VideoRecorder
from gpuinfo_linux import describe as gpu_describe, probe as gpu_probe
from i18n import STRINGS as UI_STRINGS

from platform_linux import (list_capturable_windows, window_frame_rect,
                            window_under_cursor, foreign_foreground,
                            monitor_size)

import channels
import commands
import startup_linux
import settings_io
import pipeline_linux
from pipeline_linux import (AUTO_REVIVE_BACKOFF, MAX_CONSECUTIVE_RESTARTS,
                            RESTART_COOLDOWN)
from paths import BASE_DIR, NATIVE_DIR, WORKER_EXE
from protocol import (SharedFrameBuffer, _negotiate_shm, send_dda,
                      send_frame, WorkerReader)
from pipeline_linux import (_drain_stderr, restart_worker, shutdown_worker,
                            start_worker, teardown_pipeline, rebuild_pipeline,
                            switch_monitor, switch_window)
from startup_linux import (LOG_PATH, _init_logging, _log_environment)
from settings_io import (DEFAULT_LANG, PRESET_KEYS, SKIN_MIN, load_config,
                         load_presets, resolve_params, _work_size,
                         hotkey_labels)

# Re-export constants for tests that look them up in main
from settings_io import (CHANNEL_URL, PRESET_NAME_PREFIX, REPO_URL,
                         WORK_SCALE_MAX, WORK_SCALE_STEP, APP_VERSION,
                         CHANNEL_LABEL, PROFILES, WORK_MAX_W, WORK_MAX_H,
                         WORK_SCALE_MIN)
from protocol import (DDA_ACK_FMT, DDA_ACK_MAGIC, DDA_FMT, DDA_MAGIC,
                      FRAME_FLAG_BYPASS, FRAME_FLAG_MOTION_SMALL,
                      FRAME_FLAG_NO_COLOR, FRAME_FLAG_SHM, FRAME_FLAG_SPLIT,
                      FRAME_FLAG_WANT_PIXELS, FRAME_FMT, FRAME_MAGIC,
                      GRAY_ACK_FMT, GRAY_ACK_MAGIC, GRAY_FMT, GRAY_MAGIC,
                      HEADER_FMT, MOTION_ACK_FMT, MOTION_ACK_MAGIC,
                      MOTION_FMT, MOTION_MAGIC, OUTS_ACK_FMT, OUTS_ACK_MAGIC,
                      OUTS_FMT, OUTS_MAGIC, OUT_BYTES_IN_SHM, OUT_FMT,
                      OUT_MAGIC, RACK_FMT, RESIZE_ACK_MAGIC,
                      RESIZE_FLAG_NR_SMALL, RESIZE_FMT, RESIZE_MAGIC,
                      SHM_ACK_FMT, SHM_ACK_MAGIC, SHM_FMT, SHM_MAGIC,
                      VIDEO_MAGIC, WGC_ACK_FMT, WGC_ACK_MAGIC, WGC_FMT,
                      WGC_MAGIC, WINDOW_ACK_FMT, WINDOW_ACK_MAGIC,
                      WINDOW_FLAG_CAPTURABLE, WINDOW_FLAG_DISABLE,
                      WINDOW_FMT, WINDOW_MAGIC, WorkerReader, _read_exact)


FPS_LOG_INTERVAL = 2.0
PERF_LOG_INTERVAL = 5.0
PERF_KEYS = ("grab", "resize_full", "guides", "send", "recv", "show")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_worker(worker: subprocess.Popen, logs: list[str]) -> None:
    """If the worker died, print last stderr lines and raise."""
    code = worker.poll()
    if code is not None:
        tail = "\n".join(logs[-40:]) or "(stderr empty)"
        raise RuntimeError(
            f"the NGX worker exited with code {code}.\n"
            f"last stderr lines:\n{tail}"
        )


def _hard_failure(logs: list[str]) -> bool:
    """Whether the worker's tail shows 0xBAD00001 (permanent failure)."""
    return any("0xBAD00001" in line for line in logs[-40:])


# ---------------------------------------------------------------------------
# Pipeline state container
# ---------------------------------------------------------------------------

class _Pipeline:
    """Everything main() rebinds while the program runs.

    One object instead of ~50 closure variables.
    """

    __slots__ = (
        "buf_full", "capture", "cfg", "consecutive_restarts",
        "dda_attempted", "dda_mode", "display", "follow_pos",
        "follow_resize", "follow_size", "mon_resize", "frame_index",
        "gpu_ok", "gray_active", "guide_fails", "guides", "height",
        "hotkey_bindings", "hotkeys", "lang", "last_foreground",
        "last_restart", "mon_h", "mon_w", "monitor", "motion_attempted",
        "motion_small", "next_auto_revive", "nr_small", "out_attempted",
        "out_shm", "output_rgba", "params", "paused", "pending_apply",
        "pending_shot", "perf", "present_attempted", "present_mode",
        "presets", "pts", "reader", "record_audio", "recorder", "running",
        "shm", "shot_dialog_open", "shot_paths", "split_pos", "startup_menu",
        "tray_commands", "width", "window_hwnd", "work_frame", "work_h",
        "work_scale", "work_w", "worker", "worker_failed", "worker_logs",
        "worker_stop", "want_dda", "want_motion_small", "want_out_shm",
        "want_present", "cfg_path", "gpu_text", "warmup",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    st = _Pipeline()
    parser = argparse.ArgumentParser(
        description="DLSS 5 Desktop NR — Linux prototype")
    parser.add_argument("--config", type=Path,
                        default=BASE_DIR / "config.json",
                        help="path to config.json")
    args = parser.parse_args()
    _init_logging()

    # Single-instance check via PID file (simple, no Win32 mutex)
    pid_path = Path("/tmp/neuralscreen.pid")
    if pid_path.exists():
        try:
            old_pid = int(pid_path.read_text().strip())
            # Check if the process is still alive
            os.kill(old_pid, 0)
            print("[main] another NeuralScreen is running - this copy exits",
                  file=sys.stderr)
            return 1
        except (OSError, ValueError):
            # Stale PID file — remove it
            try:
                pid_path.unlink()
            except Exception:
                pass
    try:
        pid_path.write_text(str(os.getpid()))
    except Exception:
        pass

    st.cfg_path = args.config
    startup_linux.configure(st)
    try:
        startup_linux.bring_up(st)

        # ------------------------------------------------------------------
        # Nested helpers (closures over st)
        # ------------------------------------------------------------------

        def _recreate_capture() -> None:
            """Recreate the capture after a failure."""
            try:
                st.capture.close()
            except Exception:
                pass
            st.capture = ScreenCapture(monitor_idx=st.monitor)

        def _safe_grab() -> np.ndarray | None:
            """grab() that recreates the capture on failure."""
            try:
                return st.capture.grab()
            except Exception as exc:
                print(f"[main] capture failed ({exc}) - recreating")
                try:
                    _recreate_capture()
                except Exception as exc2:
                    print(f"[main] recreating capture failed: {exc2}",
                          file=sys.stderr)
                return None

        # ------------------------------------------------------------------
        # Loop-local state
        # ------------------------------------------------------------------
        guide = None
        startup_pending = True
        fps_window: list[float] = []
        last_log = time.monotonic()
        last_fps = 0.0
        last_perf_log = time.monotonic()
        st.perf = {k: [] for k in PERF_KEYS}

        def _perf(key: str, t0: float) -> None:
            st.perf[key].append((time.perf_counter() - t0) * 1000.0)

        # ------------------------------------------------------------------
        # Main loop
        # ------------------------------------------------------------------
        while st.running:
            loop_start = time.perf_counter()
            now = time.monotonic()

            # Poll X11 events for global hotkeys
            try:
                poll_x11_events(block=False)
            except Exception:
                pass

            if not commands.drain_commands(st):
                break

            # Worker dead — check auto-revive
            if st.worker_failed:
                if (st.next_auto_revive
                        and time.monotonic() >= st.next_auto_revive):
                    st.next_auto_revive = 0.0
                    st.worker_failed = False
                    print("[main] auto-reviving the worker")
                    try:
                        st.worker, st.worker_logs, st.reader, st.worker_stop = restart_worker(
                            st.worker, st.params, st.work_w, st.work_h,
                            st.warmup,
                            st.width if (st.work_w != st.width
                                         or st.work_h != st.height) else 0,
                            st.height if (st.work_w != st.width
                                          or st.work_h != st.height) else 0,
                            st.worker_stop, st.shm)
                        channels.forget_present(st)
                        channels.forget_dda(st)
                        channels.forget_out(st)
                        channels.sync_motion_size(st)
                        st.frame_index = 0
                        st.pts = 0
                        st.paused = False
                        st.display.set_visible(True)
                        st.display.alert(UI_STRINGS[st.lang]["nr_on"])
                    except Exception as exc:
                        print(f"[main] auto-revive failed ({exc}) - staying OFF",
                              file=sys.stderr)
                        st.worker_failed = True
                time.sleep(0.05)
                continue

            # Deferred apply
            if (st.pending_apply is not None
                    and time.monotonic() - st.last_restart >= RESTART_COOLDOWN):
                p_scale, p_profile, p_params, p_small = st.pending_apply
                st.pending_apply = None
                print("[main] applying deferred settings")
                pipeline_linux.do_restart(st, p_scale, p_profile, p_params,
                                          new_small=p_small)

            if not st.running:
                break

            bypass = st.paused
            commands.drain_save_dialog(st)

            # Channel negotiation
            if st.want_present and not st.present_mode and not st.present_attempted:
                channels.enable_present(st)
            # Track foreground (for window mode)
            fg = foreign_foreground()
            if fg:
                st.last_foreground = fg
            # Re-assert overlay on top every 30 frames
            if st.display.menu.visible and st.frame_index % 30 == 0:
                st.display.reveal()
            if st.frame_index % 30 == 0:
                st.display.reveal()
            # Window tracking
            if st.window_hwnd is not None:
                pipeline_linux.follow_window(st)
            elif st.frame_index % 30 == 0:
                pipeline_linux.follow_monitor(st)

            if st.want_dda and not st.dda_mode and not st.dda_attempted:
                if st.window_hwnd is not None:
                    if not channels.enable_wgc(st):
                        switch_window(st, 0)
                else:
                    channels.enable_dda(st)
            if (st.want_motion_small and not st.motion_small
                    and not st.motion_attempted):
                st.motion_attempted = True
                channels.sync_motion_size(st)
            if st.want_out_shm and not st.out_shm and not st.out_attempted:
                channels.enable_out_shm(st)

            # --- Input for overlay menu ---
            if st.display.menu.visible:
                for ev in pygame.event.get():
                    for action in st.display.menu.handle_event(ev):
                        commands.apply_menu_action(st, action)
                if not st.display.menu.dragging:
                    st.display.menu.set_state(
                        settings_io.menu_payload(st))

            # --- Grab ahead ---
            if st.work_frame is None and not st.gray_active:
                t0 = time.perf_counter()
                frame = _safe_grab()
                _perf("grab", t0)
                if frame is None:
                    continue
                if (frame.shape[1] != st.width
                        or frame.shape[0] != st.height):
                    t0 = time.perf_counter()
                    try:
                        cv2.resize(frame, (st.width, st.height),
                                   interpolation=cv2.INTER_LANCZOS4,
                                   dst=st.buf_full)
                    except cv2.error:
                        st.buf_full = np.empty(
                            (st.height, st.width, 4), dtype=np.uint8)
                        cv2.resize(frame, (st.width, st.height),
                                   interpolation=cv2.INTER_LANCZOS4,
                                   dst=st.buf_full)
                    _perf("resize_full", t0)
                    frame = st.buf_full
                else:
                    frame = np.ascontiguousarray(frame, dtype=np.uint8)
                st.work_frame = frame

            # --- Guides ---
            try:
                t0 = time.perf_counter()
                if st.gray_active:
                    guide = st.guides.process(gray=st.shm.read_gray())
                else:
                    guide = st.guides.process(st.work_frame)
                _perf("guides", t0)
            except Exception as guide_exc:
                print(f"[main] guides.process failed ({guide_exc})",
                      file=sys.stderr)
                st.guide_fails += 1
                if st.guide_fails >= 5:
                    print("[main] guides unstable - zero motion",
                          file=sys.stderr)
                    st.guide_fails = 0
                    guide = st.guides.zero_guide()
                else:
                    continue

            # --- Send to worker ---
            try:
                check_worker(st.worker, st.worker_logs)
                t0 = time.perf_counter()
                send_frame(
                    st.worker, st.frame_index, st.work_frame,
                    guide.motion, guide.reset, st.pts, st.shm,
                    want_pixels=(st.pending_shot is not None
                                 or (st.recorder is not None
                                     and st.recorder.needs_frame())),
                    motion_small=st.motion_small,
                    no_color=bool(st.dda_mode),
                    bypass=bypass,
                    split=st.split_pos,
                )
                _perf("send", t0)
            except (BrokenPipeError, OSError, EOFError,
                    RuntimeError) as exc:
                st.consecutive_restarts += 1
                if st.consecutive_restarts >= MAX_CONSECUTIVE_RESTARTS:
                    print(f"[main] worker died "
                          f"{st.consecutive_restarts}x - NR OFF")
                    st.paused = True
                    st.worker_failed = True
                    st.display.alert(UI_STRINGS[st.lang]["nr_off"])
                    st.consecutive_restarts = 0
                    st.work_frame = None
                    if not _hard_failure(st.worker_logs):
                        st.next_auto_revive = (time.monotonic()
                                               + AUTO_REVIVE_BACKOFF)
                        print(f"[main] transient failure - auto-revive "
                              f"in {AUTO_REVIVE_BACKOFF:.0f}s")
                    try:
                        shutdown_worker(st.worker, st.worker_stop)
                    except Exception:
                        pass
                    st.display.set_visible(False)
                    continue
                print(f"[main] worker died ({exc}) - restarting "
                      f"({st.consecutive_restarts}/"
                      f"{MAX_CONSECUTIVE_RESTARTS})")
                if st.worker_logs:
                    print("[main] worker stderr (tail):")
                    for line in st.worker_logs[-15:]:
                        print(f"  {line}")
                st.worker, st.worker_logs, st.reader, st.worker_stop = restart_worker(
                    st.worker, st.params, st.work_w, st.work_h, 10,
                    st.width if (st.work_w != st.width
                                 or st.work_h != st.height) else 0,
                    st.height if (st.work_w != st.width
                                  or st.work_h != st.height) else 0,
                    st.worker_stop, st.shm)
                channels.forget_present(st)
                channels.forget_dda(st)
                channels.forget_out(st)
                channels.sync_motion_size(st)
                st.frame_index = 0
                st.pts = 0
                st.work_frame = None
                continue

            # --- Grab next frame while worker computes ---
            next_frame = None
            if not st.gray_active:
                t0 = time.perf_counter()
                next_frame = _safe_grab()
                _perf("grab", t0)
            if next_frame is not None:
                if (next_frame.shape[1] != st.width
                        or next_frame.shape[0] != st.height):
                    t0 = time.perf_counter()
                    try:
                        cv2.resize(next_frame, (st.width, st.height),
                                   interpolation=cv2.INTER_LANCZOS4,
                                   dst=st.buf_full)
                    except cv2.error:
                        st.buf_full = np.empty(
                            (st.height, st.width, 4), dtype=np.uint8)
                        cv2.resize(next_frame, (st.width, st.height),
                                   interpolation=cv2.INTER_LANCZOS4,
                                   dst=st.buf_full)
                    _perf("resize_full", t0)
                    next_frame = st.buf_full
                else:
                    next_frame = np.ascontiguousarray(
                        next_frame, dtype=np.uint8)

            # --- Receive from worker ---
            t0 = time.perf_counter()
            try:
                st.output_rgba = None
                recv_reader = st.reader
                recv_deadline = time.monotonic() + 5.0
                while time.monotonic() < recv_deadline:
                    try:
                        st.output_rgba = st.reader.recv(
                            st.frame_index, timeout=0.05)
                        break
                    except TimeoutError:
                        if st.display.is_switch_active():
                            st.display.draw_overlay(0.0)
                        if not commands.drain_commands(st):
                            st.running = False
                            break
                        if st.reader is not recv_reader:
                            break
                        continue
                else:
                    raise TimeoutError(
                        f"worker silent for 5s on frame "
                        f"{st.frame_index}")
                if not st.running:
                    break
                if st.reader is not recv_reader:
                    continue
            except (TimeoutError, EOFError, RuntimeError,
                    OSError) as exc:
                st.consecutive_restarts += 1
                if st.consecutive_restarts >= MAX_CONSECUTIVE_RESTARTS:
                    print(f"[main] worker dead "
                          f"{st.consecutive_restarts}x - NR OFF")
                    st.paused = True
                    st.worker_failed = True
                    st.display.alert(UI_STRINGS[st.lang]["nr_off"])
                    st.consecutive_restarts = 0
                    st.work_frame = None
                    st.display.exit_switch_mode()
                    if not _hard_failure(st.worker_logs):
                        st.next_auto_revive = (time.monotonic()
                                               + AUTO_REVIVE_BACKOFF)
                        print(f"[main] transient failure - auto-revive "
                              f"in {AUTO_REVIVE_BACKOFF:.0f}s")
                    try:
                        shutdown_worker(st.worker, st.worker_stop)
                    except Exception:
                        pass
                    st.display.set_visible(False)
                    continue
                print(f"[main] worker dead frame {st.frame_index} "
                      f"({exc}) - restarting")
                st.worker, st.worker_logs, st.reader, st.worker_stop = restart_worker(
                    st.worker, st.params, st.work_w, st.work_h, 10,
                    st.width if (st.work_w != st.width
                                 or st.work_h != st.height) else 0,
                    st.height if (st.work_w != st.width
                                  or st.work_h != st.height) else 0,
                    st.worker_stop, st.shm)
                channels.forget_present(st)
                channels.forget_dda(st)
                channels.forget_out(st)
                channels.sync_motion_size(st)
                st.frame_index = 0
                st.pts = 0
                st.work_frame = None
                continue
            _perf("recv", t0)

            # A frame arrived — break the failure chain
            st.consecutive_restarts = 0
            status = "NR OFF" if st.paused else "NR ON"
            st.pts += 1

            # --- Display ---
            t0 = time.perf_counter()
            try:
                if (st.recorder is not None
                        and st.output_rgba is not None):
                    try:
                        surf = pygame.image.frombuffer(
                            st.output_rgba,
                            (st.output_rgba.shape[1],
                             st.output_rgba.shape[0]),
                            "RGBX")
                        st.display.draw_capture_overlay(surf)
                    except Exception as menu_exc:
                        print(f"[main] menu not baked into recording: "
                              f"{menu_exc}", file=sys.stderr)
                    try:
                        st.recorder.write(st.output_rgba)
                    except Exception as rec_exc:
                        print(f"[main] recording write failed "
                              f"({rec_exc}) - stopping",
                              file=sys.stderr)
                        try:
                            st.recorder.close()
                        except Exception:
                            pass
                        st.recorder = None

                if st.present_mode:
                    st.display.exit_switch_mode()
                    st.display.reveal()
                    if (st.pending_shot is not None
                            and st.output_rgba is not None):
                        commands.save_screenshot(
                            st, st.pending_shot, st.output_rgba)
                        st.pending_shot = None
                    st.display.draw_overlay()
                elif st.output_rgba is None:
                    st.display.exit_switch_mode()
                    st.display.reveal()
                    st.display.draw_overlay()
                else:
                    st.display.exit_switch_mode()
                    st.display.reveal()
                    st.display.show(st.output_rgba)
                    if st.pending_shot is not None:
                        commands.save_screenshot(
                            st, st.pending_shot, st.output_rgba)
                        st.pending_shot = None
            except Exception as exc:
                print(f"[main] output failed ({exc}) - recreating window")
                st.cfg["menu_offset"] = [
                    int(st.display.menu.offset[0]),
                    int(st.display.menu.offset[1])]
                st.cfg["menu_scale"] = round(
                    st.display.menu.user_scale, 2)
                st.cfg["menu_height"] = (
                    None if st.display.menu.user_height is None
                    else int(st.display.menu.user_height))
                try:
                    st.display.close()
                except Exception:
                    pass
                st.display = Display(
                    st.width, st.height,
                    fullscreen=bool(st.cfg["fullscreen"]))
                st.display.set_lang(st.lang)
                st.display.set_excluded_from_capture(
                    st.window_hwnd is None)
                st.display.menu.set_user_scale(
                    float(st.cfg.get("menu_scale", 1.0)))
                st.display.menu.set_hotkeys(
                    hotkey_labels(st.hotkey_bindings))
                saved_theme = st.cfg.get("theme")
                if (isinstance(saved_theme, str)
                        and saved_theme in ("light", "dark")):
                    st.display.menu.set_state(
                        {"theme": saved_theme})
                st.display.menu.set_state({"lang": st.lang})
                saved = st.cfg.get("menu_offset")
                if (isinstance(saved, (list, tuple))
                        and len(saved) == 2):
                    st.display.menu.offset = [
                        int(saved[0]), int(saved[1])]
                if st.present_mode:
                    st.display.set_hud_only(True)
                    st.display.reveal()
                st.display.alert(UI_STRINGS[st.lang]["nr_on"])
            _perf("show", t0)

            # --- HUD update ---
            st.display.set_hud({
                "fps": last_fps,
                "status": status,
                "resolution": f"{st.width}x{st.height}",
                "profile": st.cfg["profile"],
                "params": {
                    k: v for k, v in st.params.items()
                    if k not in ("profile", "preset", "style",
                                 "auto_mask", "ui_correction")
                },
                "frames": st.frame_index,
                "recording": st.recorder is not None,
                "rec_seconds": (st.recorder.duration_ms / 1000.0
                                if st.recorder else 0.0),
                "rec_indicator": bool(
                    st.cfg.get("rec_indicator", True)),
            })

            st.frame_index += 1
            if startup_pending and st.frame_index >= 2:
                startup_pending = False
                if st.startup_menu:
                    st.display.menu.set_state(
                        settings_io.menu_payload(st))
                    st.display.menu.visible = True
                    st.display.set_menu_opaque(True)
                    st.display.set_menu_input(True)
                    print("[main] menu opened at startup")
                else:
                    st.display.alert(UI_STRINGS[st.lang]["started"],
                                     3.5)

            st.work_frame = next_frame
            fps_window.append(time.perf_counter() - loop_start)
            if len(fps_window) > 120:
                fps_window.pop(0)

            # --- FPS log ---
            if now - last_log >= FPS_LOG_INTERVAL:
                last_fps = (len(fps_window) / sum(fps_window)
                            if fps_window else 0.0)
                scene = (f" | scene {guide.scene_score:.3f}"
                         if guide is not None else "")
                print(f"[main] {status} | FPS {last_fps:5.1f} | "
                      f"frames {st.frame_index} | "
                      f"work {st.work_w}x{st.work_h}{scene}")
                last_log = now

            if now - last_perf_log >= PERF_LOG_INTERVAL:
                parts = []
                for key in PERF_KEYS:
                    samples = st.perf[key]
                    if samples:
                        parts.append(
                            f"{key} {sum(samples)/len(samples):.1f}ms")
                    samples.clear()
                if parts:
                    print("[perf] " + " | ".join(parts))
                last_perf_log = now

        print("[main] exiting at the user's request")

    except KeyboardInterrupt:
        print("\n[main] interrupted (Ctrl+C)")
    except Exception as exc:
        print(f"[main] ERROR: {exc}", file=sys.stderr)
        if st.worker is not None and st.worker.poll() is not None:
            print("[main] worker crashed; last stderr:",
                  file=sys.stderr)
            for line in st.worker_logs[-40:]:
                print(f"  {line}", file=sys.stderr)
        return 1
    finally:
        if st.recorder is not None:
            try:
                st.recorder.close()
            except Exception as exc:
                print(f"[main] failed to close recording: {exc}",
                      file=sys.stderr)
        if st.worker is not None:
            shutdown_worker(st.worker, st.worker_stop)
        if st.shm is not None:
            st.shm.close()
        try:
            settings_io.save_menu_layout(st)
        except Exception:
            pass
        if st.capture is not None:
            try:
                st.capture.close()
            except Exception as exc:
                print(f"[main] failed to close capture: {exc}",
                      file=sys.stderr)
        if st.display is not None:
            try:
                st.display.close()
            except Exception as exc:
                print(f"[main] failed to close window: {exc}",
                      file=sys.stderr)
        try:
            unregister_all()
        except Exception:
            pass
        # Clean up PID file
        try:
            pid_path.unlink()
        except Exception:
            pass
        print("[main] resources released")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"\nNeuralScreen failed to start: {exc}", file=sys.stderr)
        sys.exit(1)