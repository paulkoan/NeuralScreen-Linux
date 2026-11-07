#!/bin/bash
# neuralscreen.sh — v1: the MVP pipeline, on the native port, with global hotkeys.
#
# WHY THIS AND NOT main_linux.py
#
# main_linux.py is the Windows-derived GUI (menu, HUD, recording, window modes, monitor
# switching) and its Linux backends were never finished: display_linux was a stub against an app
# that expects twenty more methods, and pipeline_linux was missing five functions. Each attempt to
# start it found the next unbuilt corner.
#
# The MVP in minimal/ is the path that has actually worked for weeks: portal capture of one
# window, the native port as the worker, an SDL window showing the result. It needed nothing
# added except hotkeys, which it now has. So v1 runs that.
#
# WHAT IT NEEDS
#
#   the port binary   /opt/neuralscreen/port/build/dlss5vk   (port-build produces it)
#   the model         /opt/neuralscreen/model                (extract.py produces it)
#   a graphical session, because the capture is a portal screen-cast
#
# Override with NEURALSCREEN_PORT_BIN, NEURALSCREEN_MODEL_DIR, NEURALSCREEN_SIZE.
#
# USAGE
#
#   ./neuralscreen.sh                    # 2560x1440, one window
#   ./neuralscreen.sh --frames 300       # extra flags go straight to minimal
#
# THE FAST PATH (the largest lever measured towards 60 fps)
#
#   NEURALSCREEN_SIZE=1920x1080 ./neuralscreen.sh
#
#   The pass costs the square of the resolution, so running it internally at 1080p and letting
#   the present scale the result up to the 1440p desktop is worth ~7 ms a frame: 19.5 ms (51 fps)
#   at 1080p with the pixel channel against 26.4 ms (38 fps) at 1440p, both over shared memory.
#   The window is fullscreen-desktop, so the scaling is free - the renderer stretches the frame
#   to the screen with a linear filter. What you pay is the picture: a 1080p image upscaled to
#   1440p is softer than a native 1440p one, which is the trade the settings instruction allows.
#   Everything else about the run is unchanged.
#
# The portal asks which window to share. Pick the game stream window.
#
# HOTKEYS (global - they work while the game window has focus)
#
#   F1 / Space   enhancement on/off (the output window must have focus)
#   Ctrl+Alt+1   the same, but global - and on Wayland a global X grab does not see keys
#                pressed in a Wayland-native window, so treat it as a bonus when it works
#   Ctrl+Alt+Q   quit
#   Esc / q      quit (the output window needs focus for these)
#
# SAVING THE STATS
#
# Every run is teed into runs/local/<timestamp>.log and, when it finishes, that file is
# committed and pushed to main so the analysis clone can read it. The rest of the working
# tree is left alone - on this box it may hold edits that are not ours to publish.
# NEURALSCREEN_UPLOAD=0 keeps a run local; the log is still written.
#
# The A/B also runs on a timer: the enhancement flips every NEURALSCREEN_AB seconds (default 3,
# 0 disables). That is the comparison that needs nothing from you, and the badge says which half
# you are looking at. NEURALSCREEN_DIFF=0 turns off the end-of-run diff report, which is reported
# alongside GPU utilisation (sampled once a second - each sample is an nvidia-smi call).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT_BIN="${NEURALSCREEN_PORT_BIN:-/opt/neuralscreen/port/build/dlss5vk}"
MODEL_DIR="${NEURALSCREEN_MODEL_DIR:-/opt/neuralscreen/model}"
SIZE="${NEURALSCREEN_SIZE:-2560x1440}"

if [[ ! -x "$PORT_BIN" ]]; then
    echo "no port binary at $PORT_BIN" >&2
    echo "  build it with the runner's port-build entry, or set NEURALSCREEN_PORT_BIN" >&2
    exit 1
fi
if [[ ! -d "$MODEL_DIR" ]]; then
    echo "no model directory at $MODEL_DIR" >&2
    echo "  extract it with experiments/opendlss_weights/extract.py, or set NEURALSCREEN_MODEL_DIR" >&2
    exit 1
fi
if [[ -z "${WAYLAND_DISPLAY:-}" && -z "${DISPLAY:-}" ]]; then
    echo "no WAYLAND_DISPLAY or DISPLAY in this shell" >&2
    echo "  the capture is a portal screen-cast, so this has to run in the graphical session" >&2
    exit 1
fi

export NS_WORKER_CMD="${NS_WORKER_CMD:-$PORT_BIN serve --model $MODEL_DIR}"

# A segfault in a C extension (SDL, cv2, Xlib) prints nothing useful without this.
export PYTHONFAULTHANDLER=1

PYTHON="$HERE/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"

AB="${NEURALSCREEN_AB:-3}"
DIFF="${NEURALSCREEN_DIFF:-1}"
extra=()
[[ "$DIFF" != "0" ]] && extra+=(--report-diff)
extra+=(--report-gpu)
[[ "$AB" != "0" ]] && extra+=(--ab-alternate "$AB")

echo "worker: $NS_WORKER_CMD"
echo "size:   $SIZE"
[[ "$AB" != "0" ]] && echo "A/B:    enhancement flips every ${AB}s"

# SAVE AND UPLOAD THE STATISTICS
#
# The stats are printed, not written: the [perf] lines, the diff summary and the GPU
# samples all go to stdout. So the run is teed into a tracked log under runs/local/, and
# only that one file is committed - never the rest of the working tree, which on this box
# may hold local edits that are not ours to publish. The commit goes to main, so the next
# pull in the analysis clone sees it.
#
# Set NEURALSCREEN_UPLOAD=0 to keep a run local (the log is still written).
STATS_DIR="$HERE/runs/local"
STATS_LOG="$STATS_DIR/$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$STATS_DIR"

# Unbuffered, or the tee'd log arrives in 8 KiB blocks and a killed run loses its tail.
export PYTHONUNBUFFERED=1

"$PYTHON" -m minimal --source window --size "$SIZE" --shm --hotkeys "${extra[@]}" "$@" 2>&1 | tee "$STATS_LOG"
STATUS=${PIPESTATUS[0]}

# The upload lives in tools/ so it can be tested on its own: it commits one file, pushes it, and
# then asks the remote whether it really has it. Reporting success from a push's exit code is how
# a run's stats went missing while the terminal said "uploaded".
if [[ "${NEURALSCREEN_UPLOAD:-1}" == "0" ]]; then
    echo "stats: saved to $STATS_LOG (upload disabled)"
else
    "$HERE/tools/upload_stats.sh" "$HERE" "$STATS_LOG" "$STATUS"
fi

exit "$STATUS"
