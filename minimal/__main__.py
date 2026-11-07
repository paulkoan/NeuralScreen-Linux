"""Entry point: python -m minimal [--frames N] [--monitor M] [--headless]

The MVP run: capture the screen, run every frame through the DLSS5 neural pass
in the Wine worker, show the result in a fullscreen SDL2 window.
"""

from __future__ import annotations

import argparse
import sys
import traceback

from minimal.capture import CaptureError, list_monitors, open_capture
from minimal.display import DisplayError
from minimal.loop import DEFAULT_PARAMS, Pipeline
from minimal.version import version_lines
from minimal.worker import WORK_MAX_H, WORK_MAX_W


def parse_params(overrides: list[str] | None) -> dict:
    """DEFAULT_PARAMS with `--param NAME=VALUE` overrides applied.

    Exists so a run can be changed without editing code — in particular so the
    effect can be dialled to zero, which is the only way to tell the neural
    pass's contribution to a frame from the contribution of sending that frame
    through the worker and back. Without such a control, "the pass is working"
    and "the transport perturbs pixels" look the same in a diff.

    Names are checked against the defaults rather than passed through, so a typo
    fails here with the list of real names instead of being quietly ignored by a
    worker that never sees it.
    """
    params = dict(DEFAULT_PARAMS)
    for item in overrides or []:
        name, sep, value = item.partition("=")
        name = name.strip()
        if not sep:
            raise ValueError(f"--param needs NAME=VALUE, got {item!r}")
        if name not in DEFAULT_PARAMS:
            raise ValueError(
                f"unknown parameter {name!r} — known: "
                f"{', '.join(sorted(DEFAULT_PARAMS))}")
        default = DEFAULT_PARAMS[name]
        try:
            params[name] = float(value) if isinstance(default, float) else int(value)
        except ValueError:
            want = "a number" if isinstance(default, float) else "an integer"
            raise ValueError(f"--param {name}={value}: expected {want}")
    return params


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="minimal",
        description="NeuralScreen MVP — capture, DLSS5 neural pass, display.")
    p.add_argument("--frames", type=int, default=0,
                   help="stop after N frames (0 = until the window is closed)")
    p.add_argument("--monitor", type=int, default=0, help="screen index (default 0)")
    p.add_argument("--bgra", action="store_true",
                   help="hand the synthetic card over in BGRA order, the way a capture "
                        "card does, so the handoff can be timed without a screen")
    p.add_argument("--source",
                   choices=("auto", "screen", "wayland", "window", "synthetic",
                            "image", "video"),
                   default="auto",
                   help="where frames come from: auto (portal on Wayland, X11 "
                        "grab otherwise), screen, wayland, window (the portal "
                        "asks for ONE window instead of a screen — cheaper, and "
                        "what a game stream wants), a generated test card, a "
                        "still image, or a video file replayed frame by frame "
                        "(the stream without the compositor, the browser or the "
                        "portal dialog — the only source that gives two runs the "
                        "same frames)")
    p.add_argument("--capture-no-scale", action="store_true",
                   help="drop videoscale from the capture pipeline. The chain "
                        "measures 33%% of a core at 2560x1440 — about 42ms of CPU "
                        "per frame — and this removes one 14.7MB pass from it. "
                        "The risk is caps negotiation failing when the portal's "
                        "reported size and the stream's disagree (fractional "
                        "scaling), which is loud rather than silent")
    p.add_argument("--size", metavar="WxH",
                   help="force the frame size for sources that can make one "
                        "(synthetic). Lets the 2560x1440 matrix be measured "
                        "without the portal and so without a dialog — which is "
                        "how the 1440p cost gets decomposed instead of guessed. "
                        "Required by --source window: a window stream reports no "
                        "size, and frames are scaled to this")
    p.add_argument("--input-image", metavar="PATH",
                   help="the frame to replay with --source image")
    p.add_argument("--input-video", metavar="PATH",
                   help="the file to replay with --source video; frames come out in order as "
                        "fast as they are asked for and the file loops at the end")
    p.add_argument("--interpolate", action="store_true",
                   help="present a generated mid-frame between each pair of real frames, so a "
                        "30-computed pipeline presents at ~60. Needs a worker that emits one "
                        "(OUT_FLAG_INTERPOLATED); costs a hold of --interp-pace-ms inside the "
                        "frame, without which the compositor coalesces the two presents")
    p.add_argument("--interp-pace-ms", type=float, default=8.0, metavar="MS",
                   help="how long to hold the mid-frame before the real one (default 8, one "
                        "refresh at 60Hz). It is taken out of the frame's own time")
    p.add_argument("--gil-switch-ms", type=float, default=0.0, metavar="MS",
                   help="the interpreter's thread switch interval; 0 (the default) keeps "
                        "CPython's 5ms. Added to test whether the client's wait for a reply was "
                        "the reader thread failing to get the GIL — it was not: at 1ms the recv "
                        "split moved 0.2ms, inside noise. Kept, off, as a knob for a future "
                        "reader that does more work per reply")
    p.add_argument("--param", action="append", metavar="NAME=VALUE",
                   help="override an NR parameter; repeatable. Known: "
                        + ", ".join(sorted(DEFAULT_PARAMS))
                        + ". e.g. --param intensity=0 to dial the effect off")
    p.add_argument("--work-scale", type=float, default=1.0, metavar="F",
                   help="fraction of the frame the network works on, 0<F<=1 "
                        "(default 1.0). The result is scaled back to full size, "
                        "so this buys frame rate without shrinking the output: "
                        "the cost falls with the square of the scale. Lower it "
                        "if the pass is too slow, at the cost of the effect's "
                        "own resolution")
    p.add_argument("--hotkeys", action="store_true",
                   help="register global hotkeys: Ctrl+Alt+1 toggles the enhancement, "
                        "Ctrl+Alt+Q quits. Global, so they work while the game window has "
                        "focus; needs a running X server (XWayland is enough)")
    p.add_argument("--indicator", dest="indicator", action="store_true", default=None,
                   help="draw an ON/OFF badge in the top-left corner of the output window "
                        "(default: on unless --headless). It is drawn by the renderer, not into "
                        "the frame, so a saved PNG stays clean")
    p.add_argument("--no-indicator", dest="indicator", action="store_false",
                   help="do not draw the badge")
    p.add_argument("--ab-alternate", type=float, default=0.0, metavar="SECONDS",
                   help="flip the enhancement on and off every SECONDS. An A/B with no keypress, "
                        "which matters because a global X grab does not see keys pressed in a "
                        "Wayland-native window")
    p.add_argument("--report-gpu", action="store_true",
                   help="sample GPU utilisation for the life of the run and report it with the "
                        "timings. A frame that is slow while the GPU is idle is one better code "
                        "could fix; one that is slow at 98%% means the work has to come out")
    p.add_argument("--report-diff", action="store_true",
                   help="print how far the pass moved the picture: per-channel MAD, maximum, "
                        "PSNR and the share of pixels that changed by more than 2 and 8 levels")
    p.add_argument("--save-diff", metavar="PATH",
                   help="write the difference as a PNG, amplified so a one-level change is "
                        "visible (see --diff-gain)")
    p.add_argument("--diff-gain", type=float, default=8.0,
                   help="amplification for --save-diff (default 8: 128 is no change, +/-8 levels "
                        "maps to the full range at gain 16)")
    p.add_argument("--windowed", action="store_true",
                   help="draw in a window instead of fullscreen")
    p.add_argument("--prefetch", action="store_true",
                   help="drain the frame source on its own thread and always "
                        "process the newest frame. A screencast whose client "
                        "stops consuming stops producing, so without this the "
                        "capture leg absorbs a producer round trip every frame "
                        "(measured: 238ms per grab in the loop against 13ms "
                        "with nothing else running). Costs a busy core")
    p.add_argument("--worker-env", action="append", default=[], metavar="KEY=VALUE",
                   help="set an environment variable in the worker process only. Repeatable. "
                        "The policy's [entry.env] applies to every run of that entry, so this is "
                        "how one run turns on a port-side switch (DLSS5VK_SERVE_SPLIT=1, a memory "
                        "setting) without editing the policy or affecting other runs")
    p.add_argument("--bypass", action="store_true",
                   help="NR OFF: the worker skips NGX entirely and hands back "
                        "the frame it was given. A truer control than "
                        "--param intensity=0, which may still run the network at "
                        "zero strength: this one separates the network from the "
                        "texture upload/readback when hunting the per-frame cost")
    p.add_argument("--send-ahead", type=int, default=1, metavar="N",
                   help="keep N frames in flight instead of sending one and "
                        "waiting for it (default 1 = the original serial loop). "
                        "The worker fed with no client at all runs 42.5fps at "
                        "1440p against the pipeline's 9.1, and the serialisation "
                        "is most of that difference")
    p.add_argument("--frame-timeout", type=float, default=60.0, metavar="S",
                   help="how long to wait for a reply before calling it a stall "
                        "(default 60s). A stall stops the run and names itself "
                        "rather than hanging: the worker answers in order, so "
                        "after a missing reply every later reply is "
                        "unattributable")
    p.add_argument("--writev", action="store_true",
                   help="hand each frame to the kernel in one scatter-gather "
                        "write instead of four separate ones. Each separate write "
                        "can block on a full pipe while the worker polls with a "
                        "Sleep(8), and the loop pays a fixed ~45ms a frame in "
                        "send at every frame size — while the worker's own "
                        "timestamps say it delivers a 64KB frame in 0.21ms")
    p.add_argument("--shm", dest="shm", action="store_true", default=True,
                   help="put the frame in a shared section for the worker to read, and take "
                        "the result pixels from another: 14.7MB each way at 2560x1440 that "
                        "otherwise go down a pipe (on by default). The native worker implements "
                        "both; a worker that does not - the Wine worker, and the mock in the "
                        "tests - refuses and every frame stays on the pipe, with a line saying "
                        "so, so asking for it cannot cost a run"),
    p.add_argument("--no-shm", dest="shm", action="store_false",
                   help="measure the pipe path instead: every number on the record before "
                        "2026-11-02 used it, and it under-reports by 7.5-13ms on the shapes "
                        "measured. Kept because comparing the two transports is the only reason "
                        "the pipe path still has a use"),
    # Off by default because the field is not a quality trade: the MVP builds
    # ONE all-zero field and reuses it, the native worker zero-fills its own
    # buffer when none arrives and calls that the identity reprojection, and the
    # pictures are byte-identical (r2026-10-30-ah vs -ad, MAD 0.0). At 1440p it
    # is 14.7MB of zeroes per frame, 5ms of send and 7.5ms of the frame.
    p.add_argument("--motion", dest="no_motion", action="store_false",
                   help="send the motion field after all. Not a quality decision - the "
                        "field is all zeros and the native worker's no-field path is "
                        "byte-identical - but the Wine worker derives flow from it, so "
                        "the NGX arm needs this on. Off by default: 14.7MB and ~5ms a "
                        "frame at 2560x1440 for bytes that change no pixel")
    p.add_argument("--no-motion", dest="no_motion", action="store_true",
                   help="do not send the motion field (the default; kept so existing "
                        "run requests and scripts still parse)")
    p.set_defaults(no_motion=True)
    p.add_argument("--motion-guides", action="store_true",
                   help="estimate the motion field with guides.py (DIS optical flow on a "
                        "downscaled gray frame, noise floor applied) instead of sending "
                        "zeros. Implies the field goes out, so the default no-motion path "
                        "is off for that run. Needs OpenCV (cv2) on this machine.")
    p.add_argument("--motion-small", action="store_true",
                   help="send the motion field at the optical-flow size "
                        "(320x180) and let the worker upscale it. NOT USABLE in "
                        "the pipe path: measured on the box, the worker goes "
                        "silent for 60s and never answers frame 0. Kept for the "
                        "wire format and the tests; see docs/M0-FINDINGS.md")
    p.add_argument("--worker-log", action="store_true",
                   help="echo the worker's stderr as it arrives — its warm-up and its "
                        "per-frame timings — instead of only printing it when a run "
                        "fails, which is why a slow first frame was invisible")
    p.add_argument("--headless", action="store_true",
                   help="run without presenting (for tests and CI)")
    p.add_argument("--save-before", metavar="PATH",
                   help="write the frame the pass was given, from the same "
                        "iteration as --save-after, as a PNG")
    p.add_argument("--save-after", metavar="PATH",
                   help="write the last processed frame as a PNG")
    p.add_argument("--save-mid", metavar="PATH",
                   help="write the last generated mid-frame as a PNG. Implies asking for pixels, "
                        "because a mid-frame IS a pixel reply (the worker skips it when the "
                        "caller wants none). Without this, --save-after writes a real frame and "
                        "the mid-frame — the point of the flag — is never visible in any artifact, "
                        "so a wrong warp can only be seen by watching the screen")
    p.add_argument("--list-monitors", action="store_true",
                   help="print the screens and exit")
    return p


def wants_pixels(args) -> bool:
    """Does this run need the worker's pixels back?

    Pixels cost the worker a 14.7MB readback plus a 14.7MB reply, so they are asked for only
    when something consumes them: a window to draw, a PNG to write, a diff to report. A
    headless benchmark that saves nothing should not pay for a channel it throws away.

    `--interpolate` belongs on this list and was missing from it. A generated mid-frame IS a
    pixel reply - the port's midPath is `wantInterp && wantPixels` - so a headless run with
    --interpolate asked for no pixels, got no mid-frames, and would have reported zero mids:
    a null that reads as a broken feature rather than as a question nobody asked.
    """
    return bool((not args.headless)
                or args.save_before or args.save_after or args.save_mid
                or args.report_diff or args.save_diff
                or args.interpolate)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # The reader thread decodes each reply and copies the pixels out of the shared section, and
    # it cannot do any of that until it holds the GIL. CPython switches threads every 5ms by
    # default, which is the same order as the client-side handoff a run measures: recv 29.6ms
    # against a worker total of 19.7 leaves ~8ms, and the frame's own copy accounts for 1.7 of it.
    # A shorter interval lets the reader run as soon as the worker's bytes land. It costs more
    # context switches, which is why it is a knob and not a silent change.
    if args.gil_switch_ms and args.gil_switch_ms > 0:
        sys.setswitchinterval(args.gil_switch_ms / 1000.0)

    if args.list_monitors:
        try:
            for idx, desc in list_monitors():
                print(f"  monitor {idx}: {desc}")
        except CaptureError as exc:
            print(f"no screens: {exc}", file=sys.stderr)
            return 1
        return 0

    try:
        params = parse_params(args.param)
    except ValueError as exc:
        print(f"bad --param: {exc}", file=sys.stderr)
        return 2

    if not 0.0 < args.work_scale <= 1.0:
        # Above 1 would ask the network for more pixels than the frame has,
        # which the worker refuses; 0 would ask for a zero-pixel frame.
        print(f"bad --work-scale: {args.work_scale} is not in (0, 1]",
              file=sys.stderr)
        return 2

    force_w = force_h = None
    if args.size:
        try:
            w_s, h_s = args.size.lower().split("x")
            force_w, force_h = int(w_s), int(h_s)
        except ValueError:
            print(f"bad --size: {args.size!r} is not WxH (e.g. 2560x1440)",
                  file=sys.stderr)
            return 2
        if force_w < 64 or force_h < 64:
            print(f"bad --size: {args.size} is smaller than 64x64",
                  file=sys.stderr)
            return 2

    if args.bgra and args.source != "synthetic":
        print("--bgra only applies to --source synthetic; a real capture reports its own order",
              file=sys.stderr)
        return 2

    try:
        source = open_capture(args.source, monitor=args.monitor,
                              input_image=args.input_image,
                              input_video=args.input_video,
                              width=force_w, height=force_h,
                              video_scale=not args.capture_no_scale,
                              bgra=args.bgra)
        if args.prefetch:
            # Wrap before the Pipeline sees it: the loop then reads a frame that
            # is already waiting instead of one the producer makes on demand.
            from minimal.prefetch import Prefetch
            source = Prefetch(source, log=print)
        worker_extra = {}
        for item in args.worker_env:
            key, _, value = item.partition("=")
            if not key or not _:
                raise SystemExit(f"--worker-env wants KEY=VALUE, got {item!r}")
            worker_extra[key] = value
        pipe = Pipeline(fullscreen=not args.windowed, headless=args.headless,
                        capture=source, params=params,
                        work_scale=args.work_scale,
                        motion_small=args.motion_small,
                        bypass=args.bypass,
                        send_ahead=args.send_ahead,
                        no_motion=args.no_motion,
                        motion_guides=args.motion_guides,
                        shm=args.shm,
                        # Pixels cost the worker a 14.7MB readback plus a 14.7MB reply.
                        # Ask for them only when something consumes them: a window to
                        # draw or a PNG to write. A headless benchmark that saves
                        # nothing should not pay for a channel it throws away.
                        want_pixels=wants_pixels(args),
                        frame_timeout=args.frame_timeout,
                        writev=args.writev,
                        worker_log=args.worker_log,
                        interpolate=args.interpolate,
                        interp_pace=args.interp_pace_ms / 1000.0,
                        worker_env_extra=worker_extra,
                        indicator=args.indicator,
                        report_diff=args.report_diff,
                        save_diff=args.save_diff,
                        diff_gain=args.diff_gain,
                        ab_alternate=args.ab_alternate,
                        report_gpu=args.report_gpu)
    except (CaptureError, DisplayError) as exc:
        print(f"startup failed: {exc}", file=sys.stderr)
        return 2

    if args.hotkeys:
        # Which backend is decided in hotkeys_backend: on Wayland the X11 grab cannot see a
        # Wayland window's keys, and it fails *silently* — that is why Ctrl+Alt+1 registered and
        # then did nothing. The callbacks only enqueue; the loop owns the state, and a toggle
        # applied from a reader thread would race the frame it is building.
        import hotkeys_backend
        hotkeys_backend.install(pipe)

    print(f"source {args.source}"
          + (f" ({args.input_image})" if args.source == "image" else "")
          + f"  capture {pipe.width}x{pipe.height}  ->  "
          f"work {pipe.work_w}x{pipe.work_h} "
          f"(work scale {pipe.work_scale:.2f}, "
          f"NGX ceiling {WORK_MAX_W}x{WORK_MAX_H})")
    # Printed because a diff is only interpretable alongside the settings that
    # produced it, and a report is read long after the command line is gone.
    print("params: " + " ".join(f"{k}={pipe.params[k]}" for k in sorted(pipe.params)))
    print(f"worker: {' '.join(pipe.worker.cmd)}")
    # Which code this run is, said before it starts. A run was once reported from a stale
    # binary — the apply failed and the build never ran — and nothing in the output could
    # have told anyone that, which is a whole afternoon when the numbers are surprising.
    for line in version_lines(pipe.worker.cmd):
        print(line)

    try:
        summary = pipe.run(frames=args.frames,
                           save_before=args.save_before,
                           save_after=args.save_after,
                           save_mid=args.save_mid)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        pipe.close()
        return 130
    except Exception as exc:
        print(f"pipeline failed: {exc}", file=sys.stderr)
        traceback.print_exc()
        pipe.close()
        return 3

    print(f"frames: {summary['frames_done']} done, "
          f"{summary['frames_skipped']} skipped, "
          f"{summary['seconds']}s ({summary['fps']} fps headline, "
          f"{summary.get('steady_fps', summary['fps'])} fps steady), "
          f"worker exit {summary['worker_exit']}")
    # Where the time actually goes. "4.2 fps" alone cannot be acted on: the fix
    # is completely different depending on whether the frame is lost in the
    # capture, in our own bytes down the pipe, or waiting on the worker.
    t = summary.get("timing", {})
    if t.get("count"):
        parts = [f"{k} {1000 * t[k]:.1f}ms"
                 for k in ("capture", "send", "recv", "display") if k in t]
        steady = t.get("steady_fps", t["fps"])
        med = t.get("total_median", t["total"])
        print(f"timing: {'  '.join(parts)}   "
              f"(mean {1000 * t['total']:.1f}ms/frame, {t['fps']:.1f} fps; "
              f"median {1000 * med:.1f}ms/frame, {steady:.1f} fps steady)")
        # recv is the largest stage and it is opaque: it holds the worker's own time, the
        # handoff and our copy of the frame out of the shared section. The copy is timed
        # on the reader thread, so it can be taken out of recv - what remains is waiting.
        if "recv_copy" in t:
            _c = t["recv_copy"]
            _left = t["recv"] - _c
            print(f"recv split (means): copy {1000 * _c:.1f}ms "
                  f"(min {1000 * t['recv_copy_min']:.1f}, max {1000 * t['recv_copy_max']:.1f}) "
                  f"+ waiting {1000 * _left:.1f}ms   "
                  f"<- the copy is ours; the wait is the worker and the handoff")
    # Presented frames, which is not the same thing as computed frames once mid-frames are
    # generated: the eye sees the presentation rate, the pipeline pays for the computed one.
    shown = summary.get("interp_shown")
    if shown:
        secs = summary.get("seconds") or 0.0
        rate = (shown / secs) if secs > 0 else 0.0
        print(f"interp: {shown} generated frames presented"
              + (f" ({rate:.1f}/s) beside {summary['frames_done']} computed" if secs > 0 else "")
              + " — presentation is the computed rate plus these")
    # An A/B run alternates, and a bypassed frame runs no network at all, so the frame time above
    # is a mixture of two different machines. Said loudly, because it reads as a rate the pipeline
    # can hold, and with the pass on it is roughly half of what the mixture suggests.
    modes = summary.get("modes") or {}
    if modes.get("alternate") and modes.get("bypassed_frames"):
        print(f"          ! the A/B was on (every {modes['alternate']:g}s): "
              f"{modes['enhanced_frames']} frames enhanced at {modes['enhanced_fps']:.1f} fps, "
              f"{modes['bypassed_frames']} bypassed at {modes['bypassed_fps']:.1f} fps. "
              f"The frame time above is both modes averaged - the enhanced rate is the one that "
              f"describes the product. Run with --ab-alternate 0 to measure throughput.")
    # What the frame source replayed, when it can say. A timing from a file is meaningless without
    # knowing which file and how far into it the run got: a run that looped twice is not the same
    # run as one that never reached the end.
    src = summary.get("source")
    if src and src.get("path"):
        loops = src.get("loops")
        print(f"source: replayed {src['path']} — {src.get('frames_decoded', '?')} frames decoded"
              + (f", {loops} loop{'s' if loops != 1 else ''}" if loops is not None else ""))
    # The worker's own timestamps, which know nothing of ours. Printed beside the
    # timing line on purpose: if these two disagree about the same run, the
    # timing line is what is wrong.
    wc = summary.get("worker_clock") or {}
    # The spread rather than the mean, for every stage that has one. A stage that
    # costs the same on every frame is structural — something is pacing at a fixed
    # interval. A stage that is small most frames and huge once is a one-off, and
    # the two need opposite fixes... but only if you can see which it is: a run
    # reported "recv 627.7ms" as its mean, and that number is either the network
    # being 60x slower than bench says or one warm-up frame divided by sixty.
    # The frame that carried the peak is what settles it, so it is printed with it.
    def spread_line(name: str) -> None:
        lo, mid, hi = (1000 * t[f"{name}_min"], 1000 * t[f"{name}_median"],
                       1000 * t[f"{name}_max"])
        at = t.get(f"{name}_max_at", -1)
        # A peak carried by a frame sent before the worker's first reply is the
        # worker's warm-up (its model load and PTX JIT), not a per-frame cost.
        # The first reply cannot land until `send_ahead` sends have been issued:
        # with --send-ahead 2 the second send blocks while the worker JITs, so a
        # 4.4s block lands at frame 1 and an index-0-only test called it a real
        # stall. Ask "was this frame sent before the first reply" instead.
        warmup_last = summary.get("send_ahead", 1) - 1
        if hi < 2 * lo:
            shape = "steady — a fixed interval, not contention"
        elif 0 <= at <= warmup_last:
            shape = (f"one-off at frame {at} — sent before the worker's first "
                     f"reply lands, so the warm-up, not a per-frame cost")
        else:
            shape = f"a one-off at frame {at} — not the warm-up, so worth looking at"
        print(f"{name} spread: min {lo:.1f}  median {mid:.1f}  max {hi:.1f} ms "
              f"at frame {at} of {t.get('count', 0)}   ({shape})")

    for name in ("send", "recv"):          # our traffic out, and the worker's answer
        if t.get(f"{name}_max") is not None:
            spread_line(name)
    for name in sorted(k[:-4] for k in t if k.endswith("_max")):
        if name in ("send", "recv"):
            continue
        median = t.get(f"{name}_median", 0.0)
        # Only the stages whose peak is a one-off in its own right: a stage that is
        # always large has a large max too, and naming every one of those buries the
        # line that matters.
        if median > 0 and t[f"{name}_max"] > 2 * median and t[f"{name}_max"] > 0.02:
            spread_line(name)
    if wc.get("ms_per_frame"):
        print(f"worker clock: {wc['frames']} frames in {wc['span_s']}s = "
              f"{wc['ms_per_frame']} ms/frame "
              f"({1000 / wc['ms_per_frame']:.0f} fps, from the worker's own "
              f"timestamps)")
    if wc.get("gap_s", 0) > 1.0 and wc.get("gap_between"):
        a, b = wc["gap_between"]
        print(f"worker stall: {wc['gap_s']:.1f}s between {a!r} and {b!r}")
    worst = wc.get("worst_ms_per_frame")
    if worst and wc.get("ms_per_frame") and worst > 2 * wc["ms_per_frame"]:
        print(f"worker stall: its slowest stretch between frame reports ran at "
              f"{worst:.0f} ms/frame against {wc['ms_per_frame']:.1f} overall")
    # Only the portal can split its own grab, and the split decides everything:
    # a slow grab is the compositor if the wait dominates, and us if the read
    # does.
    if "capture_wait" in t:
        pipe_bytes = t.get("capture_pipe_bytes")
        # The threshold moves with the buffer: a drained frame is 14.7 MB at 2560x1440, and
        # the floor is what the pipe can carry. 64 KiB hosts give ~19 ms, 1 MiB ~9 ms. Naming
        # the buffer the kernel granted keeps the number from being read against the wrong one.
        if pipe_bytes:
            kib = pipe_bytes // 1024
            floor = {65536: 19.0, 1048576: 9.0}.get(pipe_bytes, 0.3 * kib / 14.7)
            note = (f"read near {floor:.0f}ms at 2560x1440 with a {kib} KiB pipe means we are "
                    f"draining a stocked pipe; far above that means the compositor was "
                    f"dribbling")
        else:
            note = ("read ~19ms at 2560x1440 means we are draining a stocked pipe; far above "
                    "that means the compositor was dribbling")
        print(f"capture split: wait {1000 * t['capture_wait']:.1f}ms  "
              f"read {1000 * t['capture_read']:.1f}ms   ({note})")
    # What the prefetch drain saw. The frame age is the latency the capture
    # adds, for real: with old frames dropped it stays near one frame time
    # rather than growing with a queue.
    pf = summary.get("prefetch")
    if pf:
        mean = pf.get("age_mean")
        mx = pf.get("age_max")
        ages = (f"frame age mean {1000 * mean:.1f}ms max {1000 * mx:.1f}ms"
                if mean is not None else "no frame used")
        print(f"prefetch: drained {pf['drained']} frames on its own thread, "
              f"{pf['dropped']} dropped, {ages}")
        if mean is not None and mean > 0.100:
            print(f"          ! the drain is being starved ({1000 * mean:.0f}ms "
                  f"mean age): it competes with the worker for memory "
                  f"bandwidth, so it may cost more than the round trip it saves")
    # The capture chain's own CPU. It never shows in the frame time, and at
    # 2560x1440 it competes with the worker rather than waiting for it.
    cc = summary.get("capture_cpu")
    if cc is not None and cc.get("share") is not None:
        print(f"capture cpu: the pipeline used {cc['seconds']:.2f}s over "
              f"{cc['wall']:.2f}s = {100 * cc['share']:.0f}% of one core")
        if cc["share"] > 0.5:
            print(f"          ! that work runs while the worker waits: the same "
                  f"2560x1440 frame cost send 114.2ms through the portal against "
                  f"67.3ms produced synthetically")
    elif cc is not None:
        # The source says it can report its CPU and the reading failed. Saying
        # so, rather than omitting the line, is the difference between a bug and
        # a measurement that quietly looks like zero.
        print(f"capture cpu: NOT measured — {cc['reason']} "
              f"(pid {cc.get('pid')})")
    if pipe.gpu is not None:
        print(pipe.gpu.describe())
    if args.save_before:
        print(f"  before -> {args.save_before}")
    if args.save_after:
        print(f"  after  -> {args.save_after}")
    if args.save_mid:
        n = summary.get("interp_shown", 0)
        if n:
            print(f"  mid    -> {args.save_mid} ({n} generated frames arrived; the last one)")
        else:
            print(f"  mid    -> nothing written: asked for a mid-frame, none arrived "
                  f"(the worker needs the mid path, and it only runs when the caller asks for "
                  f"pixels - which this run now does)")
    return 0 if summary["frames_done"] > 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())