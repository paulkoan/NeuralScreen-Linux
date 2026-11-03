#!/bin/bash
# port_profile.sh — per-dispatch timings for the built port, at the resolution we ship.
#
# WHY
#
# The port's neural pass runs 12.0-13.5 ms at 2560x1440 inside the worker (network+composite,
# steady frames of r2026-11-03-live-1440p) against NGX's 7.1 ms for the same weights at the same
# size. That ~1.7x is the largest single cost left in the frame and it is NOT the schedule:
# counter chaining is on at this resolution (`nr_graph.cpp` falls back to a barrier after every
# launch only when `(fullHeight + 11) / 8 > 512`, which is 181 here), and the graph is fused.
# What is left is the arithmetic inside the kernels, and the port can already say where it goes:
#
#   dlss5vk profile --model <dir> --width 2560 --height 1440 --frames 7
#
# prints every dispatch with a timestamp span, then totals by kernel and by stage, taking the
# per-dispatch minimum over the frames so other tenants on the GPU cannot inflate it. This
# script is that call, with the paths the runner uses, so a tick can run it.
#
# WHAT IT NEEDS FROM THE BOX
#
# A policy entry, because argv is fixed in /opt/neuralscreen/policy.toml and nothing here may
# edit it:
#
#   [[entry]]
#   name = "port-profile"
#   argv = ["bash", "tools/port_profile.sh"]
#
# The binary is NOT rebuilt here - it profiles whatever port-build last produced, which is the
# point: the number has to belong to the code the runs are using.
#
# USAGE
#
#   bash tools/port_profile.sh                 # 2560x1440, the resolution we ship
#   bash tools/port_profile.sh 1920 1080       # a size to compare against
#
# Env overrides: NEURALSCREEN_PORT_BIN, NEURALSCREEN_MODEL_DIR.
set -uo pipefail

BIN="${NEURALSCREEN_PORT_BIN:-/opt/neuralscreen/port/build/dlss5vk}"
MODEL="${NEURALSCREEN_MODEL_DIR:-/opt/neuralscreen/model}"
WIDTH="${1:-2560}"
HEIGHT="${2:-1440}"
FRAMES="${3:-7}"

if [[ ! -x "$BIN" ]]; then
    echo "no port binary at $BIN" >&2
    echo "  the runner's port-build entry produces it; set NEURALSCREEN_PORT_BIN otherwise" >&2
    exit 1
fi
if [[ ! -d "$MODEL" ]]; then
    echo "no model directory at $MODEL" >&2
    echo "  extract it with experiments/opendlss_weights/extract.py; set NEURALSCREEN_MODEL_DIR" >&2
    exit 1
fi

echo "binary: $BIN"
echo "model:  $MODEL"
echo "size:   ${WIDTH}x${HEIGHT}, minimum of $FRAMES frames per dispatch"
echo

# The profile route disables chaining on purpose (per-dispatch timings need the barriers), so
# its total is not the frame's total and must not be compared against one. The comparison that
# matters is between kernels and between the two branches, both measured the same way.
"$BIN" profile --model "$MODEL" --width "$WIDTH" --height "$HEIGHT" --frames "$FRAMES"