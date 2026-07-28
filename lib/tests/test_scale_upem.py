"""UPM normalisation — the first pass over a CJK master, so everything after it
(embolden strengths, the 2:1 advance gate) is expressed in product units.

serif is the family that needs it: Neo ZhiSong is drawn on 2048 and the product
grid is 1000. The pass used to be a heredoc inside 03-prepare-cjk.sh, where its
one interesting property — that a master already on the grid is passed through
untouched rather than round-tripped through a scale of 1.0 — was untested.
"""

from __future__ import annotations

import pytest
from fontTools.ttLib import TTFont

from conftest import CP_A, CP_ZHONG, FULL, HALF

from fontkit import scale_upem

GLYPHS = {"A": (HALF, (50, 0, 450, 700)), "zhong": (FULL, (0, 0, 1000, 900))}
CMAP = {CP_A: "A", CP_ZHONG: "zhong"}


def _advance(path, codepoint):
    font = TTFont(path)
    try:
        return font["hmtx"][font.getBestCmap()[codepoint]][0], font["head"].unitsPerEm
    finally:
        font.close()


@pytest.fixture()
def dual_2048(make_font):
    """A dual-width font declaring a 2048 grid — serif's CJK master's shape."""
    path = make_font(name="src-2048.ttf", glyphs=GLYPHS, cmap=CMAP)
    font = TTFont(path)
    font["head"].unitsPerEm = 2048
    font.save(path)
    font.close()
    return path


def test_scales_to_the_product_grid(dual_2048, tmp_path):
    dst = tmp_path / "scaled.ttf"
    assert scale_upem.scale_font(dual_2048, dst, 1000) == 2048

    advance, upem = _advance(dst, CP_A)
    assert upem == 1000
    # 500 units on a 2048 grid is not 500 units on a 1000 grid: advances move
    # with the scale, which is why this has to run before anything measures them.
    assert advance == round(HALF * 1000 / 2048)


def test_a_master_already_on_the_grid_keeps_its_advances(make_font, tmp_path):
    src = make_font(name="src-1000.ttf", glyphs=GLYPHS, cmap=CMAP)
    dst = tmp_path / "scaled.ttf"
    assert scale_upem.scale_font(src, dst, 1000) == 1000

    assert _advance(dst, CP_A) == (HALF, 1000)
    assert _advance(dst, CP_ZHONG) == (FULL, 1000)


def test_missing_source_is_an_error_not_a_traceback(tmp_path):
    argv = [str(tmp_path / "nope.ttf"), str(tmp_path / "out.ttf"), "--upem", "1000"]
    assert scale_upem.main(argv) == 2


def test_nonsense_upem_is_rejected(dual_2048, tmp_path):
    argv = [str(dual_2048), str(tmp_path / "out.ttf"), "--upem", "0"]
    assert scale_upem.main(argv) == 2
