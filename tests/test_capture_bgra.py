"""The synthetic card can hand itself over in BGRA, so the handoff is measurable with no screen.

The stock card is RGBA, so a timing run on it never exercises the BGRA path - which is exactly
the question the plan could not answer without a display. Building the card in BGRA order once,
when the fixture is made, keeps the fixture free: the swap is not part of the per-frame cost.
"""
import numpy as np

from minimal.capture import SyntheticCapture, open_capture


def test_bgra_card_is_the_rgba_card_with_red_and_blue_swapped():
    rgba = SyntheticCapture(width=16, height=8).grab()
    bgra = SyntheticCapture(width=16, height=8, bgra=True).grab()
    assert np.array_equal(bgra, rgba[..., [2, 1, 0, 3]])


def test_the_flag_is_reported_so_the_worker_can_stamp_the_frame():
    assert SyntheticCapture(width=8, height=8).bgra is False
    assert SyntheticCapture(width=8, height=8, bgra=True).bgra is True


def test_the_two_cards_differ_in_the_colour_channels_only():
    rgba = SyntheticCapture(width=16, height=8).grab()
    bgra = SyntheticCapture(width=16, height=8, bgra=True).grab()
    # Alpha and shape are untouched; the red and blue ramps are the ones that swap.
    assert np.array_equal(rgba[..., 3], bgra[..., 3])
    assert not np.array_equal(rgba[..., 0], bgra[..., 0])


def test_open_capture_passes_the_order_through():
    source = open_capture("synthetic", width=8, height=4, bgra=True)
    assert source.bgra is True
    assert source.resolution == (8, 4)
