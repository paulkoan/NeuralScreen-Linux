#!/usr/bin/env python3
"""Check the serve blend_scale readout against the model it has to be read from.

    uv run python experiments/opendlss_port/check_blend_scale.py [patch] [container]

`serve` prints one line at startup:

    serve: blend scale 0.7397 (block70.layer0.blend_scale)

and that line is the only evidence a run has that the temporal blend's learned cap came
out of the model rather than out of the source. Absent or short, the readout falls back to
the demo's own 1.0 — by design, because a model without this weight is still servable —
so the failure this guards against looks exactly like a healthy run: a frame comes back,
the loop's numbers are the loop's numbers, and the only thing that changed is a weight
that never arrived. r2026-10-12-d's whole claim about the blend being free rests on the
value being 0.7397 and not the default.

Two authorities, checked here and neither asserted:

  * the source, out of linux-port.patch's src/serve.cpp — the tensor the readout looks up
    (`model->tensor(70, 0, "blend_scale")`), the f16 load inside it
    (`nr::auxHalf(blend, 0, 0)` — byteOffset 0, column 0, the front of the tensor), the
    width guard, and the two strings that make "read" and "defaulted" different lines.
    A read that was removed, renamed, moved to another tensor or pointed at a different
    half in the tensor does not contain what this file transliterates, and this file says
    so and stops.
  * the model — `native/nvngx_dlssnr.dll`, whose weight table `extract.py` walks. The
    payload of `block70.layer0.blend_scale` is `eb 39`, which as f16 is 0.73974609375:
    docs/frame.md's documented 0.7397, the value the readout printed on the box. The same
    arithmetic one half along — the trailer's first two bytes, or the next tensor's — is
    0.0 and 0.000336, so the coordinates are discriminating and a shifted read cannot land
    on the documented value by accident.

Exit codes: 0 the readout is the model's, 2 it is not (or this check is stale), 2 the
container is not there to check against. The container is NVIDIA's and gitignored, so a
clone without it cannot verify the value — it will not say "verified" without it.
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DLL = REPO / "native" / "nvngx_dlssnr.dll"
sys.path.insert(0, str(REPO / "experiments" / "opendlss_weights"))

import extract  # noqa: E402

# docs/frame.md's one known constant of the shipped model, and the tensor that carries it.
PIN = 0.7397
TENSOR = "block70.layer0.blend_scale"

TENSOR_RE = re.compile(r'model->tensor\(\s*(\d+)\s*,\s*(\d+)\s*,\s*"([^"]+)"\s*\)')
BIND_RE = re.compile(r"Tensor&\s*(\w+)\s*=\s*model->tensor")
AUX_RE = re.compile(r"auxHalf\(\s*(\w+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")


def patch_adds(patch_text: str, path: str) -> str:
    """The added lines of one file in a git format-patch, as source."""
    start = patch_text.index(f"diff --git a/{path}")
    body = patch_text[start:]
    following = body.find("\ndiff --git ", 10)
    diff = body if following < 0 else body[:following]
    return "".join(line[1:] + "\n" for line in diff.splitlines()
                   if line.startswith("+") and not line.startswith("+++"))


def refuse(what: str) -> int:
    print(f"the readout no longer contains: {what}")
    print("this check is stale - update it with the readout")
    return 2


def main() -> int:
    patch = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("linux-port.patch")
    container = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_DLL
    source = patch_adds(patch.read_text(), "src/serve.cpp")

    read = TENSOR_RE.search(source)
    if read is None:
        return refuse("the blend_scale tensor lookup (model->tensor(..))")
    bind = BIND_RE.search(source)
    if bind is None:
        return refuse("the binding of the looked-up tensor to a name")

    block, layer, parameter = read.group(1), read.group(2), read.group(3)
    if f"block{block}.layer{layer}.{parameter}" != TENSOR:
        return refuse(
            f"the lookup it transliterates: model->tensor({block}, {layer}, \"{parameter}\") "
            f"is not {TENSOR}")

    aux = AUX_RE.search(source)
    if aux is None:
        return refuse("the f16 load out of the tensor (auxHalf(..))")
    if aux.group(1) != bind.group(1):
        return refuse(
            f"the f16 load out of the tensor it looked up: it reads "
            f"auxHalf({aux.group(1)}, ..) but the tensor is bound to {bind.group(1)}")
    byte_offset, column = int(aux.group(2)), int(aux.group(3))

    for needed, why in (
            ("float blendScale = 1.0f;", "the declared default"),
            ("if (blend.byteLength >= 2)", "the width guard on the f16"),
            (f'"{TENSOR}"', "the string that names what was read"),
            ('"absent - defaulted to 1.0', "the string the fallback prints")):
        if needed not in source:
            return refuse(f"{why} ({needed})")

    # The two strings have to be two arms of one expression: a fallback printed
    # unconditionally is a line that reads the same whether the weight arrived or not.
    fallback = next((ln for ln in source.splitlines() if "absent - defaulted to 1.0" in ln), "")
    if "found ?" not in fallback:
        return refuse("the fallback as the else arm of `found ? .. : ..`")

    if not container.is_file():
        print(f"no such file: {container}")
        print("native/nvngx_dlssnr.dll is gitignored (159 MiB, and NVIDIA's), so this clone "
              "cannot check the readout's value against the model. Point the second argument "
              "at wherever it is.")
        return 2

    data = container.read_bytes()
    try:
        off, size = extract.find_weight_blob(data)
    except extract.ExtractionError as error:
        print(f"{container} carries no weight table to check against: {error}")
        return 2
    blob = data[off:off + size]
    records = extract.parse_records(blob, extract.DEFAULT_FIELDS)
    record = next((r for r in records if r["name"] == TENSOR), None)
    if record is None:
        print(f"the model has no {TENSOR} record to read")
        return 2
    payload = record["payload_offset"]

    # nr::auxHalf(tensor, byteOffset, column), transliterated: the u16 at
    # byteOffset + column * 2, little endian, read as f16. The readout's own arithmetic.
    def read_half(byte_offset_: int, column_: int) -> float:
        at = payload + byte_offset_ + column_ * 2
        return struct.unpack_from("<e", blob + b"\0\0", at)[0]

    value = read_half(byte_offset, column)
    print(f"the readout, out of {patch.name}: model->tensor({block}, {layer}, \"{parameter}\"), "
          f"auxHalf(blend, {byte_offset}, {column})")
    print(f"the model, out of {container.name}: {TENSOR} at {payload:,}, "
          f"{record['byteLength']} bytes wide, {'/'.join(f'{b:02x}' for b in blob[payload:payload + record['byteLength']])}")

    failures = []
    if abs(value - PIN) >= 1e-3:
        failures.append(f"the read lands on {value!r}, not the documented {PIN} "
                        f"({PIN} as f16 is 0.73974609375)")
    elif value == 1.0:
        failures.append("the read lands on the 1.0 default, not the model's weight")

    # The coordinates have to be discriminating, or the pin above is a coincidence of
    # position: a read one half along reads something else, wherever the shift lands.
    next_payload = next((r["payload_offset"] for r in records
                         if r["payload_offset"] > payload), len(blob))
    shifted = {
        "the half after it in the container": read_half(byte_offset + 2, column),
        "column 1": read_half(byte_offset, column + 1),
        "the next tensor's front": struct.unpack_from("<e", blob + b"\0\0", next_payload)[0],
    }
    for where, shifted_value in shifted.items():
        if abs(shifted_value - PIN) < 1e-3:
            failures.append(f"{where} reads {shifted_value!r} too: the read's coordinates "
                            f"are not what distinguishes {TENSOR}")

    if failures:
        for failure in failures:
            print(f"REFUSED: {failure}")
        print("the readout is not the model's weight - a run would report it as one anyway")
        return 2

    print(f"  the value:  {value!r} at the read's own coordinates  agree")
    for where, shifted_value in shifted.items():
        print(f"  {where}: {shifted_value!r}  agree - not this value")
    print(f"  the default: the fallback prints its own string, not the tensor's name  agree")
    print(f"the readout is {TENSOR}, read from the model: {value!r}, not the 1.0 default")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
