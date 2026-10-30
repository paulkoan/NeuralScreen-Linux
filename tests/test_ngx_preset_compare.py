"""The preset comparison must refuse to quote a difference it cannot attribute.

These tests pin the parser against the real log shapes (r2026-10-29-b's stdout and the NGX
host's feature-created line) and pin every refusal the tool relies on: same preset reached the
DLL, same frame was not fed to both runs, frames were skipped, a run did not exit 0.
"""
import importlib.util
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "ngx_preset_compare.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("ngx_preset_compare", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GOOD = """\
source synthetic  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)
params: auto_mask=0 intensity=1.0 local_structure=1.0 local_tone=1.0 preset=0 profile=1 skin_structure=-1.0 style=1 ui_correction=0
worker: /opt/neuralscreen/port/build/dlss5vk serve --model /opt/neuralscreen/model
stamp:   port 9d08f41 (12 modified) patch 819bea6f149ee975b922cfea802402d1bd9b7111
frames: 120 done, 0 skipped, 8.621s (13.92 fps headline, 34.7 fps steady), worker exit 0
timing: capture 5.1ms  send 6.4ms  recv 58.4ms  display 0.0ms   (mean 69.9ms/frame, 14.3 fps; median 28.8ms/frame, 34.7 fps steady)
[worker] serve: frame 0 carries reset: no history for this frame, and this frame primes the next
[worker] serve frame 5: total 37.0 (proxy 8.6, network+composite 16.2, readback 4.5, reply 7.9)
[worker] serve frame 6: total 37.9 (proxy 10.4, network+composite 13.5, readback 7.3, reply 8.3)
"""


def test_parse_reads_the_real_lines():
    tool = load_tool()
    info = tool.parse(GOOD)
    assert info["frames"]["done"] == 120
    assert info["frames"]["skipped"] == 0
    assert info["frames"]["steady"] == "34.7"
    assert info["timing"]["median"] == 28.8
    assert info["timing"]["median_fps"] == 34.7
    assert info["worker"].startswith("/opt/neuralscreen/port")
    assert "819bea6f149e" in info["stamp"]
    assert info["network_composite_ms"] == [16.2, 13.5]


def test_parse_without_a_preset_line_leaves_it_none():
    tool = load_tool()
    info = tool.parse(GOOD.replace("stamp:", "nostamp:"))
    assert info["preset"] is None


def make_pair(tool, preset_old=1, preset_new=2, before_old="aa", before_new="aa",
              after_old="bb", after_new="cc", exit_old=0, exit_new=0, skipped=0):
    def side(tag, preset, before, after, code):
        return {"tag": tag, "preset": preset, "exit_code": code, "after": "after.png",
                "before_sha": before, "after_sha": after, "frames": {"skipped": skipped},
                "timing": {"median": 30.0}, "network_composite_ms": []}
    return side("preset1", preset_old, before_old, after_old, exit_old), \
           side("preset2", preset_new, before_new, after_new, exit_new)


def test_a_good_pair_is_trustworthy():
    tool = load_tool()
    ok, problems = tool.verdict(*make_pair(tool))
    assert ok and problems == []


def test_the_same_preset_is_refused():
    tool = load_tool()
    ok, problems = tool.verdict(*make_pair(tool, preset_new=1))
    assert not ok
    assert any("did not switch" in p for p in problems)


def test_a_different_before_frame_is_refused():
    tool = load_tool()
    ok, problems = tool.verdict(*make_pair(tool, before_new="dd"))
    assert not ok
    assert any("same frame" in p for p in problems)


def test_an_identical_after_frame_is_refused():
    tool = load_tool()
    ok, problems = tool.verdict(*make_pair(tool, after_new="bb"))
    assert not ok
    assert any("picture did not change" in p for p in problems)


def test_skipped_frames_are_refused():
    tool = load_tool()
    ok, problems = tool.verdict(*make_pair(tool, skipped=3))
    assert not ok
    assert sum("skipped" in p for p in problems) == 2


def test_a_failed_run_is_refused():
    tool = load_tool()
    ok, problems = tool.verdict(*make_pair(tool, exit_new=3))
    assert not ok
    assert any("not a completed run" in p for p in problems)
