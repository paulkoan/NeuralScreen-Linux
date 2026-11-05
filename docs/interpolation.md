# Interpolation, and what the motion field can and cannot do

Two asks, written down because both turn on the same thing: the motion field the client already
computes and sends. One is a feature (generate frames), one is a question (use motion to apply the
pass only to the foreground). The question has a short answer and a real caveat, so it comes first.

## Using motion to find "the foreground"

**Feasible, with three caveats that decide whether it is worth doing.**

The field exists. `guides.py` estimates current-to-previous flow with DIS at 320x180, applies a
0.5 px noise floor, and the port's composite already reprojects the previous published frame
through it (`shaders/composite_serve.comp`, `pixel + 0.5 + motion`, five-tap Catmull-Rom). So a
per-pixel "did this move" signal is available today, at 320x180, for free — it is already on the
wire.

A mask from it is a few lines: `moving = |motion| > threshold`, dilated and blurred so its edges
are not a hard line.

The caveats:

1. **Motion is not foreground.** A static foreground object (a parked car, a menu, an NPC standing
   still) has zero motion; a panning camera gives the *background* a large uniform motion. The
   useful transform is to remove the dominant motion first — take the median vector over the frame
   as the camera's motion, subtract it, and threshold the residual. That is standard ego-motion
   compensation and it is what turns "things that move" into "things that move relative to the
   scene". Without it, a pan marks the whole frame as foreground and a still shot marks nothing.
2. **It does not make the pass cheaper.** The network is fully convolutional and runs on the whole
   frame whatever we do with the result; masking the *output* (`out = mask*enhanced +
   (1-mask)*original`) is cheap and client-side, but the 10.5 ms in the worker is still spent on
   pixels nobody sees. To actually save that time the masking has to happen inside the network —
   tiled or masked convolution — which is a research project, not a flag.

   *Correction, after reading maximedgoulet/FoveatedDLSS5's FOVEATION.md:* "runs on the whole
   frame" is true of the network's single evaluate, but the frame it evaluates need not be at
   output resolution. That project squeezes the whole image into a smaller, non-uniformly sampled
   grid — density 1.0 in a centre zone of output pixels, a smoothstep fall-off, and `Edge` density
   (0.5 by default) beyond it, independently per axis so corners reach Edge×Edge. The network then
   runs **once** on that smaller image with one temporal history, and every stage that maps
   working↔full inverts the warp. At 7680×2160 the grid is 5540×2132 = 71% of the pixels; at
   3840×2160 it is 3620×2132 = 93%. Their own doc says 3440×1440 bypasses the mode because it
   saves under 5%.

   That is a third path, and a cheaper one than masking or tiling: the cost cut comes from the
   input being smaller, and the centre stays 1:1 so the foveal region is untouched. It needs no
   protocol change here — one evaluate, one reply. What it does need is the same resample applied
   to the guides: their `fov_guides` compute pass resamples depth and motion onto the warped grid
   so NR's inputs stay registered. Our motion field is already at 320×180 and upscaled in the
   worker, so resampling it is cheap. The limit for our 1440p 16:9 stream: the gain scales
   with how much edge you give up, and a 3000-px centre does not even fit a 2560-wide frame — a
   smaller centre leaves maybe 20-25% of the network's 10.5 ms on the table, not 50%.
3. **The blend is what would change, and that is a picture decision.** Enhancing only moving
   regions means the HUD, text and static UI keep their stream artefacts while the world gets
   cleaned up. That may look *worse*: the eye compares the two regions directly. It is worth
   testing rather than assuming.

**Cheap experiment worth running before any port work:** render `moving` (with ego-motion
compensation) and save it as a PNG over a few stream frames. If the mask does not clearly pick out
the objects a person would call foreground, the idea dies there for the cost of one run — no port
change needed.

## Interpolation (30 -> 60 presented)

**Where the pipeline is.** Live end-to-end 1440p is 33.8 ms / 29.6 fps: capture 6.5, send 1.5,
worker 23 (network 10.5, proxy 2.5, composite 0.3, readback + reply ~4, rest scheduling), display
3.2. Sixty presented frames a second needs 16.7 ms *per processed frame* if every frame is
processed, which the worker cannot reach — but at 30 processed fps each frame has 33.3 ms, and
33.8 ms is already there. So the shape is: process at ~30, present at ~60.

**What already exists for it.** The composite holds the previous published frame in `History` and
reads it at the reprojected position through the motion field. Generating a mid-frame is the same
fetch at half the motion:

    mid(pixel) = historyFetch(pixel + 0.5 + 0.5 * motion)

That is one dispatch after the composite, reusing buffers that are already bound. The hard part is
not the warp.

**What is missing, in order of difficulty:**

1. **The protocol is one reply per sent frame.** `WorkerReader.recv` waits for the index it sent,
   and the client shows exactly one frame per iteration. Emitting a mid-frame means either two
   replies per index (with a flag saying which is which) or a second output slot. `OUT_FMT` has an
   `ngx_result` field doing nothing on the happy path; a flag there is the smallest change.
2. **The field is too coarse for warping.** 320x180 upscaled to 1440p is fine for temporal
   denoising — it only needs to know roughly where history came from — and visibly wrong for
   frame generation, where the mid-frame's whole content is placed by the vector. Small fast
   objects (a crosshair, a drifting particle) will smear. Options: estimate flow at 720p (DIS
   costs roughly 4x the pixels, so ~+15-30 ms of CPU — too slow), or accept 320x180 and see how it
   looks on real content, or run the flow on the GPU. The last is the right answer eventually and
   the largest piece of work here.
3. **Occlusion and disocclusion.** A pixel that was hidden in the previous frame and is visible in
   the mid-frame has no history to warp from. Without a hole-filling rule the mid-frame shows
   streaks at every moving edge. The composite's `historyValid` flag is the beginning of this
   (`composite_serve.comp`), and the standard cheap answer is to fall back to the current frame's
   un-reprojected pixel where history is invalid — which degrades to "no interpolation here"
   rather than to a streak.
4. **Latency.** Presenting frame N's mid between N-1 and N adds one frame of delay, ~33 ms, on a
   stream that is already network-bound. Whether that is acceptable is a product question, not a
   technical one.

**First step, concrete:** the warp and its protocol flag, measured on the synthetic card where the
motion is known exactly — a 320x180-or-whatever field with a known bar moving at a known rate
makes a wrong warp obvious and a right one checkable, and none of it needs a live capture. If the
warped mid-frame is correct on the card, the remaining questions are quality on real content
(point 2) and latency (point 4), and both are answerable with one live run each.
