"""Entry point: python -m minimal [--frames N] [--monitor M] [--headless]

The MVP run: capture the screen, run every frame through the DLSS5 neural pass
in the Wine worker, show the result in a fullscreen SDL2 window.
"""

from __future__ import annotations

import argparse
import sys
import traceback

from minimal.capture import CaptureError, list_monitors
from minimal.display import DisplayError
from minimal.loop import Pipeline
from minimal.worker import WORK_MAX_H, WORK_MAX_W


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="minimal",
        description="NeuralScreen MVP — capture, DLSS5 neural pass, display.")
    p.add_argument("--frames", type=int, default=0,
                   help="stop after N frames (0 = until the window is closed)")
    p.add_argument("--monitor", type=int, default=0, help="screen index (default 0)")
    p.add_argument("--windowed", action="store_true",
                   help="draw in a window instead of fullscreen")
    p.add_argument("--headless", action="store_true",
                   help="run without presenting (for tests and CI)")
    p.add_argument("--save-before", metavar="PATH",
                   help="write the first captured frame as a PNG")
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
        pipe = Pipeline(monitor=args.monitor, fullscreen=not args.windowed,
                        headless=args.headless)
    except (CaptureError, DisplayError) as exc:
        print(f"startup failed: {exc}", file=sys.stderr)
        return 2

    print(f"capture {pipe.width}x{pipe.height}  ->  "
          f"work {pipe.work_w}x{pipe.work_h} "
          f"(NGX ceiling {WORK_MAX_W}x{WORK_MAX_H})")
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
    if args.save_before:
        print(f"  before -> {args.save_before}")
    if args.save_after:
        print(f"  after  -> {args.save_after}")
    return 0 if summary["frames_done"] > 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())