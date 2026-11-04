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
# The portal asks which window to share. Pick the game stream window.
#
# HOTKEYS (global - they work while the game window has focus)
#
#   Ctrl+Alt+1   enhancement on/off - the A/B, live
#   Ctrl+Alt+Q   quit
#   Esc / q      quit (the output window needs focus for these)
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

echo "worker: $NS_WORKER_CMD"
echo "size:   $SIZE"

exec "$PYTHON" -m minimal --source window --size "$SIZE" --shm --hotkeys "$@"
