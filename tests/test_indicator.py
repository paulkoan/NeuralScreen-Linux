"""The ON/OFF badge: a 3x5 bitmap font, drawn by the renderer, never into the frame.

Two properties are load-bearing. The glyphs have to be readable at the size they are drawn, and
the badge has to be drawn *after* the texture upload - if it were painted into the frame, every
saved PNG and every recording would carry the UI.
"""
from __future__ import annotations

import numpy as np
import pytest

from minimal.display import glyph_pixels, indicator_layout


def _render(text: str, scale: int = 1) -> list[str]:
    """The glyphs as ASCII, so a test can look at them the way a person does."""
    width = indicator_layout(text, 0, 0, scale)[2]
    height = 5 * scale
    grid = [["." for _ in range(width)] for _ in range(height)]
    for (x, y, w, h), lit in glyph_pixels(text, 0, 0, scale):
        if not lit:
            continue
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                grid[yy][xx] = "#"
    return ["".join(row) for row in grid]


def test_the_badge_is_wider_for_off():
    assert indicator_layout("ON", 0, 0, 1)[2] == 8      # 2 glyphs x (3 + 1 gap)
    assert indicator_layout("OFF", 0, 0, 1)[2] == 12    # 3 glyphs


def test_scale_multiplies_everything():
    assert indicator_layout("ON", 5, 7, 4) == (5, 7, 32, 20)


def test_on_reads_as_on():
    rows = _render("ON")
    assert len(rows) == 5
    # O is a ring: the middle column of the second row is a hole.
    assert rows[1][1] == "."
    # N is not: its second row is solid.
    assert rows[1][5] == "#"


def test_off_reads_as_off():
    rows = _render("OFF")
    # O: 3,2,2,2,3 (# per row); F: 3,1,2,1,1. Three glyphs, so the row sums are:
    assert [row.count("#") for row in rows] == [9, 4, 6, 4, 5]


def test_every_glyph_has_a_full_five_rows():
    for char in "ONF":
        assert len(glyph_pixels(char, 0, 0, 1)) == 15, f"{char} is not 3x5"


def test_a_letter_outside_the_font_is_blank_not_a_crash():
    cells = glyph_pixels("Z", 0, 0, 2)
    assert all(not lit for _, lit in cells)


def test_the_badge_is_drawn_after_the_frame_is_uploaded():
    """Painting it into the frame would put it in every screenshot and recording."""
    source = open("minimal/display.py", encoding="utf-8").read()
    update = source.index("SDL_UpdateTexture")
    draw = source.index("self._draw_indicator()")
    present = source.index("SDL_RenderPresent", draw)
    assert update < draw < present


def test_the_loop_tells_the_badge_what_the_frame_was():
    source = open("minimal/loop.py", encoding="utf-8").read()
    assert source.count("setter(not self.bypass)") >= 2, (
        "both the serial and the pipelined path show frames; both must set the badge")
