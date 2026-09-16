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
    p.add_argument("--source", choices=("auto", "screen", "wayland", "synthetic", "image"),
                   default="auto",
                   help="where frames come from: auto (portal on Wayland, X11 "
                        "grab otherwise), screen, wayland, a generated test "
                        "card, or a still image")
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
    p.add_argument("--motion-small", action="store_true",
                   help="send the motion field at the optical-flow size "
                        "(320x180) and let the worker upscale it. The MVP's "
                        "field is all zeros, so this changes nothing about what "
                        "the network sees and removes ~half the bytes of every "
                        "frame sent to the worker")
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

    try:
        source = open_capture(args.source, monitor=args.monitor,
                              input_image=args.input_image)
        pipe = Pipeline(fullscreen=not args.windowed, headless=args.headless,
                        capture=source, params=params,
                        work_scale=args.work_scale,
                        motion_small=args.motion_small)
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
    if args.save_before:
        print(f"  before -> {args.save_before}")
    if args.save_after:
        print(f"  after  -> {args.save_after}")
    return 0 if summary["frames_done"] > 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())