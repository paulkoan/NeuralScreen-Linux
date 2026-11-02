"""`--motion-guides`: estimate the motion field instead of sending zeros.

`guides.py` (TemporalGuideGenerator) was written and then never wired in, so every
measurement the port has taken sent a field of all zeros — which the worker treats as the
identity reprojection. These tests pin both halves: the default path still sends one reused
zero field, and the guides path sends an estimated one, at the size the wire expects.

The estimator needs cv2, which pulls libGL; tests that touch it skip where that is missing
and run on the box.
"""
import numpy as np

from minimal.loop import Pipeline
from minimal.worker import FLOW_H, FLOW_W
from tests.conftest import FakeDisplay

REPO = __import__("pathlib").Path(__file__).resolve().parent.parent


class _RecordingWorker:
    """Records the motion field each send carried, which the real worker copies immediately."""

    class _Proc:
        returncode = None

    def __init__(self):
        self.proc = self._Proc()
        self.logs: list[str] = []
        self.sends: list[dict] = []
        self._waiting: list[int] = []

    def start(self):
        pass

    def stop(self, timeout=None):
        self.proc.returncode = 0

    def is_alive(self):
        return True

    def send(self, index, frame, motion, reset, pts=0, want_pixels=True, bgra=False):
        # A copy, because the loop may reuse the buffer for the next frame.
        self.sends.append({"index": index, "motion": np.array(motion, copy=True), "reset": reset})
        self._waiting.append(index)

    def recv(self, index, timeout=60.0):
        self._waiting.remove(index)
        return None

    def recv_any(self, timeout=60.0):
        return self._waiting.pop(0), None


class _MovingCapture:
    """A frame whose content shifts one pixel per grab, so flow is not zero."""

    bgra = False

    def __init__(self, width=256, height=160):
        self.width, self.height = width, height
        self._n = 0

    @property
    def resolution(self):
        return self.width, self.height

    def grab(self):
        frame = np.zeros((self.height, self.width, 4), np.uint8)
        frame[..., 3] = 255
        # A block of texture that walks across the frame; a flat field has no flow.
        x = 8 + (self._n * 3) % (self.width - 40)
        frame[40:100, x:x + 32, :3] = 255
        self._n += 1
        return frame

    def close(self):
        pass


def _pipeline(**kwargs):
    return Pipeline(capture=_MovingCapture(), display=FakeDisplay(), headless=True,
                    worker_cmd=["true"], worker_cwd=REPO, want_pixels=False, **kwargs)


def test_the_default_still_sends_one_reused_zero_field():
    pipe = _pipeline()
    assert pipe.guides is None and pipe.motion_guides is False
    recorder = _RecordingWorker()
    pipe.worker = recorder
    pipe.run(frames=3)
    assert [s["index"] for s in recorder.sends] == [0, 1, 2]
    assert all(not np.any(s["motion"]) for s in recorder.sends), "the default must send zeros"
    assert [s["reset"] for s in recorder.sends] == [True, False, False]


def test_no_estimator_is_built_unless_it_is_asked_for():
    """Lazily created in __init__, so the default path never touches cv2."""
    pipe = _pipeline(motion_guides=False)
    assert pipe.guides is None


def _require_cv2():
    """cv2 imports but its libGL does not exist in every sandbox; skip where it fails."""
    try:
        import cv2  # noqa: F401
    except ImportError as exc:                      # pragma: no cover - environment dependent
        import pytest
        pytest.skip(f"cv2 is unusable here: {exc}")


def test_the_estimator_is_built_and_the_field_goes_out():
    _require_cv2()

    pipe = _pipeline(motion_guides=True)
    assert pipe.guides is not None
    assert pipe.no_motion is False, "a real field has to be sent, so no-motion must be off"

    recorder = _RecordingWorker()
    pipe.worker = recorder
    pipe.run(frames=4)

    assert [s["index"] for s in recorder.sends] == [0, 1, 2, 3]
    # Frame 0 has no predecessor: zeros and a reset, exactly as the estimator documents.
    assert not np.any(recorder.sends[0]["motion"])
    assert recorder.sends[0]["reset"] is True
    # After that the block has moved, so at least one frame must carry real motion.
    later = recorder.sends[1:]
    assert any(np.any(s["motion"]) for s in later), "the estimator produced no motion at all"
    for send in later:
        assert send["motion"].dtype == np.float16
        assert send["motion"].flags["C_CONTIGUOUS"]


def test_the_field_is_the_size_the_wire_expects():
    _require_cv2()

    full = _pipeline(motion_guides=True)
    assert full.zero_motion.shape == (full.work_h, full.work_w, 2)

    small = _pipeline(motion_guides=True, motion_small=True)
    assert small.zero_motion.shape == (FLOW_H, FLOW_W, 2)
    assert small.guides.emit_small is True


def test_a_scene_cut_asks_the_worker_to_reset():
    _require_cv2()

    from guides import TemporalGuideGenerator

    gen = TemporalGuideGenerator(256, 160)
    black = np.zeros((160, 256, 4), np.uint8)
    black[..., 3] = 255
    white = black.copy()
    white[..., :3] = 255

    first = gen.process(black)
    assert first.reset is True, "the first frame has no predecessor and must reset"
    assert not np.any(first.motion)

    same = gen.process(black)
    assert same.reset is False and not np.any(same.motion), "an unchanged frame has no motion"

    cut = gen.process(white)
    assert cut.reset is True, "a scene cut must reset history rather than carry flow across it"
    assert cut.scene_score > 0.24