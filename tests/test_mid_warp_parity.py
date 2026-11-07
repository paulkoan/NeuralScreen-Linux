"""The mid-frame's arithmetic has to be the composite's, and nothing compiled here can say so.

`shaders/mid_warp.comp` states its own contract: its reconstruction "is deliberately the
composite's own", and `historyFetch` is "identical to composite_serve.comp's; the two have to
agree". A person wrote that and nothing checked it - `check_composite.py` transliterates the
composite's copy of the arithmetic, and there was no equivalent for the second copy the
mid-frame added.

Why it matters more than tidiness: the client treats a generated mid-frame and a real frame as
the same kind of object on the wire - RGBA8, same byte arithmetic, no special case in the loop.
If the two spellings of `truncateHalf`, `toByte` or `historyFetch` drift apart, a mid-frame
stops being the same kind of object and nothing raises: the run completes, the counts are right,
and the picture between two real frames is subtly not the same reconstruction. Same failure
shape as a binding mismatch - silent, and only visible as a picture, on a machine with a GPU.

Both shaders are read out of the port patch rather than the port source, so this runs anywhere
the repo does. The negative half of the test mutates a copy and requires the comparison to
notice, because a checker that cannot fail is not a check.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

PATCH = REPO / "experiments" / "opendlss_port" / "linux-port.patch"
SHARED = ("truncateHalf", "toByte", "historyFetch")


def added_text(patch_text: str, path: str) -> str:
    """The added lines for one file inside a patch."""
    out, inside = [], False
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            inside = line.startswith(f"diff --git a/{path} b/{path}")
            continue
        if inside and line.startswith("+") and not line.startswith("+++"):
            out.append(line[1:])
    return "\n".join(out)


def function(src: str, name: str) -> str | None:
    m = re.search(r"^[A-Za-z_][\w:<> ]*\b%s\s*\([^)]*\)\s*\{(.*?)^\}" % re.escape(name),
                  src, re.S | re.M)
    return m.group(0) if m else None


def normalise(src: str) -> str:
    """Comments and whitespace are free to differ; the arithmetic is not."""
    src = re.sub(r"//[^\n]*", "", src)
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"\s+", " ", src).strip()


def shaders():
    patch_text = PATCH.read_text(encoding="utf-8")
    mid = added_text(patch_text, "shaders/mid_warp.comp")
    comp = added_text(patch_text, "shaders/composite_serve.comp")
    assert mid, "the patch no longer carries shaders/mid_warp.comp"
    assert comp, "the patch no longer carries shaders/composite_serve.comp"
    return mid, comp


def test_both_shaders_are_in_the_patch():
    mid, comp = shaders()
    assert "mid(pixel) = historySample" in mid, "the mid warp's own expression is not in it"
    assert "historyFetch" in comp


def test_the_mid_frame_reuses_the_composites_arithmetic():
    mid, comp = shaders()
    for name in SHARED:
        a, b = function(mid, name), function(comp, name)
        assert a is not None, f"{name} is missing from mid_warp.comp"
        assert b is not None, f"{name} is missing from composite_serve.comp"
        assert normalise(a) == normalise(b), (
            f"{name} differs between the mid-frame shader and the composite. The client treats "
            f"both outputs as the same kind of bytes; if this drifts, the mid-frame is a "
            f"different object and nothing else notices.\n"
            f"  mid      : {normalise(a)[:200]}\n"
            f"  composite: {normalise(b)[:200]}")


def test_the_check_notices_a_divergence():
    """A checker that cannot fail is not a checker."""
    mid, comp = shaders()
    broken = mid.replace("0.0, 255.0", "0.0, 254.0", 1)
    assert broken != mid, "the mutation did not apply - the test is not testing anything"
    a, b = function(broken, "toByte"), function(comp, "toByte")
    assert a is not None and b is not None, "toByte vanished from one of the shaders"
    assert normalise(a) != normalise(b), "the comparison missed a changed constant"


def test_the_mid_shader_takes_its_own_push_constant_and_nothing_else():
    """The host fills a 20-byte push; a shader that grew a field would read the next one as junk."""
    mid, _ = shaders()
    m = re.search(r"layout\(push_constant\) uniform Push \{(.*?)\}", mid, re.S)
    assert m, "mid_warp.comp has no push_constant block"
    block = re.sub(r"//[^\n]*", "", m.group(1))   # a trailing comment is not a field
    fields = [f.strip() for f in block.split(";") if f.strip()]
    assert len(fields) == 5, f"the host writes 5 fields, the shader declares {len(fields)}: {fields}"
    assert "midOffset" in fields[-1], "the last field is the one the host passes 0.5 in"

    # and the host's struct agrees, name for name. The definition is in kernels.cpp; the call is
    # in serve.cpp, and the offset it passes is the one thing here that must be a half.
    patch_text = PATCH.read_text(encoding="utf-8")
    host = added_text(patch_text, "src/kernels.cpp")
    hm = re.search(r"void Kernels::midWarpToRgba8.*?struct Push \{(.*?)\}", host, re.S)
    assert hm, "the host's midWarpToRgba8 no longer declares a Push struct"
    # C may declare several names on one line, so count names rather than statements
    host_names = [n.strip().split()[-1]
                  for n in re.split(r"[,;]", re.sub(r"//[^\n]*", "", hm.group(1)))
                  if n.strip() and not n.strip().startswith(("struct", "}"))]
    shader_names = [f.split()[-1] for f in fields]
    assert host_names == shader_names, (
        f"the host fills {host_names} but the shader reads {shader_names} - a field that moved "
        f"or changed type reads the neighbouring bytes as the value, and a 20-byte push is small "
        f"enough that nothing else would complain")

    serve = added_text(patch_text, "src/serve.cpp")
    call = re.search(r"midWarpToRgba8\((.*?)\);", serve, re.S)
    assert call, "serve.cpp no longer calls midWarpToRgba8"
    assert "0.5f" in call.group(1), (
        "the call no longer passes 0.5 - the mid-frame is a fraction of a frame by definition, "
        "and any other value puts it somewhere between the two frames it is meant to sit between")
