#!/bin/bash
# make_test_clip.sh [OUTPUT] [SECONDS] — a stand-in for a stream, with a stream's artefacts.
#
# WHAT THIS IS FOR
#
# Every live run so far has been a different session. The same unchanged pipeline, on the same
# box, read 15.8 / 17.1 / 17.3 / 20.9 fps - because the content differed and so did the load. A
# number like that cannot be compared to the next number, which is most of why the last few days
# of measurements disagree with each other.
#
# A file fixes that: the frames are the same every run, so two runs differ only by what was
# changed. This script writes one, and it is deliberately not a pristine render - it is encoded at
# a low bitrate so it carries the blocking, banding and mosquito noise that NeuralScreen exists to
# clean up. A clip with no artefacts measures the pass on content that has nothing wrong with it.
#
#     tools/make_test_clip.sh                       # /opt/neuralscreen/clip-1440p.mp4, 30 s
#     tools/make_test_clip.sh /tmp/c.mp4 10         # somewhere else, shorter
#
# Then replay it, which needs no compositor, no browser and no portal dialog:
#
#     ./neuralscreen.sh --source video --input-video /opt/neuralscreen/clip-1440p.mp4
#
# To use your own footage instead - the GeForce Now window, which is the real thing - record it
# once and replay it forever:
#
#     wf-recorder -f /opt/neuralscreen/clip-1440p.mp4 -c libx264 -p crf=30 -g "$(slurp)"
#
# and keep the encoder's artefacts: the pass is measured on what a stream actually looks like.
set -euo pipefail

OUT=${1:-/opt/neuralscreen/clip-1440p.mp4}
SECONDS_LEN=${2:-30}
W=${CLIP_WIDTH:-2560}
H=${CLIP_HEIGHT:-1440}
FPS=${CLIP_FPS:-30}
CRF=${CLIP_CRF:-32}          # not a quality choice: this is what puts the artefacts in

command -v ffmpeg >/dev/null || { echo "ffmpeg is required" >&2; exit 1; }

mkdir -p "$(dirname "$OUT")"

# testsrc2 rather than testsrc: it has gradients and moving colour structure, so the encoder has
# something to spend bits on and the artefacts land where detail is, which is where the pass acts.
ffmpeg -v error -y \
    -f lavfi -i "testsrc2=size=${W}x${H}:rate=${FPS}:duration=${SECONDS_LEN}" \
    -c:v libx264 -preset veryfast -crf "$CRF" -pix_fmt yuv420p -g "$((FPS * 2))" \
    -movflags +faststart \
    "$OUT"

printf 'wrote %s  %sx%s %s fps %ss crf %s  %s\n' \
    "$OUT" "$W" "$H" "$FPS" "$SECONDS_LEN" "$CRF" "$(du -h "$OUT" | cut -f1)"
echo "replay:  ./neuralscreen.sh --source video --input-video $OUT"
