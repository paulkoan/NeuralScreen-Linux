"""The complete burst is saved in a form a downstream run can read.

`--save-burst DIR` is the difference between "we measured a session" and "the
session can be measured again later": it keeps every frame's colour on both
sides of the pass and the motion field that went with it, plus a manifest that
names the layout and the capture split. These tests run it against the mock
worker and a virtual X server, so no GPU and no portal are involved.

What is checked is the contract a reader relies on:

  * the manifest exists and agrees with the files on disk (count and size);
  * each saved frame's colour PNG opens at the capture resolution;
  * the motion npz reads back as the float16 HxWx2 field that was sent;
  * the capture split lands in the manifest when the source reports one.

The last one is skipped when the source cannot split its own grab: a synthetic
screen has no "waiting for the frame" half, and the manifest must say so by
leaving the key out rather than by inventing zeros.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

MOCK_WORKER = REPO / "tests" / "mock_worker.py"


@pytest.fixture
def cli_env(xvfb_display, monkeypatch):
    """The environment `python -m minimal` needs to run against the mock."""
    monkeypatch.setenv("DISPLAY", xvfb_display)
    monkeypatch.setenv("NS_WORKER_CMD", f"{sys.executable} {MOCK_WORKER}")
    monkeypatch.chdir(REPO)
    return xvfb_display


def _run_burst(tmp_path: Path, frames: int = 3) -> tuple[int, Path]:
    from minimal.__main__ import main

    burst = tmp_path / "burst"
    code = main(["--frames", str(frames), "--headless",
                 "--save-burst", str(burst)])
    return code, burst


def test_burst_writes_manifest_frames_and_motion(cli_env, tmp_path, capsys):
    """A short run saves every answered frame, its motion field and a manifest."""
    code, burst = _run_burst(tmp_path, frames=3)
    out = capsys.readouterr().out

    assert code == 0, f"the CLI exited {code}:\n{out}"
    manifest_path = burst / "manifest.json"
    assert manifest_path.is_file(), f"no manifest; output was:\n{out}"
    manifest = json.loads(manifest_path.read_text())

    assert manifest["format"] == "neuralscreen-burst/1"
    saved = manifest["frames_saved"]
    assert saved >= 3, f"only {saved} frames saved of 3 attempted"
    assert manifest["frames_dropped"] == 0, "frames were dropped on a 3-frame run"
    assert manifest["errors"] == []

    frames_dir = burst / manifest["frames_dir"]
    motion_dir = burst / manifest["motion_dir"]
    for index in range(saved):
        for side in ("before", "after"):
            png = frames_dir / f"frame_{index:06d}_{side}.png"
            assert png.is_file(), f"missing {png}"
            assert png.stat().st_size > 0
        npz = motion_dir / f"frame_{index:06d}_motion.npz"
        assert npz.is_file(), f"missing {npz}"
        with np.load(npz) as data:
            motion = data["motion"]
        assert list(motion.shape) == manifest["motion_shape"], (
            f"{npz.name} is {motion.shape}, manifest says "
            f"{manifest['motion_shape']}")
        assert motion.dtype == np.float16
        # The pipeline sends a zero field today; the point of saving it is that
        # the downstream run can see it is zero rather than assume a flow.
        assert np.array_equal(motion, np.zeros_like(motion))

    assert manifest["width"] and manifest["height"], "resolution not recorded"
    assert "burst" in out and "manifest" in out
    assert f"{saved} frames saved" in out


def test_burst_frames_open_at_capture_resolution(cli_env, tmp_path):
    """The saved colour frames are the size the capture reported."""
    import pygame

    code, burst = _run_burst(tmp_path, frames=2)
    assert code == 0
    manifest = json.loads((burst / "manifest.json").read_text())
    w, h = manifest["width"], manifest["height"]
    for side in ("before", "after"):
        surface = pygame.image.load(
            str(burst / manifest["frames_dir"] / f"frame_000000_{side}.png"))
        assert surface.get_size() == (w, h), (
            f"{side} frame is {surface.get_size()}, manifest says {(w, h)}")


def test_pipeline_saves_a_burst_a_reader_can_open(
        fake_capture, fake_display, mock_worker_cmd, tmp_path):
    """The whole chain without a display: run the pass, save the burst, read it.

    This is the acceptance test for "the saved data is in a format that the
    downstream analysis runs can immediately read": it drives the real Pipeline
    against the mock worker and FakeCapture/FakeDisplay (no X server, no portal),
    saves a burst, and then opens it with the reader a downstream run would use.
    """
    from minimal.loop import Pipeline
    from tools.read_burst import load_burst, load_manifest

    burst = tmp_path / "burst"
    pipe = Pipeline(capture=fake_capture, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO)
    summary = pipe.run(frames=3, save_burst=str(burst))

    assert summary["frames_done"] >= 3, summary
    assert summary["burst"] is not None, "save_burst did not produce a manifest"
    manifest = load_manifest(burst)
    assert manifest["frames_saved"] >= 3
    assert manifest["frames_dropped"] == 0
    assert manifest["errors"] == []

    frames = list(load_burst(burst))
    assert len(frames) == manifest["frames_saved"], (
        "the reader returned a different number of frames than the manifest names")
    for index, before, after, motion in frames:
        assert before.shape == after.shape, "colour frames changed size"
        assert before.shape[:2] == (manifest["height"], manifest["width"])
        assert motion.shape[-1] == 2, "motion is not an (H,W,2) field"
        assert motion.dtype == np.float16
    # The mock worker offsets the pixels, so a saved 'after' must differ from its
    # 'before'. A burst of identical pairs would be a capture of the display's
    # own copy rather than the pass's result.
    _, before, after, _ = frames[0]
    assert not np.array_equal(before, after), (
        "the saved 'after' is identical to its 'before'")


def test_reader_refuses_a_burst_with_a_missing_frame(
        fake_capture, fake_display, mock_worker_cmd, tmp_path):
    """A manifest that promises a frame the directory does not have is an error.

    The reader is the contract between the run and every downstream analysis, so
    it must fail loudly on an incomplete burst rather than yield a short list
    that a mean gets computed over.
    """
    from minimal.loop import Pipeline
    from tools.read_burst import BurstError, load_burst

    burst = tmp_path / "burst"
    pipe = Pipeline(capture=fake_capture, display=fake_display, headless=True,
                    worker_cmd=mock_worker_cmd, worker_cwd=REPO)
    pipe.run(frames=2, save_burst=str(burst))

    missing = burst / "frames" / "frame_000001_after.png"
    assert missing.is_file()
    missing.unlink()

    with pytest.raises(BurstError) as excinfo:
        list(load_burst(burst))
    assert "missing" in str(excinfo.value)


def test_burst_manifest_records_capture_split_when_available(
        cli_env, tmp_path):
    """A source that splits its grab puts the split in the manifest."""
    code, burst = _run_burst(tmp_path, frames=2)
    assert code == 0
    manifest = json.loads((burst / "manifest.json").read_text())
    split = manifest.get("capture_split")
    if not split:
        pytest.skip("the synthetic source does not split its own grab")
    assert set(split) >= {"wait_ms", "read_ms", "frames"}
    assert split["frames"] > 0
