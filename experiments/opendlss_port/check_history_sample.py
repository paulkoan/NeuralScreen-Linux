#!/usr/bin/env python3
"""Check the demo's reprojection and its five-tap Catmull-Rom history filter, arithmetically.

    uv run python experiments/opendlss_port/check_history_sample.py [checkout] [patch]

`serve`'s composite sampled the history at the pixel itself while the path was handed no motion,
and the patch's own header said why: "this path is handed no motion, so the reprojection is the
identity". That was honest only while the demo's reprojection and filter reduce to it when the
motion field is zero, and this is where that reduction is checked rather than asserted. (The
history half has since landed: shaders/composite_serve.comp carries the two, and
check_composite.py is where that rendering of them is compared with the demo's.) The definition
is read from the original, named and hash-pinned:

  * demo/shaders/velocity_unpack.comp and demo/shaders/nr_common.glsl of
    github.com/maanHimself/OpenDLSS-NR at 9d08f41 — the commit the port's stamp names. Quoted:

        // velocity_unpack.comp: motion is previous NDC - current NDC, y up
        vec2 ndc = vec2((float(id.x) + 0.5) / float(push.width) * 2.0 - 1.0,
                        1.0 - (float(id.y) + 0.5) / float(push.height) * 2.0);
        m = clip.xy / clip.w - ndc;                       // nothing drawn / depth 0: a point at infinity
        bool onScreen = all(lessThan(abs(ndc + m), vec2(1.0)));
        imageStore(motion, ivec2(id), onScreen ? vec4(0.5 * vec2(m.x, -m.y), 1.0, 0.0) : vec4(0.0));

        // nr_common.glsl: the reprojection, then the filter
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
        vec3 historySample(sampler2D previousTex, sampler2D motionTex, vec2 pixel, vec2 valid) {
          vec2 position = historyUv(motionTex, pixel, valid) * valid;
          vec2 base = floor(position - 0.5) + 0.5;
          vec2 f = clamp(position - base, vec2(0.0), vec2(1.0));
          vec2 square = f * f; vec2 cube = f * square;
          vec2 w0 = fma(f + cube, vec2(-0.5), square);
          vec2 w1 = (cube * 1.5 - square * 2.5) + 1.0;
          vec2 w3 = (cube - square) * 0.5;
          vec2 w2 = ((1.0 - w0) - w1) - w3;
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

What is checked, and what it rests on:

  1. The four weights are the uniform Catmull-Rom kernel sampled at f + 1, f, 1 - f and 2 - f
     (w2 is spelled as the residual that makes the four sum to 1), and `middle` = w1 + w2 is in
     [1, 1.125] — so `base + w2 / middle` cannot divide by zero.
  2. The five taps, with the coefficients a..e and the normalisation, compute the kernel's own
     twelve terms — the columns and rows of the cross, every product with at least one axis in
     {base, base + 1} — read off the texel grid instead of through interpolated fetches. The four
     corner texels are the ones the five taps cannot reach: they are dropped and the rest is
     renormalised, which is why this is a five-tap filter and not the tensor product of all four
     weights both ways.
  3. With the motion field zero, and the history valid-sized, the taps are the pixel's own texel
     exactly — bit for bit — which is what `serve` samples today.
  4. The reprojection: velocity_unpack's store puts `previous NDC - current NDC` into the motion
     texture as 0.5 * (m.x, -m.y), which is the uv delta with texture rows' y down, so
     `historyUv = uv + motion.xy` is the previous frame's position in uv. Off screen, the store
     writes zeros *and* the flag, so a pixel with no history cannot be handed a stale motion.

What this is NOT: a check on the GPU's texture filtering. Positions and weights here are double
precision and the texel reads are an emulation of a `linear` sampler with CLAMP_TO_EDGE
(demo/nr_pass.cpp), which is the arithmetic the shader asks for rather than the hardware's
rounding of it — the same standing as check_composite.py, which verifies that two spellings are
one formula and leaves the hardware to the parity gate. The taps are clamped into
[0.5, valid - 0.5] before they reach the sampler, so no tap wraps or leaves the texture whatever
the address mode is: the edge behaviour checked here is the shader's clamp.

Exit 2 if the original no longer says what is transliterated (or no checkout of it is readable).
"""
from __future__ import annotations

import hashlib
import math
import os
import sys
from pathlib import Path

import numpy as np

CASES = 3000
EPS32 = float(np.finfo(np.float32).eps)          # 1.19e-07
ORIGINAL = "github.com/maanHimself/OpenDLSS-NR"  # the commit the port's stamp names: 9d08f41
CHECKOUTS = [os.environ.get("NS_ODL_SRC"),
             "/opt/neuralscreen/port",
             str(Path.home() / "dev" / "OpenDLSS-NR"),
             "/opt/data/tmp/odl-src"]
FILES = {                                        # path -> sha256 of the bytes read
    "demo/shaders/nr_common.glsl": "0169c580bc56b8afa2ed39a65454010d470b743e8bd5775b134b6fac7d8fa8ef",
    "demo/shaders/velocity_unpack.comp": "58dd5013a67779eb682229473553b479eb5c6b126d916f9cb6c6413bd161b09b",
    "demo/shaders/nr_composite.comp": "faca7518816dd325e642b9e309e80bf2e2ee945e092fe3c2363d2735af004c70",
}

# The lines the transliterations below depend on. A rename or a reorder is where this file would
# otherwise quietly rot.
NEEDED = {
    "demo/shaders/nr_common.glsl": (
        "ivec2 motionTexel(sampler2D motionTex, vec2 pixel, vec2 valid) {",
        "return min(ivec2((pixel + 0.5) / valid * vec2(size)), size - 1);",
        "vec2 historyUv(sampler2D motionTex, vec2 pixel, vec2 valid) {",
        "vec2 uv = (pixel + 0.5) / valid;",
        "return texelFetch(motionTex, motionTexel(motionTex, pixel, valid), 0).xy + uv;",
        "return texelFetch(motionTex, motionTexel(motionTex, pixel, valid), 0).z > 0.5;",
        "vec3 historySample(sampler2D previousTex, sampler2D motionTex, vec2 pixel, vec2 valid) {",
        "vec2 position = historyUv(motionTex, pixel, valid) * valid;",
        "vec2 base = floor(position - 0.5) + 0.5;",
        "vec2 f = clamp(position - base, vec2(0.0), vec2(1.0));",
        "vec2 w0 = fma(f + cube, vec2(-0.5), square);",
        "vec2 w1 = (cube * 1.5 - square * 2.5) + 1.0;",
        "vec2 w3 = (cube - square) * 0.5;",
        "vec2 w2 = ((1.0 - w0) - w1) - w3;",
        "vec2 middle = w1 + w2;",
        "vec2 low = clamp(base - 1.0, vec2(0.5), valid - 0.5) / valid;",
        "vec2 center = clamp(base + w2 / middle, vec2(0.5), valid - 0.5) / valid;",
        "vec2 high = clamp(base + 2.0, vec2(0.5), valid - 0.5) / valid;",
        "vec3 left = textureLod(previousTex, vec2(low.x, center.y), 0.0).rgb;",
        "vec3 top = textureLod(previousTex, vec2(center.x, low.y), 0.0).rgb;",
        "vec3 mid = textureLod(previousTex, center, 0.0).rgb;",
        "vec3 bottom = textureLod(previousTex, vec2(center.x, high.y), 0.0).rgb;",
        "vec3 right = textureLod(previousTex, vec2(high.x, center.y), 0.0).rgb;",
        "float a = w0.x * middle.y; float b = w0.y * middle.x;",
        "float c = middle.x * middle.y; float d = w3.y * middle.x; float e = w3.x * middle.y;",
        "return value * (1.0 / (e + (d + (c + (a + b)))));",
    ),
    "demo/shaders/velocity_unpack.comp": (
        "vec2 m = vec2(uintBitsToFloat(v.z), uintBitsToFloat(v.w));",
        "m = clip.xy / clip.w - ndc;",
        "bool onScreen = all(lessThan(abs(ndc + m), vec2(1.0)));",
        "imageStore(motion, ivec2(id), onScreen ? vec4(0.5 * vec2(m.x, -m.y), 1.0, 0.0) : vec4(0.0));",
    ),
    "demo/shaders/nr_composite.comp": (
        "if (params.historyValid != 0u && hasHistory(motionTex, vec2(id), vec2(params.validWidth, params.validHeight))) {",
        "vec3 hist = historySample(historyPrev, motionTex, vec2(id), vec2(params.validWidth, params.validHeight));",
    ),
}
# The port's own shader, out of the patch. Read for a report and not transliterated: the two
# spellings it has had are both covered by the checks above, and when the patch carries a
# reprojection of its own that change has its own checker - this file is the authority it has to
# match, not a copy of it.
SHIPPED_FILTER = "historySample("
SHIPPED_PIXEL = "vec3 historyValue = history[index].rgb;"


def f32(x) -> np.float32:
    return np.float32(x)


def fma32(a, b, c) -> np.float32:
    """Exactly-rounded f32 fused multiply-add, which is what the shader's fma is."""
    return np.float32(math.fma(float(f32(a)), float(f32(b)), float(f32(c))))


def kernel(x: float) -> float:
    """The uniform Catmull-Rom kernel (a = -0.5), in double: the weights have to be this."""
    x = abs(x)
    if x <= 1.0:
        return 1.5 * x ** 3 - 2.5 * x ** 2 + 1.0
    if x < 2.0:
        return -0.5 * x ** 3 + 2.5 * x ** 2 - 4.0 * x + 2.0
    return 0.0


def shader_weights(f):
    """nr_common.glsl's four weights, in its own order of operations.

    A scalar offset gives four f32s; a vec2 offset (array of two) gives four arrays, one per axis,
    because that is what the shader's `vec2` weights are.
    """
    axes = np.array(f, dtype=np.float32).reshape(-1)
    per_axis = []
    for value in axes:
        value = np.float32(value)
        square = f32(value * value)
        cube = f32(square * value)
        w0 = fma32(f32(value + cube), -0.5, square)
        w1 = f32(f32(f32(cube * f32(1.5)) - f32(square * f32(2.5))) + f32(1.0))
        w3 = f32(f32(cube - square) * f32(0.5))
        w2 = f32(f32(f32(1.0 - w0) - w1) - w3)
        per_axis.append((w0, w1, w2, w3))
    if len(per_axis) == 1:
        return per_axis[0]
    return tuple(np.array([axis[k] for axis in per_axis], dtype=np.float32) for k in range(4))


def axis_weights(f) -> tuple[list[float], list[float]]:
    """The four weights per axis as plain floats: (x, y). A scalar offset gives the same axis twice."""
    per_axis = shader_weights(f)
    flat = [np.asarray(w).reshape(-1) for w in per_axis]
    if flat[0].size == 2:
        return ([float(w[0]) for w in flat], [float(w[1]) for w in flat])
    values = [float(w[0]) for w in flat]
    return values, values


def taps(base, weights, valid):
    """The five tap positions in uv, as historySample computes them from base and the weights.

    `base` is the containing texel's centre in pixel units (so a tap lands on a texel centre at
    i + 0.5), `valid` is (width, height) in pixels.
    """
    v = np.array(valid, dtype=np.float64)
    base = np.array(base, dtype=np.float64)
    w0, w1, w2, w3 = (np.array(w, dtype=np.float64) for w in weights)
    middle = np.array(f32(f32(w1) + f32(w2)), dtype=np.float64)     # the shader's vec2 middle
    low = np.clip(base - 1.0, 0.5, v - 0.5) / v
    center = np.clip(base + w2 / middle, 0.5, v - 0.5) / v
    high = np.clip(base + 2.0, 0.5, v - 0.5) / v
    return low, center, high, middle, (w0, w1, w2, w3)


def position_of(pixel, motion, valid):
    """historyUv * valid: the reprojected position in pixel units, where a texel centre is i + 0.5."""
    width, height = valid
    uv = np.array([(pixel[0] + 0.5) / width, (pixel[1] + 0.5) / height], dtype=np.float64)
    return (uv + np.array(motion, dtype=np.float64)) * np.array([width, height], dtype=np.float64)


def bilinear(img, u, v):
    """textureLod on a linear sampler, CLAMP_TO_EDGE, in double: the arithmetic the shader asks for.

    The indices are clamped and the fractional weights come from the unclamped position, which is
    what the address mode does; the shader's own clamp keeps every tap inside the texture, so this
    only ever bites on a tap that lands exactly on an edge.
    """
    height, width = img.shape
    x, y = float(u) * width - 0.5, float(v) * height - 0.5
    x0, y0 = math.floor(x), math.floor(y)
    fx, fy = x - x0, y - y0
    x0c, x1c = min(max(int(x0), 0), width - 1), min(max(int(x0) + 1, 0), width - 1)
    y0c, y1c = min(max(int(y0), 0), height - 1), min(max(int(y0) + 1, 0), height - 1)
    top = (1.0 - fx) * float(img[y0c, x0c]) + fx * float(img[y0c, x1c])
    bottom = (1.0 - fx) * float(img[y1c, x0c]) + fx * float(img[y1c, x1c])
    return (1.0 - fy) * top + fy * bottom


def split(pixel, motion, valid):
    """The position, the containing texel and the fractional offset — historySample's base and f."""
    position = position_of(pixel, motion, valid)
    base = np.floor(position - 0.5) + 0.5
    f = np.clip(position - base, 0.0, 1.0)
    return position, base, f


def five_tap(img, pixel, motion, valid):
    """historySample: the five interpolated fetches and the normalisation, line for line."""
    _, base, f = split(pixel, motion, valid)
    w0, w1, w2, w3 = shader_weights(f)
    low, center, high, middle, weights = taps(base, (w0, w1, w2, w3), valid)
    left = bilinear(img, low[0], center[1])
    top = bilinear(img, center[0], low[1])
    mid = bilinear(img, center[0], center[1])
    bottom = bilinear(img, center[0], high[1])
    right = bilinear(img, high[0], center[1])
    w0, w1, w2, w3 = weights
    a = w0[0] * middle[1]
    b = w0[1] * middle[0]
    c = middle[0] * middle[1]
    d = w3[1] * middle[0]
    e = w3[0] * middle[1]
    value = a * left + b * top + c * mid + d * bottom + e * right
    return value * (1.0 / (e + (d + (c + (a + b)))))


def cross_cr(img, pixel, motion, valid, corners=False):
    """The same value without the interpolated fetches: the kernel's weights on the texel grid.

    The four weights per axis multiply the columns base - 1, base, base + 1, base + 2 (the rows
    likewise). `corners` adds back the four corner texels — the ones where *both* axes are in
    {-1, +2}, which no position between two adjacent texel centres can be caught by five taps that
    stay on the cross. A tap outside the texture reads the edge texel, which is the shader's clamp.
    """
    width, height = valid
    _, base, f = split(pixel, motion, valid)
    wx, wy = axis_weights(f)
    first = [int(base[0] - 0.5), int(base[1] - 0.5)]
    total = 0.0
    value = 0.0
    for i in range(4):
        for j in range(4):
            if not corners and i in (0, 3) and j in (0, 3):
                continue
            x = min(max(first[0] + i - 1, 0), width - 1)
            y = min(max(first[1] + j - 1, 0), height - 1)
            weight = wx[i] * wy[j]
            value += weight * float(img[y, x])
            total += weight
    return value / total


def main() -> int:
    checkout = Path(sys.argv[1]) if len(sys.argv) > 1 else next(
        (Path(p) for p in CHECKOUTS
         if p and (Path(p) / "demo" / "shaders" / "nr_common.glsl").is_file()), None)
    if checkout is None:
        print(f"no checkout of {ORIGINAL} to read the definition from.")
        print("pass one as the first argument, or set NS_ODL_SRC.")
        return 2
    patch = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).with_name("linux-port.patch")
    print(f"the definition, read from {checkout}")

    for name, digest in FILES.items():
        path = checkout / name
        if not path.is_file():
            print(f"  {name}: not there")
            return 2
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        if got != digest:
            print(f"  {name}: not the original ({got[:12]})")
            print(f"this check is pinned to {ORIGINAL} 9d08f41 - update it with the shader")
            return 2
        source = path.read_text()
        for needed in NEEDED[name]:
            if needed not in source:
                print(f"  {name} no longer contains: {needed}")
                print("this check is stale - update it with the shader")
                return 2
    print(f"  {len(FILES)} files, the pinned originals, each saying what is transliterated here")

    text = patch.read_text()
    start = text.index("diff --git a/shaders/composite_serve.comp")
    body = text[start:]
    following = body.find("\ndiff --git ", 10)
    tail = body if following < 0 else body[:following]
    shipped = "".join(line[1:] + "\n" for line in tail.splitlines()
                      if line.startswith("+") and not line.startswith("+++"))
    if SHIPPED_FILTER in shipped:
        print("  shaders/composite_serve.comp: carries the reprojection and the filter; that side "
              "is check_composite.py's, from this definition  agree")
    elif SHIPPED_PIXEL in shipped:
        print("  shaders/composite_serve.comp: samples history[index], the pixel itself - the "
              "zero-motion case below  agree")
    else:
        print("  shaders/composite_serve.comp: no history sample recognised (the patch may be "
              "mid-edit); the original above is the authority either way")

    rng = np.random.default_rng(20261013)

    # --- 1. the four weights are the kernel --------------------------------------------------
    bad_weights = 0
    worst_weight = 0.0
    middle_low, middle_high = 9.9, -9.9
    for step in range(2049):
        f = f32(step / 2048.0)
        w0, w1, w2, w3 = shader_weights(f)
        for got, want in ((w0, kernel(float(f) + 1.0)), (w1, kernel(float(f))),
                          (w2, kernel(1.0 - float(f))), (w3, kernel(2.0 - float(f)))):
            gap = abs(float(f32(got)) - float(want))
            worst_weight = max(worst_weight, gap)
            if gap > 4 * EPS32:
                bad_weights += 1
        total = sum(float(w) for w in (w0, w1, w2, w3))
        middle = float(f32(f32(w1) + f32(w2)))
        middle_low, middle_high = min(middle_low, middle), max(middle_high, middle)
        if abs(total - 1.0) > 4 * EPS32 or not (1.0 <= middle <= 1.125):
            bad_weights += 1
    print(f"  1. the four weights, 2049 offsets: the kernel at f+1, f, 1-f, 2-f within "
          f"{worst_weight:.2e}; they sum to 1; middle in [{middle_low:.6f}, {middle_high:.6f}]  "
          f"{'agree' if not bad_weights else f'DIFFER in {bad_weights}'}")

    # --- 2. the five taps against the kernel read off the grid --------------------------------
    width, height = 64, 48
    valid = (width, height)
    bad_cross = bad_edges = bad_zero = 0
    worst_cross = worst_edges = 0.0
    corner_budget = 0.0
    for case in range(CASES):
        img = rng.random((height, width), dtype=np.float32)
        pixel = (int(rng.integers(0, width)), int(rng.integers(0, height)))
        edge = case % 3 == 0
        if edge:                                   # the clamp binds: a corner pixel, pushed inwards
            pixel = (0 if case % 6 == 0 else width - 1, 0 if case % 6 == 3 else height - 1)
        motion = [float(rng.random() * 1.9 - 0.95), float(rng.random() * 1.9 - 0.95)]
        zero = case % 7 == 0
        if zero:
            motion = [0.0, 0.0]
        got = five_tap(img, pixel, motion, valid)
        want = cross_cr(img, pixel, motion, valid)
        full = cross_cr(img, pixel, motion, valid, corners=True)
        _, base, f = split(pixel, motion, valid)
        wx, wy = axis_weights(f)
        corner_budget = max(corner_budget, (abs(wx[0]) + abs(wx[3])) * (abs(wy[0]) + abs(wy[3])))
        # 1e-6: the weights are f32 and the two sides group the same twelve products differently,
        # so what is left is the weights' own rounding (~1e-8 here), not algebra.
        gap = abs(got - want)
        worst_cross = max(worst_cross, gap)
        if edge:
            worst_edges = max(worst_edges, gap)
        if gap > 1e-6:
            bad_cross += 1
            if edge:
                bad_edges += 1
        if abs(got - full) > 2 * corner_budget + 1e-9:
            bad_cross += 1
        if zero and got != float(img[pixel[1], pixel[0]]):
            bad_zero += 1
    print(f"  2. the five taps against the kernel's twelve terms ({CASES} cases, the edges "
          f"included): worst {worst_cross:.2e} (edges {worst_edges:.2e})  "
          f"{'agree' if not bad_cross else f'DIFFER in {bad_cross}'}")
    print(f"     the four corner texels are dropped and the rest renormalised: at most "
          f"{corner_budget:.4f} of the weight, so at most {2 * corner_budget:.4f} of the local range")

    # --- 3. zero motion is the pixel's own texel ----------------------------------------------
    w, h = 32, 24
    img = rng.random((h, w), dtype=np.float32)
    moved = sum(1 for y in range(h) for x in range(w)
                if five_tap(img, (x, y), [0.0, 0.0], (w, h)) != float(img[y, x]))
    print(f"  3. zero motion, every pixel of a {w}x{h} history: the five taps read history[y*w + x], "
          f"the element serve samples  {'agree' if not moved else f'DIFFER in {moved}'}")
    if moved:
        bad_zero += moved

    # --- 4. the reprojection ------------------------------------------------------------------
    bad_reproject = 0
    worst_reproject = 0.0
    for case in range(CASES):
        w, h = 1280, 720
        pixel = (int(rng.integers(0, w)), int(rng.integers(0, h)))
        m = [float(rng.random() * 2.0 - 1.0), float(rng.random() * 2.0 - 1.0)]   # previous - current, NDC
        ndc = np.array([(pixel[0] + 0.5) / w * 2.0 - 1.0, 1.0 - (pixel[1] + 0.5) / h * 2.0])
        uv = np.array([(pixel[0] + 0.5) / w, (pixel[1] + 0.5) / h])
        stored = np.array([0.5 * m[0], -0.5 * m[1]])            # velocity_unpack's motion texture
        uv_prev = uv + stored
        gap = max(abs((2.0 * uv_prev[0] - 1.0) - (ndc[0] + m[0])),
                  abs((1.0 - 2.0 * uv_prev[1]) - (ndc[1] + m[1])))
        worst_reproject = max(worst_reproject, gap)
        if gap > 1e-12:
            bad_reproject += 1
        # the motion texture's texel for a pixel, at the render target's own size: the pixel (1:1)
        if min(int((pixel[0] + 0.5) / w * w), w - 1) != pixel[0]:
            bad_reproject += 1
        # and what the store does off screen: zeros and the flag together, never a stale motion
        on_screen = abs(ndc[0] + m[0]) < 1.0 and abs(ndc[1] + m[1]) < 1.0
        written = np.array([0.5 * m[0], -0.5 * m[1], 1.0]) if on_screen else np.zeros(3)
        if on_screen != (written[2] > 0.5) or (not on_screen and written.any()):
            bad_reproject += 1
    print(f"  4. the reprojection: uv + motion.xy is the previous NDC position, y down ({CASES} "
          f"cases): worst {worst_reproject:.2e}; its texel is the pixel's own at 1:1; off screen "
          f"the store writes zeros with the flag  "
          f"{'agree' if not bad_reproject else f'DIFFER in {bad_reproject}'}")

    # --- the field's own precision, reported rather than assumed -------------------------------
    # The motion texture is rgba16f (demo/nr_pass.cpp), so the stored uv delta is quantised to f16.
    half, one = float(np.spacing(np.float16(0.5))), float(np.spacing(np.float16(1.0)))
    print(f"     the field is f16: a uv delta of 0.5 steps by {half:.2e} uv = {half * 1440:.2f} px "
          f"at 1440 width, of 1.0 by {one:.2e} = {one * 1440:.2f} px")

    if bad_weights or bad_cross or bad_zero or bad_reproject:
        return 1
    print("the definition is the demo's, and serve's sample is it at zero motion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
