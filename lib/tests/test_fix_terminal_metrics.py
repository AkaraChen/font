"""--keep-bbox is the one behavioural difference between serif and the rest."""
from __future__ import annotations

from fontTools.ttLib import TTFont

from fontkit import fix_terminal_metrics as ftm

from conftest import CP_A, CP_ZHONG, FULL, HALF


def _font_with_an_oversized_glyph(make_font):
    # U+2E3B (three-em dash) is deliberately 3 em wide in these products, so it
    # is exactly the glyph that blows head.xMax out past the terminal cell.
    return make_font(
        glyphs={
            "A": (HALF, (20, 0, 480, 700)),
            "zhong": (FULL, (20, 0, 980, 700)),
            "threeemdash": (3000, (0, 300, 2900, 360)),
        },
        cmap={CP_A: "A", CP_ZHONG: "zhong", 0x2E3B: "threeemdash"},
        avg_char_width=832,
    )


def test_always_fixes_the_mono_advertisement(make_font):
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


def test_keep_bbox_pins_head_to_half_and_full_glyphs(make_font):
    path = _font_with_an_oversized_glyph(make_font)
    ftm.fix_font(path, keep_bbox=True)

    font = TTFont(path, lazy=False)
    assert font["head"].xMax == 980, "three-em dash must not set the cell width"
    font.close()


def test_without_keep_bbox_fonttools_recomputes_head_on_save(make_font):
    """pixel / rounded / sans / typewriter have always shipped this.

    Their copy of the script computed the tight bbox and then let
    TTFont.recalcBBoxes overwrite it during save. Flipping that is a product
    change, not a refactor, so the default must keep losing the tight bbox.
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
