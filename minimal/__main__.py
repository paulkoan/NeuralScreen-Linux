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
    p.add_argument("--source",
                   choices=("auto", "screen", "wayland", "window", "synthetic",
                            "image"),
                   default="auto",
                   help="where frames come from: auto (portal on Wayland, X11 "
                        "grab otherwise), screen, wayland, window (the portal "
                        "asks for ONE window instead of a screen — cheaper, and "
                        "what a game stream wants), a generated test card, or a "
                        "still image")
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
                        "how the 1440p cost gets decomposed instead of guessed")
    p.add_argument("--input-image", metavar="PATH",
                   help="the frame to replay with --source image")
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
    p.add_argument("--windowed", action="store_true",
                   help="draw in a window instead of fullscreen")
    p.add_argument("--prefetch", action="store_true",
                   help="drain the frame source on its own thread and always "
                        "process the newest frame. A screencast whose client "
                        "stops consuming stops producing, so without this the "
                        "capture leg absorbs a producer round trip every frame "
                        "(measured: 238ms per grab in the loop against 13ms "
                        "with nothing else running). Costs a busy core")
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
    p.add_argument("--motion-small", action="store_true",
                   help="send the motion field at the optical-flow size "
                        "(320x180) and let the worker upscale it. NOT USABLE in "
                        "the pipe path: measured on the box, the worker goes "
                        "silent for 60s and never answers frame 0. Kept for the "
                        "wire format and the tests; see docs/M0-FINDINGS.md")
    p.add_argument("--headless", action="store_true",
                   help="run without presenting (for tests and CI)")
    p.add_argument("--save-before", metavar="PATH",
                   help="write the frame the pass was given, from the same "
                        "iteration as --save-after, as a PNG")
    p.add_argument("--save-after", metavar="PATH",
                   help="write the last processed frame as a PNG")
    p.add_argument("--list-monitors", action="store_true",
                   help="print the screens and exit")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

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

    try:
        source = open_capture(args.source, monitor=args.monitor,
                              input_image=args.input_image,
                              width=force_w, height=force_h,
                              video_scale=not args.capture_no_scale)
        if args.prefetch:
            # Wrap before the Pipeline sees it: the loop then reads a frame that
            # is already waiting instead of one the producer makes on demand.
            from minimal.prefetch import Prefetch
            source = Prefetch(source, log=print)
        pipe = Pipeline(fullscreen=not args.windowed, headless=args.headless,
                        capture=source, params=params,
                        work_scale=args.work_scale,
                        motion_small=args.motion_small,
                        bypass=args.bypass,
                        send_ahead=args.send_ahead,
                        frame_timeout=args.frame_timeout,
                        writev=args.writev)
    except (CaptureError, DisplayError) as exc:
        print(f"startup failed: {exc}", file=sys.stderr)
        return 2

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

    try:
        summary = pipe.run(frames=args.frames,
                           save_before=args.save_before,
                           save_after=args.save_after)
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
          f"{summary['seconds']}s ({summary['fps']} fps), "
          f"worker exit {summary['worker_exit']}")
    # Where the time actually goes. "4.2 fps" alone cannot be acted on: the fix
    # is completely different depending on whether the frame is lost in the
    # capture, in our own bytes down the pipe, or waiting on the worker.
    t = summary.get("timing", {})
    if t.get("count"):
        parts = [f"{k} {1000 * t[k]:.1f}ms"
                 for k in ("capture", "send", "recv", "display") if k in t]
        print(f"timing: {'  '.join(parts)}   "
              f"(total {1000 * t['total']:.1f}ms/frame, {t['fps']:.1f} fps)")
    # The worker's own timestamps, which know nothing of ours. Printed beside the
    # timing line on purpose: if these two disagree about the same run, the
    # timing line is what is wrong.
    wc = summary.get("worker_clock") or {}
    # The spread rather than the mean. send is a fixed ~40ms a frame at every
    # frame size, which no per-frame work in this process explains: the worker's
    # own clock says it delivered the same frame in 0.17ms. Steady send means
    # something is pacing us at a fixed interval; spiky send means we are being
    # descheduled, and only the first of those is a pacing bug.
    if t.get("send_max") is not None:
        lo, mid, hi = (1000 * t["send_min"], 1000 * t["send_median"],
                       1000 * t["send_max"])
        shape = ("steady — a fixed interval, not contention"
                 if hi < 2 * lo else "spiky — we are being descheduled")
        print(f"send spread: min {lo:.1f}  median {mid:.1f}  max {hi:.1f} ms "
              f"at frame {t.get('send_max_at', -1)} of {t.get('count', 0)}   ({shape})")
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
        print(f"capture split: wait {1000 * t['capture_wait']:.1f}ms  "
              f"read {1000 * t['capture_read']:.1f}ms   "
              f"(read ~19ms at 2560x1440 means we are draining a stocked pipe; "
              f"read far above that means the compositor was dribbling)")
    # What the prefetch drain saw. The frame age is the honest latency the
    # capture adds: with old frames dropped it stays near one frame time rather
    # than growing with a queue.
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
    if args.save_before:
        print(f"  before -> {args.save_before}")
    if args.save_after:
        print(f"  after  -> {args.save_after}")
    return 0 if summary["frames_done"] > 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())