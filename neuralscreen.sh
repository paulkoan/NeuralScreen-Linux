#!/bin/bash
# neuralscreen.sh — start v1: the app, with the native port as its worker.
#
# WHAT THIS IS
#
# main_linux.py is the application: capture, guides, the worker, the overlay, the hotkeys. It
# was written against the Wine/NGX worker and had no way to run the native port, which is what
# v1 ships. This script supplies the two things the app cannot guess - which binary to run and
# which config to read - and then gets out of the way.
#
# The port speaks the same worker protocol as the Wine path, so nothing else in the app changes:
# same header, same frames, same replies. NS_WORKER_CMD is the switch, and pipeline_linux honours
# it (it used to hard-code native/run_worker.sh).
#
# WHAT IT NEEDS
#
#   the port binary   /opt/neuralscreen/port/build/dlss5vk   (port-build produces it)
#   the model         /opt/neuralscreen/model                (extract.py produces it)
#   a graphical session, because the capture is a portal screen-cast
#
# Override any of them with NEURALSCREEN_PORT_BIN, NEURALSCREEN_MODEL_DIR, NEURALSCREEN_CONFIG.
#
# USAGE
#
#   ./neuralscreen.sh                 # config.v1.json beside this script
#   ./neuralscreen.sh my-config.json  # a config of your own
#
# Hotkeys are the app's own: Num1 NR on/off, Num2 settings, Num3 screenshot, Num0 record,
# Num4/Num6 resolution, Num5 one window instead of the screen, Ctrl+Alt+Q quit.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT_BIN="${NEURALSCREEN_PORT_BIN:-/opt/neuralscreen/port/build/dlss5vk}"
MODEL_DIR="${NEURALSCREEN_MODEL_DIR:-/opt/neuralscreen/model}"
CONFIG="${1:-${NEURALSCREEN_CONFIG:-$HERE/config.v1.json}}"

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
if [[ ! -f "$CONFIG" ]]; then
    echo "no config at $CONFIG" >&2
    echo "  config.v1.json ships beside this script; pass another path as the first argument" >&2
    exit 1
fi
if [[ -z "${WAYLAND_DISPLAY:-}" && -z "${DISPLAY:-}" ]]; then
    echo "no WAYLAND_DISPLAY or DISPLAY in this shell" >&2
    echo "  the capture is a portal screen-cast, so this has to run in the graphical session" >&2
    exit 1
fi

# The worker command. Left alone if the caller already set one, so a Wine run can still be
# started by exporting NS_WORKER_CMD before this script.
export NS_WORKER_CMD="${NS_WORKER_CMD:-$PORT_BIN serve --model $MODEL_DIR}"

PYTHON="$HERE/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"

echo "worker: $NS_WORKER_CMD"
echo "config: $CONFIG"
exec "$PYTHON" "$HERE/main_linux.py" --config "$CONFIG"
