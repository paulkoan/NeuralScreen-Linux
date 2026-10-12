#!/usr/bin/env python3
"""Check the serve composite's arithmetic against the two things it has to match.

    uv run python experiments/opendlss_port/check_composite.py [patch]

The shader (shaders/composite_serve.comp, taken out of linux-port.patch) is a
transliteration of two other pieces of code, and this is where that claim is checked
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

    `historySample` is the five-tap Catmull-Rom reconstruction; at a fractional offset of
    zero it is the centre tap and nothing else (the kernel is 1 at 0 and 0 at every other
    tap), which is what zero motion and no depth means here. So the reference's `hist` is
    the same texel, and the two are comparable.

What this is NOT: a check on the GPU's exp2 or on the driver's contractions. Both sides
run the same Python arithmetic here, so what is verified is that the two formulas are the
same formula — the hardware side is the parity gate on the box (src/main.cpp, which the
demo's own fixture drives). The last multiply-add is the one place contraction could
differ and it cannot bite: `inner * 8` is exact in f32, so there is one rounding either way
(that is src/main.cpp's own note on `composed`).
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np

CASES = 4000


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
    publication point. `head` is 4 channels; the fourth is the blend logit."""
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
    # they say. A rename or a reorder is where this file would otherwise quietly rot.
    for needed in ("float composeChannel(float headValue, float centredProxy)",
                   "float inner = fma(headValue, 0.03125, centredProxy);",
                   "return clamp(inner * 8.0 + 0.5, 0.0, 1.0);",
                   "if (pc.historyValid != 0u) {",
                   "float scale = clamp(pc.blendScale, 0.0, 1.0);",
                   "float weight = clamp((1.0 / (1.0 + exp2(neural.a * uintBitsToFloat(0xbfb8aa3bu)))) * scale,",
                   "vec3 historyValue = history[index].rgb;",
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

    print(f"{CASES} random cases, both paths")
    print(f"  no history: the shader against src/main.cpp's composed()  "
          f"{'agree' if not mismatched_parity else f'DIFFER in {mismatched_parity} (by {worst_parity})'}")
    print(f"  history:    the shader against demo/shaders/nr_composite.comp  "
          f"{'agree' if not mismatched_demo else f'DIFFER in {mismatched_demo} (by {worst_demo})'}")
    if mismatched_parity or mismatched_demo:
        return 1
    print("the blend is the demo's formula, and it is invisible without a history")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
