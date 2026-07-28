"""The mono advertisement, and the head bbox this module must NOT touch."""
from __future__ import annotations

from fontTools.ttLib import TTFont

from fontkit import fix_terminal_metrics as ftm

from conftest import CP_A, CP_ZHONG, FULL, HALF


def _font_with_an_oversized_glyph(make_font):
    # U+2E3B (three-em dash) is deliberately 3 em wide in these products, and is
    # the glyph that used to be squeezed out of head's bbox by the removed
    # --keep-bbox workaround.
    return make_font(
        glyphs={
            "A": (HALF, (20, 0, 480, 700)),
            "zhong": (FULL, (20, 0, 980, 700)),
            "threeemdash": (3000, (0, 300, 2900, 360)),
        },
        cmap={CP_A: "A", CP_ZHONG: "zhong", 0x2E3B: "threeemdash"},
        avg_char_width=832,
    )


def test_fixes_the_mono_advertisement(make_font):
    path = make_font(
        glyphs={"A": (HALF, (20, 0, 480, 700)), "zhong": (FULL, (20, 0, 980, 700))},
        cmap={CP_A: "A", CP_ZHONG: "zhong"},
        is_fixed_pitch=0,
        panose_proportion=3,
        avg_char_width=832,
    )
    ftm.fix_font(path)

    font = TTFont(path)
    assert font["OS/2"].xAvgCharWidth == HALF
    assert font["post"].isFixedPitch == 1
    assert font["OS/2"].panose.bProportion == 9
    font.close()


def test_head_bbox_still_covers_every_glyph(make_font):
    """KIT-284: the tight-bbox workaround is gone and must stay gone.

    OpenType says head.xMin/xMax cover *all* glyphs. serif used to ship a
    narrower bbox to stop hosts reading it as the terminal cell width; that
    report turned out to be a terminal bug, so the non-conformant table is not
    worth carrying. If someone reintroduces it, this fails.
    """
    path = _font_with_an_oversized_glyph(make_font)
    ftm.fix_font(path)

    font = TTFont(path, lazy=False)
    assert font["head"].xMax == 2900
    font.close()


def test_dry_run_touches_nothing(make_font):
    path = _font_with_an_oversized_glyph(make_font)
    before = path.read_bytes()
    ftm.fix_font(path, dry_run=True)
    assert path.read_bytes() == before
