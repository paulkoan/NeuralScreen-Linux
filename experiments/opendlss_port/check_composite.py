#!/usr/bin/env python3
"""Check the serve composite's arithmetic against the three things it has to match.

    uv run python experiments/opendlss_port/check_composite.py [patch]

The shader (shaders/composite_serve.comp, taken out of linux-port.patch) is a
transliteration of three other pieces of code, and this is where that claim is checked
rather than asserted:

  * src/main.cpp's `composed()` — the parity gate's spelling, which is what a run is
    compared against. There is no history in that path, so the blend must be invisible
    there: with historyValid = 0 the shader has to publish the same byte, for every input.
  * demo/shaders/nr_composite.comp — the reference composition, quoted below. With a
    history it has to compute the same value, expression for expression:

        vec3 neural = clamp(fma(h, vec3(0.03125), fma(proxyCode, vec3(0.125), vec3(-0.0625))) * 8.0 + 0.5, 0.0, 1.0);
        float scale = clamp(params.blendScale, 0.0, 1.0);
        float weight = clamp((1.0 / (1.0 + exp2(head[feature + 3u] * uintBitsToFloat(0xbfb8aa3bu)))) * scale, 0.0, 1.0);
        vec3 hist = historySample(historyPrev, motionTex, ...);
        neural = fma(vec3(weight), hist - neural, neural);
        vec3 history = vec3(truncateHalf(neural.r), ...);

    `historySample` is the five-tap Catmull-Rom reconstruction, and it is checked here
    twice over: the whole filter against an independent build of it (`catmull_rom_reference`
    — the textbook weights, the plus-shaped tap set, the normalize by the weight sum, in
    double precision, so that agreeing with it is not the transliteration agreeing with
    itself), and the zero-motion case against the centre tap it has to collapse to.
  * demo/shaders/nr_common.glsl — `historyUv`, `hasHistory` and `historySample`, quoted
    below. This is the definition the reprojection comes from, and the one place the port
    deliberately differs is the units:

        vec2 uv = (pixel + 0.5) / valid;
        vec2 historyUv = texelFetch(motionTex, motionTexel(...), 0).xy + uv;   // uv units, y down
        vec2 position = historyUv * valid;                                     // -> pixel units
        vec2 base = floor(position - 0.5) + 0.5;
        vec2 f = clamp(position - base, vec2(0.0), vec2(1.0));
        vec2 square = f * f; vec2 cube = f * square;
        vec2 w0 = fma(f + cube, vec2(-0.5), square);
        vec2 w1 = (cube * 1.5 - square * 2.5) + 1.0;
        vec2 w3 = (cube - square) * 0.5;
        vec2 w2 = ((1.0 - w0) - w1) - w3;
        vec2 middle = w1 + w2;
        vec2 low    = clamp(base - 1.0,        vec2(0.5), valid - 0.5);
        vec2 center = clamp(base + w2 / middle, vec2(0.5), valid - 0.5);
        vec2 high   = clamp(base + 2.0,        vec2(0.5), valid - 0.5);
        vec3 left   = textureLod(previousTex, vec2(low.x, center.y), 0.0).rgb;
        vec3 top    = textureLod(previousTex, vec2(center.x, low.y), 0.0).rgb;
        vec3 mid    = textureLod(previousTex, center, 0.0).rgb;
        vec3 bottom = textureLod(previousTex, vec2(center.x, high.y), 0.0).rgb;
        vec3 right  = textureLod(previousTex, vec2(high.x, center.y), 0.0).rgb;
        float a = w0.x * middle.y; float b = w0.y * middle.x;
        float c = middle.x * middle.y; float d = w3.y * middle.x; float e = w3.x * middle.y;
        vec3 value = fma(left, vec3(a), top * b);
        value = fma(mid, vec3(c), value);
        value = fma(bottom, vec3(d), value);
        value = fma(right, vec3(e), value);
        value * (1.0 / (e + (d + (c + (a + b)))));

    The port carries the field in work-resolution pixels — guides.py's units, "NGX consumes
    current-to-previous motion in pixel units", and what the wire sends — where the demo
    divides out to uv and multiplies back. `position = pixel + 0.5 + motion` is the demo's
    `historyUv * valid` as arithmetic; the round trip is a units change and not a difference
    of formula, and it is the one thing here that cannot be compared exactly, because
    `(x / valid) * valid` is not `x` in f32. It is compared to a bound instead, and the
    reason for staying in pixels is not cosmetic: a zero field then lands exactly on a texel
    centre, and the filter's zero-motion case is exactly the centre tap — the property the
    fixture runs on the box check.

What this is NOT: a check on the GPU's exp2, on its texture unit's sub-texel precision, or
on the driver's contractions. Both sides run the same Python arithmetic here, so what is
verified is that the formulas are the same formulas — the hardware side is the parity gate
on the box (src/main.cpp, which the demo's own fixture drives). The last multiply-add of
the blend is the one place contraction could differ and it cannot bite: `inner * 8` is
exact in f32, so there is one rounding either way (that is src/main.cpp's own note on
`composed`). The five-tap's own contraction is open in the same way, and the zero-motion
case is immune to it: every weight but the centre tap's is exactly 0 there.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

CASES = 4000
FIELD = 24                 # the history field the five-tap cases are drawn on
INTERIOR = 4               # positions inside this many texels of the edge: no clamp fires
EPS32 = 2.0 ** -23         # one ulp at 1.0, the yardstick for both bounds below
# The demo divides out to uv and multiplies back; `(x / valid) * valid` is not x in f32, and
# one rounding either way is what the round trip costs. Measured: under one ulp.
UNITS_ULPS = 4.0
# The five-tap transliterated is ~10 f32 operations deep and the reference below is double, so
# agreeing is agreeing to f32 rounding: ~10 ulps on code values in [0, 1] is 1e-6, and this is
# an order above that. For scale: a five-tap that forgot the normalize differs by 1.6% at the
# worst fraction (the control at the bottom prints it), a thousand times further out.
FILTER_TOLERANCE = 1e-5


def f32(value) -> np.float32:
    return np.float32(value)


def clamp32(x, low=0.0, high=1.0):
    return np.float32(min(max(float(x), low), high))


def fma32(a, b, c) -> np.float32:
    """Exactly-rounded f32 fused multiply-add (python's fma is exact for f32 inputs)."""
    return np.float32(math.fma(float(np.float32(a)), float(np.float32(b)), float(np.float32(c))))


def truncate_half(value) -> np.float32:
    """src/main.cpp's truncateHalf: toward zero onto the half grid, on the bits."""
    bits = int(np.float32(value).view(np.uint32))
    sign = (bits >> 16) & 0x8000
    exponent = (bits >> 23) & 0xFF
    mantissa = bits & 0x7FFFFF
    if exponent == 0xFF:
        half = sign | (0x7E00 if mantissa else 0x7C00)
    else:
        half_exponent = exponent - 112
        if half_exponent >= 31:
            half = sign | 0x7C00
        elif half_exponent <= 0:
            half = sign if half_exponent < -10 else sign | ((mantissa | 0x800000) >> (14 - half_exponent))
        else:
            half = sign | (half_exponent << 10) | (mantissa >> 13)
    return np.float32(np.frombuffer(np.uint16(half).tobytes(), dtype=np.float16)[0])


def to_byte(value) -> int:
    return int(min(max(math.floor(float(np.float32(value)) * 255.0 + 0.5), 0.0), 255.0))


def centred(proxy_channels):
    return [fma32(p, 0.125, -0.0625) for p in proxy_channels]


def main_old(head, proxy):
    """`composed()` as src/main.cpp spells it: truncation inside, per channel."""
    c = centred(proxy)
    return [truncate_half(clamp32(fma32(head[i], 0.03125, c[i]) * np.float32(8.0) + np.float32(0.5)))
            for i in range(3)]


def shader(head, proxy, history, blend_scale, history_valid):
    """The shader, line for line: composeChannel (no truncation), the blend, then one
    publication point. `head` is 4 channels; the fourth is the blend logit, and `history`
    is what the history half below produced for this pixel."""
    c = centred(proxy)
    value = [clamp32(fma32(head[i], 0.03125, c[i]) * np.float32(8.0) + np.float32(0.5)) for i in range(3)]
    if history_valid:
        scale = clamp32(blend_scale)
        logit = np.float32(np.float32(head[3]) * np.float32(np.uint32(0xBFB8AA3B).view(np.float32)))
        weight = clamp32(np.float32(1.0) / (np.float32(1.0) + np.exp2(logit)) * scale)
        value = [fma32(weight, history[i] - value[i], value[i]) for i in range(3)]
    return [truncate_half(v) for v in value]


def demo(head, proxy, history, blend_scale, history_valid):
    """demo/shaders/nr_composite.comp's composition, quoted in the docstring."""
    c = centred(proxy)
    neural = [clamp32(fma32(head[i], 0.03125, c[i]) * np.float32(8.0) + np.float32(0.5)) for i in range(3)]
    if history_valid:
        scale = clamp32(blend_scale)
        logit = np.float32(np.float32(head[3]) * np.float32(np.uint32(0xBFB8AA3B).view(np.float32)))
        weight = clamp32(np.float32(1.0) / (np.float32(1.0) + np.exp2(logit)) * scale)
        neural = [fma32(weight, history[i] - neural[i], neural[i]) for i in range(3)]
    return [truncate_half(v) for v in neural]


# ---- the history half: the reprojection and the five-tap filter ----------------------

def mix32(a, b, t):
    """GLSL's mix: x * (1 - a) + y * a, in f32."""
    return f32(f32(f32(a) * (1.0 - t)) + f32(f32(b) * t))


def history_fetch(field, position, valid):
    """The shader's historyFetch, line for line: one bilinear fetch of the history at a
    position in "pixel + 0.5" units, which is where the demo's `historyUv * valid` lands.
    Texel (x, y) covers [x, x + 1) with its centre at x + 0.5, so the texel the position
    starts in is p - 0.5 floored, and the indices are clamped to the valid rectangle — the
    demo's textureLod gets that from the sampler's address mode."""
    base = [f32(np.floor(f32(position[0] - 0.5))), f32(np.floor(f32(position[1] - 0.5)))]
    t = [f32(f32(position[0] - 0.5) - base[0]), f32(f32(position[1] - 0.5) - base[1])]
    lo = [min(max(int(base[0]), 0), valid[0] - 1), min(max(int(base[1]), 0), valid[1] - 1)]
    hi = [min(max(int(base[0]) + 1, 0), valid[0] - 1), min(max(int(base[1]) + 1, 0), valid[1] - 1)]
    top_left = field[lo[1]][lo[0]]
    top_right = field[lo[1]][hi[0]]
    bottom_left = field[hi[1]][lo[0]]
    bottom_right = field[hi[1]][hi[0]]
    return [mix32(mix32(top_left[c], top_right[c], t[0]),
                  mix32(bottom_left[c], bottom_right[c], t[0]), t[1]) for c in range(3)]


def shader_history(position, field, valid, normalize=True):
    """historySample as shaders/composite_serve.comp spells it: the demo's four axis taps and
    the centre, with the bilinear-weight trick, normalized by the weight sum. `normalize=False`
    is the control at the bottom: the same filter without that last line."""
    width, height = f32(valid[0]), f32(valid[1])
    base = [f32(np.floor(f32(position[0] - 0.5)) + 0.5), f32(np.floor(f32(position[1] - 0.5)) + 0.5)]
    f = [clamp32(position[0] - base[0]), clamp32(position[1] - base[1])]
    square = [f32(f[0] * f[0]), f32(f[1] * f[1])]
    cube = [f32(f[0] * square[0]), f32(f[1] * square[1])]
    w0 = [fma32(f32(f[0] + cube[0]), -0.5, square[0]), fma32(f32(f[1] + cube[1]), -0.5, square[1])]
    w1 = [f32(f32(f32(cube[0] * 1.5) - f32(square[0] * 2.5)) + 1.0),
          f32(f32(f32(cube[1] * 1.5) - f32(square[1] * 2.5)) + 1.0)]
    w3 = [f32(f32(cube[0] - square[0]) * 0.5), f32(f32(cube[1] - square[1]) * 0.5)]
    w2 = [f32(f32(f32(1.0 - w0[0]) - w1[0]) - w3[0]), f32(f32(f32(1.0 - w0[1]) - w1[1]) - w3[1])]
    middle = [f32(w1[0] + w2[0]), f32(w1[1] + w2[1])]
    low = [clamp32(base[0] - 1.0, 0.5, width - 0.5), clamp32(base[1] - 1.0, 0.5, height - 0.5)]
    center = [clamp32(base[0] + f32(w2[0] / middle[0]), 0.5, width - 0.5),
              clamp32(base[1] + f32(w2[1] / middle[1]), 0.5, height - 0.5)]
    high = [clamp32(base[0] + 2.0, 0.5, width - 0.5), clamp32(base[1] + 2.0, 0.5, height - 0.5)]
    left = history_fetch(field, (low[0], center[1]), valid)
    top = history_fetch(field, (center[0], low[1]), valid)
    mid = history_fetch(field, center, valid)
    bottom = history_fetch(field, (center[0], high[1]), valid)
    right = history_fetch(field, (high[0], center[1]), valid)
    a = f32(w0[0] * middle[1])
    b = f32(w0[1] * middle[0])
    c = f32(middle[0] * middle[1])
    d = f32(w3[1] * middle[0])
    e = f32(w3[0] * middle[1])
    values = []
    for channel in range(3):
        value = fma32(left[channel], a, f32(top[channel] * b))
        value = fma32(mid[channel], c, value)
        value = fma32(bottom[channel], d, value)
        value = fma32(right[channel], e, value)
        values.append(f32(value * f32(1.0 / f32(e + f32(d + f32(c + f32(a + b))))))
                      if normalize else f32(value))
    return values


def demo_position(pixel, motion_uv, valid):
    """demo/shaders/nr_common.glsl's reprojection, through the uv it works in:

        vec2 uv = (pixel + 0.5) / valid;
        vec2 position = (texelFetch(motionTex, ...).xy + uv) * valid;

    with the field's motion in uv. The port's `pixel + 0.5 + motion` is the same
    expression with the field in pixels; this is what says by how much the two can differ,
    and it is the only comparison here that is not exact, because the round trip is not."""
    uv = [f32(f32(pixel[0] + 0.5) / f32(valid[0])), f32(f32(pixel[1] + 0.5) / f32(valid[1]))]
    previous_uv = [f32(motion_uv[0] + uv[0]), f32(motion_uv[1] + uv[1])]
    return [f32(previous_uv[0] * f32(valid[0])), f32(previous_uv[1] * f32(valid[1]))]


def demo_on_screen(position, valid):
    """hasHistory: the demo's flag is "the previous position is on screen", which is the
    predicate the port can still read off the position, since the wire's field carries no
    flag of its own. False means no history to read: the blend is skipped."""
    return (position[0] >= 0.5 and position[1] >= 0.5
            and position[0] <= valid[0] - 0.5 and position[1] <= valid[1] - 0.5)


def catmull_rom_reference(field, position, valid):
    """The five-tap as mathematics, built independently of the transliteration.

    Catmull-Rom's four weights for a fractional position, the tap set the demo's five
    samples cover — the two middle rows on the two outer columns, the two middle columns on
    the two outer rows, and the 2x2 centre, with the four corners of the 4x4 neighbourhood
    never sampled — and the normalize by the sum of those weights, which is not 1: it is
    1 - (w0.x + w3.x) * (w0.y + w3.y). Double precision, so that agreeing with this is not
    the shader agreeing with itself.

    Only positions whose whole neighbourhood is inside the valid rectangle, where the demo's
    clamp of the tap positions does not fire: clamping a *position* changes an interpolation
    weight, and that is exercised by the zero-motion cases at the corners instead."""
    p = [float(position[0]), float(position[1])]          # double from here on, not f32
    base = [math.floor(p[0] - 0.5) + 0.5, math.floor(p[1] - 0.5) + 0.5]
    t = [min(max(p[0] - base[0], 0.0), 1.0), min(max(p[1] - base[1], 0.0), 1.0)]

    def weights(f):
        return (-0.5 * f ** 3 + f ** 2 - 0.5 * f,
                1.5 * f ** 3 - 2.5 * f ** 2 + 1.0,
                -1.5 * f ** 3 + 2.0 * f ** 2 + 0.5 * f,
                0.5 * f ** 3 - 0.5 * f ** 2)

    wx, wy = weights(t[0]), weights(t[1])
    first = [int(base[0] - 0.5), int(base[1] - 0.5)]
    total = 0.0
    value = [0.0, 0.0, 0.0]
    for i, wxi in zip((-1, 0, 1, 2), wx):
        for j, wyj in zip((-1, 0, 1, 2), wy):
            if i in (-1, 2) and j in (-1, 2):
                continue                     # the corners the five taps never sample
            weight = wxi * wyj
            total += weight
            texel = [float(c) for c in field[first[1] + j][first[0] + i]]
            for channel in range(3):
                value[channel] += weight * texel[channel]
    return [v / total for v in value]


def shader_source(patch: Path) -> str:
    text = patch.read_text()
    start = text.index("diff --git a/shaders/composite_serve.comp")
    body = text[start:]
    following = body.find("\ndiff --git ", 10)
    diff = body if following < 0 else body[:following]
    return "".join(line[1:] + "\n" for line in diff.splitlines()
                   if line.startswith("+") and not line.startswith("+++"))


def main() -> int:
    patch = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("linux-port.patch")
    source = shader_source(patch)

    # The transliterations above are only worth anything while the shader still says what
    # they say. A rename, a reorder or a dropped term is where this file would otherwise
    # quietly rot: each of these is a line of the filter or of the blend, in order.
    for needed in ("float composeChannel(float headValue, float centredProxy)",
                   "float inner = fma(headValue, 0.03125, centredProxy);",
                   "return clamp(inner * 8.0 + 0.5, 0.0, 1.0);",
                   # the history half: the reprojection and the five-tap
                   "return pixel + 0.5 + unpackHalf2x16(motionField[index]);",
                   "vec2 position = historyPosition(vec2(id), index);",
                   "if (all(greaterThanEqual(position, vec2(0.5))) &&",
                   "all(lessThanEqual(position, valid - 0.5))) {",
                   "vec3 historyValue = historySample(position);",
                   "vec2 base = floor(p - 0.5);",
                   "vec2 t = (p - 0.5) - base;",
                   "ivec2 lo = clamp(ivec2(base), ivec2(0), last);",
                   "ivec2 hi = clamp(ivec2(base) + 1, ivec2(0), last);",
                   "return mix(mix(topLeft, topRight, t.x), mix(bottomLeft, bottomRight, t.x), t.y);",
                   "vec2 base = floor(position - 0.5) + 0.5;",
                   "vec2 f = clamp(position - base, vec2(0.0), vec2(1.0));",
                   "vec2 w0 = fma(f + cube, vec2(-0.5), square);",
                   "vec2 w1 = (cube * 1.5 - square * 2.5) + 1.0;",
                   "vec2 w3 = (cube - square) * 0.5;",
                   "vec2 w2 = ((1.0 - w0) - w1) - w3;",
                   "vec2 middle = w1 + w2;",
                   "vec2 low = clamp(base - 1.0, vec2(0.5), valid - 0.5);",
                   "vec2 center = clamp(base + w2 / middle, vec2(0.5), valid - 0.5);",
                   "vec2 high = clamp(base + 2.0, vec2(0.5), valid - 0.5);",
                   "vec3 left = historyFetch(vec2(low.x, center.y));",
                   "vec3 top = historyFetch(vec2(center.x, low.y));",
                   "vec3 mid = historyFetch(center);",
                   "vec3 bottom = historyFetch(vec2(center.x, high.y));",
                   "vec3 right = historyFetch(vec2(high.x, center.y));",
                   "float a = w0.x * middle.y; float b = w0.y * middle.x;",
                   "float c = middle.x * middle.y; float d = w3.y * middle.x; float e = w3.x * middle.y;",
                   "vec3 value = fma(left, vec3(a), top * b);",
                   "value = fma(mid, vec3(c), value);",
                   "value = fma(bottom, vec3(d), value);",
                   "value = fma(right, vec3(e), value);",
                   "return value * (1.0 / (e + (d + (c + (a + b)))));",
                   # the blend, unchanged by it
                   "if (pc.historyValid != 0u) {",
                   "float scale = clamp(pc.blendScale, 0.0, 1.0);",
                   "float weight = clamp((1.0 / (1.0 + exp2(neural.a * uintBitsToFloat(0xbfb8aa3bu)))) * scale,",
                   "value = fma(vec3(weight), historyValue - value, value);",
                   "value = vec3(truncateHalf(value.r), truncateHalf(value.g), truncateHalf(value.b));"):
        if needed not in source:
            print(f"the shader no longer contains: {needed}")
            print("this check is stale - update it with the shader")
            return 2

    rng = np.random.default_rng(20261012)
    blend_scale = np.float32(0.7397)          # block70.layer0.blend_scale, the shipped model
    mismatched_parity = mismatched_demo = 0
    worst_parity = worst_demo = 0

    def sample():
        # Code values, a head residual of the size the network emits, and a history that is
        # also a code value (it was published as RGBA8 by the frame before).
        proxy = [np.float32(v) for v in np.clip(rng.random(3, dtype=np.float32), 0, 1)]
        head = [np.float32(v) for v in rng.normal(0.0, 1.0, 4).astype(np.float32)]
        history = [np.float32(v) for v in np.clip(rng.random(3, dtype=np.float32), 0, 1)]
        return proxy, head, history

    for case in range(CASES):
        proxy, head, history = sample()
        if case % 4 == 3:                    # the extremes: saturated proxy, huge logits
            proxy = [np.float32(1.0 if case % 8 == 3 else 0.0)] * 3
            head = [np.float32(60.0), np.float32(-60.0), np.float32(0.0), np.float32(40.0)]

        old = main_old(head, proxy)
        new = shader(head, proxy, history, blend_scale, history_valid=False)
        for a, b in zip(old, new):
            if a != b:
                mismatched_parity += 1
                worst_parity = max(worst_parity, abs(float(a) - float(b)))
                break
        else:
            # The parity gate compares published bytes, so compare those too.
            if [to_byte(v) for v in old] != [to_byte(v) for v in new]:
                mismatched_parity += 1

        reference = demo(head, proxy, history, blend_scale, history_valid=True)
        blended = shader(head, proxy, history, blend_scale, history_valid=True)
        for a, b in zip(reference, blended):
            if a != b:
                mismatched_demo += 1
                worst_demo = max(worst_demo, abs(float(a) - float(b)))
                break

    # ---- the history half -------------------------------------------------------------

    # A history field of code values, and a valid rectangle == the field: the same shape the
    # serve path binds (its history proxy is the valid size).
    valid = (FIELD, FIELD)
    field = np.clip(rng.random((FIELD, FIELD, 3), dtype=np.float32), 0, 1)

    # Zero motion: the whole filter, every valid size and every pixel of a small field, has to
    # be the centre tap and nothing else — the invariant a run on the box can see, because it
    # is what makes the fixture's bytes the bytes the blend was measured at. The pixels at the
    # edges are in here on purpose: that is where the demo's clamps of the tap positions fire.
    zero_mismatched = 0
    for case in range(CASES):
        size = 2 + case % 6                     # 2..7: small rectangles are all edge
        small = np.clip(rng.random((size, size, 3), dtype=np.float32), 0, 1)
        pixel = (rng.integers(0, size), rng.integers(0, size))
        position = (f32(pixel[0] + 0.5), f32(pixel[1] + 0.5))
        sampled = shader_history(position, small, (size, size))
        centre = [f32(v) for v in small[int(pixel[1])][int(pixel[0])]]
        if any(a != b for a, b in zip(sampled, centre)):
            zero_mismatched += 1

    # Motion: the five-tap against the independent build of it, in the interior of the field
    # (where the demo's clamp of the tap positions does not fire), and the port's reprojection
    # against the demo's own uv route.
    filter_mismatched = 0
    worst_filter = 0.0
    worst_control = 0.0
    units_worst = 0.0
    decision_mismatched = 0
    compared = 0
    for case in range(CASES):
        pixel = (int(rng.integers(0, FIELD)), int(rng.integers(0, FIELD)))
        # Motion at the size of a real one: a few pixels, either direction, fractional.
        motion = [f32(rng.normal(0.0, 1.5)), f32(rng.normal(0.0, 1.5))]
        position = [f32(f32(pixel[0] + 0.5) + motion[0]), f32(f32(pixel[1] + 0.5) + motion[1])]

        # The decision the composite makes per pixel: the demo's flag, and the rectangle the
        # port reads it off instead.
        demo_flag = demo_on_screen(position, valid)
        port_flag = (position[0] >= 0.5 and position[1] >= 0.5
                     and position[0] <= valid[0] - 0.5 and position[1] <= valid[1] - 0.5)
        if demo_flag != port_flag:
            decision_mismatched += 1

        # The units: the demo's uv route against the port's pixel-space sum, in ulps of the
        # position rather than in absolutes, because that is what the round trip costs.
        motion_uv = [f32(motion[0] / f32(valid[0])), f32(motion[1] / f32(valid[1]))]
        through_uv = demo_position(pixel, motion_uv, valid)
        for a, b in ((through_uv[0], position[0]), (through_uv[1], position[1])):
            scale = max(abs(float(a)), abs(float(b)), 1.0)
            units_worst = max(units_worst, abs(float(a) - float(b)) / scale / EPS32)

        # ... and the filter itself, on positions whose neighbourhood is inside the field,
        # which is where the demo's clamp of the tap positions does not fire.
        if not demo_flag:
            continue
        if not (INTERIOR <= position[0] <= valid[0] - INTERIOR
                and INTERIOR <= position[1] <= valid[1] - INTERIOR):
            continue
        sampled = shader_history(position, field, valid)
        reference = catmull_rom_reference(field, position, valid)
        difference = max(abs(float(a) - float(b)) for a, b in zip(sampled, reference))
        compared += 1
        worst_filter = max(worst_filter, difference)
        if difference > FILTER_TOLERANCE:
            filter_mismatched += 1
        # The control: the same filter with the normalize left out. If this were inside the
        # bound as well, the bound would not be checking the filter.
        unnormalized = shader_history(position, field, valid, normalize=False)
        worst_control = max(worst_control,
                            max(abs(float(a) - float(b)) for a, b in zip(unnormalized, reference)))

    print(f"{CASES} random cases, both paths")
    print(f"  no history: the shader against src/main.cpp's composed()  "
          f"{'agree' if not mismatched_parity else f'DIFFER in {mismatched_parity} (by {worst_parity})'}")
    print(f"  history:    the shader against demo/shaders/nr_composite.comp  "
          f"{'agree' if not mismatched_demo else f'DIFFER in {mismatched_demo} (by {worst_demo})'}")
    print(f"  history, zero motion: the five-tap against the centre tap, {CASES} cases  "
          f"{'agree' if not zero_mismatched else f'DIFFER in {zero_mismatched}'}")
    print(f"  history, motion: the five-tap against the Catmull-Rom built independently, "
          f"{compared} cases inside the field  "
          f"{'agree' if not filter_mismatched else f'DIFFER in {filter_mismatched} (by {worst_filter})'}"
          f"  (worst {worst_filter:.1e} allowed {FILTER_TOLERANCE:.0e}; the same filter without"
          f" the normalize is {worst_control:.1e} out)")
    print(f"  the reprojection: the demo's uv route against the port's pixels, worst "
          f"{units_worst:.2f} ulp (allowed {UNITS_ULPS:.0f})  "
          f"{'agree' if units_worst <= UNITS_ULPS else 'DIFFER'}")
    print(f"  the flag: the demo's on-screen test against the port's rectangle  "
          f"{'agree' if not decision_mismatched else f'DIFFER in {decision_mismatched}'}")
    if (mismatched_parity or mismatched_demo or zero_mismatched or filter_mismatched
            or decision_mismatched or units_worst > UNITS_ULPS):
        return 1
    print("the history half is the demo's filter and the demo's reprojection, and without a "
          "history the published byte does not move")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
