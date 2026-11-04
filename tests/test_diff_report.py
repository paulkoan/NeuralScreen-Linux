"""How far the pass moved the picture, and a picture of that movement.

"Can't see a difference" is not the same as "no difference": on stream content the pass is
subtle, and a one- or two-level shift is invisible side by side. These functions turn it into
numbers and into an image, and they have to be right when the answer is "nothing changed" too.
"""
from __future__ import annotations

import numpy as np
import pytest

from minimal.loop import amplified_diff, diff_metrics


def _frame(value: int = 100, h: int = 8, w: int = 8) -> np.ndarray:
    frame = np.full((h, w, 4), value, dtype=np.uint8)
    frame[..., 3] = 255
    return frame


def test_an_unchanged_frame_is_zero_and_infinite_psnr():
    metrics = diff_metrics(_frame(), _frame())
    assert metrics["mad"] == 0.0
    assert metrics["max"] == 0
    assert metrics["over_2"] == 0.0 and metrics["over_8"] == 0.0
    assert metrics["psnr"] == float("inf")


def test_a_uniform_shift_shows_up_everywhere():
    before = _frame(100)
    after = _frame(104)
    metrics = diff_metrics(before, after)
    assert metrics["mad"] == pytest.approx(4.0)
    assert metrics["mad_rgb"] == pytest.approx([4.0, 4.0, 4.0])
    assert metrics["max"] == 4
    assert metrics["over_2"] == 1.0, "every pixel moved by more than 2"
    assert metrics["over_8"] == 0.0, "none moved by more than 8"
    assert 30 < metrics["psnr"] < 40


def test_a_few_pixels_moving_hard_is_not_hidden_by_the_mean():
    before = _frame(100)
    after = before.copy()
    after[:2, :2, :3] = 200            # 4 of 64 pixels, +100
    metrics = diff_metrics(before, after)
    assert metrics["mad"] < 10, "the mean stays small"
    assert metrics["max"] == 100, "the maximum is what catches it"
    assert metrics["over_8"] == pytest.approx(4 / 64)


def test_the_alpha_channel_is_ignored():
    """Alpha is 255 on both sides and would otherwise dilute the mean by a quarter."""
    before = _frame(100)
    after = _frame(100)
    after[..., 3] = 0
    assert diff_metrics(before, after)["mad"] == 0.0


def test_the_diff_image_is_grey_where_nothing_changed():
    out = amplified_diff(_frame(), _frame(), gain=8)
    assert out.shape == (8, 8, 4)
    assert out[..., 3].min() == 255
    assert (out[..., :3] == 128).all()


def test_the_diff_image_amplifies_and_clips():
    before = _frame(100)
    after = _frame(101)
    out = amplified_diff(before, after, gain=8)
    assert (out[..., :3] == 136).all(), "one level at gain 8 is 8 above mid-grey"

    big = amplified_diff(_frame(0), _frame(255), gain=8)
    assert (big[..., :3] == 255).all(), "clipped, not wrapped"


def test_the_cli_offers_both():
    source = open("minimal/__main__.py", encoding="utf-8").read()
    for flag in ('"--report-diff"', '"--save-diff"', '"--diff-gain"', '"--ab-alternate"'):
        assert flag in source


def test_a_diff_run_asks_for_the_pixels():
    """Without the pixels there is nothing to compare - a bare reply carries no image."""
    source = open("minimal/__main__.py", encoding="utf-8").read()
    assert "args.report_diff or args.save_diff" in source
