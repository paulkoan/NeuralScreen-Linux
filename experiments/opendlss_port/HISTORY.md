# The demo's reprojection and its five-tap Catmull-Rom history filter

`serve`'s composite samples the history at the pixel itself, and the patch's own header says why:
"this path is handed no motion, so the reprojection is the identity". That is only honest while the
demo's reprojection and filter **reduce to that** when the motion field is zero. This file is the
definition, taken from the original rather than reinvented, and
`check_history_sample.py` is where the arithmetic is checked rather than asserted.

## Where it comes from

OpenDLSS-NR (MIT), `github.com/maanHimself/OpenDLSS-NR`, at **9d08f41** — the commit the port's own
stamp names (`stamp: port 9d08f41 (12 modified)`). Read from a clone of it; the port's single commit
touches `shaders/`, `src/` and `scripts/` only, so everything below is untouched by the port:

| what | where | sha256 (of the file as read) |
|---|---|---|
| the reprojection and the filter | `demo/shaders/nr_common.glsl`, lines 72-117 | `0169c580bc56b8af…` |
| what the motion texture holds | `demo/shaders/velocity_unpack.comp`, lines 1-28 | `58dd5013a67779eb…` |
| the call sites | `demo/shaders/nr_composite.comp` lines 179-183, `demo/shaders/nr_preprocess.comp` lines 57-62 | `faca7518816dd325…` |
| the original's own prose | `docs/frame.md` §"Motion vectors", §"History reconstruction", §"Composition" | — |
| the host facts used below | `demo/nr_pass.cpp` lines 48, 124-126, 329 | — |

`check_history_sample.py` pins the three sha256s, refuses (exit 2) if any of them — or the lines it
transliterates — has moved, and reads the definition out of a checkout (`argv[1]`, `NS_ODL_SRC`,
`/opt/neuralscreen/port`, `~/dev/OpenDLSS-NR`, `/opt/data/tmp/odl-src`).

## 1. The motion texture

The renderer's velocity buffer is `rgba32ui` `(object id, depth bits, motion x, motion y)` with
motion = **previous NDC − current NDC, y up**. `velocity_unpack.comp` turns that into the NR motion
texture `rgba16f`:

```glsl
vec2 ndc = vec2((float(id.x) + 0.5) / float(push.width) * 2.0 - 1.0,
                1.0 - (float(id.y) + 0.5) / float(push.height) * 2.0);   // y up: row 0 is the top
vec2 m = vec2(uintBitsToFloat(v.z), uintBitsToFloat(v.w));
if (!drawn || uintBitsToFloat(v.y) == 0.0)
  m = push.background * vec4(ndc, 0.5, 1.0) ... - ndc;   // nothing drawn / depth 0: a point at
                                                          // infinity, the camera's rotation only
bool onScreen = all(lessThan(abs(ndc + m), vec2(1.0)));
imageStore(motion, ivec2(id), onScreen ? vec4(0.5 * vec2(m.x, -m.y), 1.0, 0.0) : vec4(0.0));
```

So, in the motion texture:

* **`xy` = the current→previous displacement in uv of the render target**, y down as texture rows
  are. The `0.5` converts an NDC delta (range 2) to a uv delta (range 1) — what the comment above
  `historyUv` means by "already in uv units of the render target" — and the y is negated to go from
  NDC's y up to rows' y down. In **pixel units of the valid rectangle the offset is
  `motion.xy * (validWidth, validHeight)`**; that is the conversion an implementation keeping the
  field in pixels has to make.
* **`z` = 1 where the previous position is on screen**, i.e. the previous frame holds a history for
  this pixel, **0 where it is off screen** and there is none. `hasHistory` is `z > 0.5`.
* Off screen, the whole texel is zeroed — the zeros **and** the flag together — so a pixel with no
  history can never be handed a stale motion (verified: checks 4).
* The flag is not redundant with zero motion, and the original says so in `docs/frame.md`: zero
  motion means "the history is at this same pixel", which is a claim, and it cannot also stand for
  "there is none". An implementation whose field has no flag channel has to substitute something
  else for it (the valid-rectangle test is the one case that is readable from the position alone);
  that is a behavioural difference, not an arithmetic one.
* The texture is `rgba16f`, so the stored delta is quantised to f16: a uv delta of 0.5 steps by
  4.88e-04 uv (0.70 px at 1440 width), of 1.0 by 9.77e-04 (1.41 px) — the original's own precision,
  reported by the check rather than assumed.

## 2. The reprojection

```glsl
ivec2 motionTexel(sampler2D motionTex, vec2 pixel, vec2 valid) {
  ivec2 size = textureSize(motionTex, 0);
  return min(ivec2((pixel + 0.5) / valid * vec2(size)), size - 1);
}
vec2 historyUv(sampler2D motionTex, vec2 pixel, vec2 valid) {
  vec2 uv = (pixel + 0.5) / valid;
  return texelFetch(motionTex, motionTexel(motionTex, pixel, valid), 0).xy + uv;
}
bool hasHistory(sampler2D motionTex, vec2 pixel, vec2 valid) {
  return texelFetch(motionTex, motionTexel(motionTex, pixel, valid), 0).z > 0.5;
}
```

* `pixel` is a **pixel index**, not a centre: the `+ 0.5` is applied inside, so `uv` is the pixel's
  centre in uv and `uv + motion.xy` is where that centre was last frame, in uv (verified: checks 4,
  `uv + motion.xy` maps back to `ndc + m` to 2.2e-16).
* `motionTexel` is a nearest-texel lookup with the index clamped to the texture; with the motion
  texture at the render target's size — which is how the demo builds it, `nr_pass.cpp` line 124 —
  it is the pixel's own texel, exactly.
* The history surface is the valid rectangle's size too (`nr_pass.cpp`: `createImage(width, height,
  rgba16f)` for both `history_[2]` images, and `block.validWidth = width_`), so `valid` is at once
  the rectangle and the texture extent, and the clamp in the filter below is the texture's own edge.

## 3. The five-tap filter

```glsl
vec3 historySample(sampler2D previousTex, sampler2D motionTex, vec2 pixel, vec2 valid) {
  vec2 position = historyUv(motionTex, pixel, valid) * valid;      // uv -> "pixel + 0.5" units
  vec2 base = floor(position - 0.5) + 0.5;                         // the containing texel's centre
  vec2 f = clamp(position - base, vec2(0.0), vec2(1.0));           // the fractional offset
  vec2 square = f * f; vec2 cube = f * square;
  vec2 w0 = fma(f + cube, vec2(-0.5), square);
  vec2 w1 = (cube * 1.5 - square * 2.5) + 1.0;
  vec2 w3 = (cube - square) * 0.5;
  vec2 w2 = ((1.0 - w0) - w1) - w3;                                // the residual: the four sum to 1
  vec2 middle = w1 + w2;
  vec2 low = clamp(base - 1.0, vec2(0.5), valid - 0.5) / valid;
  vec2 center = clamp(base + w2 / middle, vec2(0.5), valid - 0.5) / valid;
  vec2 high = clamp(base + 2.0, vec2(0.5), valid - 0.5) / valid;
  vec3 left = textureLod(previousTex, vec2(low.x, center.y), 0.0).rgb;
  vec3 top = textureLod(previousTex, vec2(center.x, low.y), 0.0).rgb;
  vec3 mid = textureLod(previousTex, center, 0.0).rgb;
  vec3 bottom = textureLod(previousTex, vec2(center.x, high.y), 0.0).rgb;
  vec3 right = textureLod(previousTex, vec2(high.x, center.y), 0.0).rgb;
  float a = w0.x * middle.y; float b = w0.y * middle.x;
  float c = middle.x * middle.y; float d = w3.y * middle.x; float e = w3.x * middle.y;
  vec3 value = fma(left, vec3(a), top * b);
  value = fma(mid, vec3(c), value);
  value = fma(bottom, vec3(d), value);
  value = fma(right, vec3(e), value);
  return value * (1.0 / (e + (d + (c + (a + b)))));
}
```

Written out, because the shader is the definition and the algebra is what has to be reproduced:

* **The weights** are the uniform Catmull-Rom kernel (a = −0.5) at four offsets, one pair per axis,
  with `f` from the offset of the position inside its texel: `w0 = CR(f + 1)` (the texel at
  `base − 1`), `w1 = CR(f)` (the texel the position starts in), `w2 = CR(1 − f)` (the next one), and
  `w3 = CR(2 − f)` (the one after that), with `w2` spelled as the residual that makes the four sum
  to 1. Verified: within 2.8e-07 of the kernel in f32, sum 1.
* **`middle` = w1 + w2 is the value `base + w2 / middle` is built on**, and it is in
  **[1, 1.125]** over the whole of [0, 1] — so that division cannot be by zero and the sample
  position always lands between the position's own texel and its neighbour (verified).
* **The five taps are a cross**: the four axis neighbours `base ± …` read at the *other* axis's
  interpolated position, plus the centre, which is interpolated on both axes. The sample position of
  each tap is the weighted centroid `base + w2 / middle`, which puts the sampler's own linear
  interpolation weights at `w1 : w2` — that is the "bilinear-weight trick", and it is why the axis
  taps can be single fetches.
* **The coefficients** are `a = w0.x·middle.y` (the left column's two rows together), `b = w0.y·middle.x`
  (the top row's two columns), `c = middle.x·middle.y` (the four central texels), `d = w3.y·middle.x`,
  `e = w3.x·middle.y`. The result is divided by `e + (d + (c + (a + b)))` — the sum of those five
  coefficients, which is `middle.x + middle.y − middle.x·middle.y`, i.e. **the demo leaves the
  normalisation to the expression and not to 1.**
* **What that computes, exactly**: the kernel's twelve terms over the cross — every texel `(base.x + i − 1,
  base.y + j − 1)` whose x *or* y index is in `{1, 2}` — renormalised by their weight sum. Verified
  against those twelve terms read off the texel grid (3000 random fields and offsets, the edges
  included): worst deviation 5.4e-08, which is the weights' own f32 rounding.
* **What it drops**: the four corner texels, where *both* indices are in `{0, 3}`, are outside what
  five taps on the cross can reach. Their weight total is `(|w0.x| + |w3.x|)·(|w0.y| + |w3.y|)`,
  at most **0.0156** (at f = 0.5 in both axes), so the difference from the tensor product of the
  kernel both ways is at most 2 × that of the local range. This is a five-tap filter and not a
  sixteen-tap one; anything expecting an exact bicubic should not be pointed here.
* **The edges**: each tap is clamped into `[0.5, valid − 0.5]` *before* it reaches the sampler, so a
  tap that would fall outside reads the outermost texel centre — CR with edge extension, not wrap
  and not mirror. The clamp also keeps every tap inside the texture, so the sampler's address mode
  cannot change the result (`demo/nr_pass.cpp` sets CLAMP_TO_EDGE anyway). The two effects agree —
  clamping the position and clamping the index are the same thing here, because a tap clamped onto
  an edge lands exactly on a texel centre (verified: the edge cases in check 2).
* **Zero motion, which is the field the fixture sends today**: `motion = 0` gives `position = pixel + 0.5`,
  `base = pixel + 0.5`, `f = 0` exactly, and then `w0 = w2 = w3 = 0`, `w1 = 1`, `a = b = d = e = 0`,
  `c = 1` — so the filter is **the pixel's own texel, bit for bit**, at every pixel of the frame
  (verified). That is the reduction the current patch's comment claims, and it is why
  `check_composite.py`'s history comparison is legitimate with a zero motion field.

## 4. Where it is called

Both passes that use the history sample it the same way, and both guard on the flag:

```glsl
// nr_composite.comp:179-183 — the blend, over the valid rectangle
if (params.historyValid != 0u && hasHistory(motionTex, vec2(id), vec2(params.validWidth, params.validHeight))) {
  ...
  vec3 hist = historySample(historyPrev, motionTex, vec2(id), vec2(params.validWidth, params.validHeight));
  neural = fma(vec3(weight), hist - neural, neural);
}
// nr_preprocess.comp:57-62 — lanes 7-9, at the (reflected) source coordinate, centred like the proxy
vec3 history = centered;
if (params.historyValid != 0u && hasHistory(motionTex, vec2(sourceX, sourceY), vec2(params.validWidth, params.validHeight))) {
  vec3 h = historySample(historyPrev, motionTex, vec2(sourceX, sourceY), vec2(params.validWidth, params.validHeight));
  ...
}
```

Two conditions, and both have to hold: `historyValid` is the reset (and NR-off) knob, and
`hasHistory` is the per-pixel one. With no history the preprocess gives lanes 7-9 the current proxy
and the composite blends with weight 0.

## 5. What `serve` does with it

The port's composite carries both halves now (commit `3f3d63b`, "The history half"):
`shaders/composite_serve.comp` binds the wire's motion field (2 × f16 per pixel, current →
previous, work-resolution pixels, y down) and turns it into `pixel + 0.5 + motion` — the same
quantity as the demo's `historyUv * valid`, without the uv round trip — then samples the history
through `historyFetch` / `historySample`, which are this definition's expression for expression.

Three things to know when reading that side:

* **Where it is checked**: `check_composite.py` transliterates the shipped shader and compares it
  against the demo's, over random motion and a random history field (and refuses, exit 2, if the
  lines it translates have moved). *This* file, with `check_history_sample.py`, is the same
  definition checked from the original alone, with the source's bytes pinned — so a reader who
  wants the definition reads here, and a reader who wants the port's rendering of it reads there.
* **The flag is the wire's missing piece**: the field has no third component, so the port's only
  per-pixel test is whether the reprojected position leaves the valid rectangle, where the demo
  also has `hasHistory` (§1). A pixel uncovered by motion keeps its history there; the demo leaves
  that case to the network's own blend logit (`docs/frame.md`).
* **Lanes 7-9 are still the identity**: `shaders/preprocess.comp` does not reproject or filter,
  where the demo's `nr_preprocess.comp` does exactly what §4 above shows. The port's README names
  that as not done; it is the difference between the blend being motion-compensated and the
  network's temporal input being motion-compensated too.

`check_history_sample.py` reports which state the patch it is pointed at is in, and reads the
patch only for that report: nothing in its arithmetic depends on the implementing change's text.

## 6. Verified, inferred, assumed

* **Verified here, locally, by arithmetic** (see the script's own output for the numbers): the four
  weights are the kernel and sum to 1; `middle` ∈ [1, 1.125]; the five taps equal the kernel's
  twelve terms over the cross, edges included (worst 5.4e-08); zero motion is the pixel's own texel
  bit for bit; `uv + motion.xy` is the previous NDC position with rows' y down (worst 2.2e-16); off
  screen the store zeroes the motion with the flag. The sha256s, and every line quoted above, come
  out of the files as read.
* **Read, not checked by the script**: the host facts — the history images are the valid rectangle's
  size, the sampler is linear + CLAMP_TO_EDGE, the velocity buffer's packing. They are cited by file
  and line above and are what makes the clamp the texture's edge.
* **Inferred, not measured**: that the GPU's own linear interpolation supplies the `w1 : w2` split at
  the centroid. The check emulates bilinear filtering in double precision and establishes the
  algebra; the texture unit's rounding of it (an f32/driver matter, ~1e-7 on code values) is not
  measured here, the same standing `check_composite.py` has for the blend's `exp2`.
* **Not defined here**: where a motion field comes from on the port's side (the capture path), and
  how the port's field units relate to the demo's uv delta beyond the conversion above. The
  definition's requirements of any such field are: current→previous, y down, in units that can be
  converted to pixels or uv of the valid rectangle, and *a flag* distinct from a zero vector.
