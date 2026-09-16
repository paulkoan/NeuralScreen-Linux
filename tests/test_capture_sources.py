"""The non-screen frame sources: synthetic test card and still-image replay.

These deliberately do NOT use the xvfb_display fixture. The reason the sources
exist is that a real screen capture could not be trusted or could not work at
all — on a Wayland session mss reads the XWayland root window, which is black —
so the one thing these must not depend on is a display. If someone later wires a
display requirement in here, these tests are what should notice.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def test_synthetic_reports_the_requested_resolution():
    from minimal.capture import SyntheticCapture
    cap = SyntheticCapture(320, 180)
    assert cap.resolution == (320, 180)
    assert (cap.width, cap.height) == (320, 180)


def test_synthetic_returns_rgba_uint8_of_the_right_shape():
    from minimal.capture import SyntheticCapture
    frame = SyntheticCapture(320, 180).grab()
    assert frame.dtype == np.uint8, f"expected uint8, got {frame.dtype}"
    assert frame.ndim == 3 and frame.shape[2] == 4, f"got {frame.shape}"
    assert frame.shape[:2] == (180, 320)


def test_synthetic_frames_are_not_all_the_same():
    """A moving element, so consecutive frames differ.

    A static source would let a broken pipeline look healthy by returning a
    cached frame, and would give the NR pass nothing temporal to work on.
    """
    from minimal.capture import SyntheticCapture
    cap = SyntheticCapture(320, 180)
    assert not np.array_equal(cap.grab(), cap.grab())


def test_synthetic_has_texture_in_every_channel():
    """Structural content, not a flat fill.

    A flat frame is indistinguishable from a failed capture: the pass would
    'succeed' while changing nothing. Every channel must carry variation.
    """
    from minimal.capture import SyntheticCapture
    frame = SyntheticCapture(320, 180).grab()
    for ch, name in enumerate("RGB"):
        assert frame[..., ch].std() > 10.0, (
            f"channel {name} is nearly flat (std {frame[..., ch].std():.2f})")


def test_synthetic_frames_actually_move():
    """The moving bar has to move — 'not equal' is too weak on its own."""
    from minimal.capture import SyntheticCapture
    cap = SyntheticCapture(320, 180)
    a = cap.grab().astype(np.int16)
    b = cap.grab().astype(np.int16)
    assert np.abs(a - b).mean() > 1.0, "consecutive frames barely differ"


def test_image_replays_a_written_file(tmp_path):
    import cv2
    from minimal.capture import ImageCapture
    src = np.zeros((90, 160, 3), dtype=np.uint8)
    src[:, :80, 2] = 200          # a red half, in BGR as cv2 writes it
    src[..., 1] = np.linspace(0, 255, 90, dtype=np.uint8)[:, None]
    path = tmp_path / "shot.png"
    assert cv2.imwrite(str(path), src)

    cap = ImageCapture(path)
    assert cap.resolution == (160, 90)
    frame = cap.grab()
    assert frame.dtype == np.uint8 and frame.shape == (90, 160, 4)
    # R and B must not be swapped on the way in: RGBA is what the worker wants.
    assert frame[0, 0, 0] > 150, "red channel lost the red half"
    assert frame[0, 0, 3] == 255, "alpha should be opaque"
    assert np.array_equal(frame, cap.grab()), "a still must not change between grabs"


def test_image_rejects_an_unreadable_file(tmp_path):
    from minimal.capture import CaptureError, ImageCapture
    bad = tmp_path / "not-an-image.png"
    bad.write_text("this is not a png")
    with pytest.raises(CaptureError):
        ImageCapture(bad)
    with pytest.raises(CaptureError):
        ImageCapture(tmp_path / "does-not-exist.png")


def test_open_capture_dispatches():
    from minimal.capture import ImageCapture, SyntheticCapture, open_capture
    assert isinstance(open_capture("synthetic", width=64, height=32), SyntheticCapture)
    assert open_capture("synthetic", width=64, height=32).resolution == (64, 32)


def test_open_capture_image_requires_a_path():
    from minimal.capture import CaptureError, open_capture
    with pytest.raises(CaptureError) as exc:
        open_capture("image")
    assert "--input-image" in str(exc.value)


def test_open_capture_rejects_an_unknown_source():
    from minimal.capture import CaptureError, open_capture
    with pytest.raises(CaptureError) as exc:
        open_capture("nonsense")
    assert "nonsense" in str(exc.value)


def test_open_capture_image_reads_the_file(tmp_path):
    import cv2
    from minimal.capture import open_capture
    path = tmp_path / "shot.png"
    cv2.imwrite(str(path), np.full((40, 70, 3), 128, dtype=np.uint8))
    cap = open_capture("image", input_image=path)
    assert cap.resolution == (70, 40)
    assert cap.grab().shape == (40, 70, 4)


# --- writing a frame out ---------------------------------------------------

def test_save_png_round_trips_the_colours(tmp_path):
    """A saved frame must have the colours the frame had."""
    import cv2

    from minimal.capture import save_png
    frame = np.zeros((2, 2, 4), dtype=np.uint8)
    frame[..., 0] = 200          # R
    frame[..., 1] = 100          # G
    frame[..., 2] = 50           # B
    frame[..., 3] = 255          # A

    path = tmp_path / "frame.png"
    save_png(path, frame)
    back = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)

    assert back.shape == (2, 2, 3), (
        f"expected an opaque 3-channel PNG, got {back.shape}; an alpha channel "
        "gets flattened against a background by anything downstream")
    b, g, r = (int(back[0, 0, i]) for i in range(3))
    assert (r, g, b) == (200, 100, 50), f"channels are wrong: RGB came back as {(r, g, b)}"


def test_the_old_channel_reversal_is_not_equivalent(tmp_path):
    """Prove the round-trip test above bites, using the bug that shipped.

    `frame[..., ::-1]` looks like an RGBA->BGRA swap and is not one: it reverses
    all four channels, so the file's alpha ends up holding the red channel.
    """
    import cv2

    from minimal.capture import save_png
    frame = np.zeros((1, 1, 4), dtype=np.uint8)
    frame[..., 0], frame[..., 1], frame[..., 2], frame[..., 3] = 200, 100, 50, 255

    good, bad = tmp_path / "good.png", tmp_path / "bad.png"
    save_png(good, frame)
    cv2.imwrite(str(bad), frame[..., ::-1])

    assert not np.array_equal(cv2.imread(str(good), cv2.IMREAD_UNCHANGED),
                              cv2.imread(str(bad), cv2.IMREAD_UNCHANGED))
    assert cv2.imread(str(bad), cv2.IMREAD_UNCHANGED).shape[2] == 4, (
        "the buggy form also drags an alpha channel along, which is the half "
        "that made the captured desktop render as a white sheet")
