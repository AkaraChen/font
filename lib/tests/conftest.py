"""Synthetic dual-width fonts for the fontkit tests.

Real products take hours to build and are gated by tools/fingerprint.py in CI.
These fixtures exist for the opposite job: pinning the *behavioural* differences
between the families down to something that runs in under a second, so the
flags that replaced the forked per-family copies cannot quietly stop mattering.
"""
from __future__ import annotations

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

UPM = 1000
HALF = 500
FULL = 1000


def _square(x0: int, y0: int, x1: int, y1: int):
    pen = TTGlyphPen(None)
    pen.moveTo((x0, y0))
    pen.lineTo((x1, y0))
    pen.lineTo((x1, y1))
    pen.lineTo((x0, y1))
    pen.closePath()
    return pen.glyph()


def build_font(
    path,
    glyphs: dict[str, tuple[int, tuple[int, int, int, int] | None]],
    cmap: dict[int, str],
    *,
    is_fixed_pitch: int = 1,
    panose_proportion: int = 9,
    avg_char_width: int | None = None,
):
    """Write a minimal TTF.

    glyphs maps glyph name -> (advance, bbox or None for a blank glyph).
    cmap maps codepoint -> glyph name. '.notdef' is added automatically.
    """
    order = [".notdef"] + list(glyphs)
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)

    pen_glyphs = {".notdef": _square(0, 0, 10, 10)}
    metrics = {".notdef": (HALF, 0)}
    for name, (adv, box) in glyphs.items():
        pen_glyphs[name] = _square(*box) if box else TTGlyphPen(None).glyph()
        metrics[name] = (adv, box[0] if box else 0)

    fb.setupGlyf(pen_glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable(
        {
            "familyName": "Test Dual",
            "styleName": "Regular",
            "psName": "TestDual-Regular",
        }
    )
    fb.setupOS2()
    fb.setupPost()

    font = fb.font
    font["post"].isFixedPitch = is_fixed_pitch
    os2 = font["OS/2"]
    os2.panose.bFamilyType = 2
    os2.panose.bProportion = panose_proportion
    os2.xAvgCharWidth = HALF if avg_char_width is None else avg_char_width
    fb.save(str(path))
    return path


# Codepoints picked for their East_Asian_Width class, which is what every
# advance rule in this package keys off:
CP_A = ord("A")  # Na → half
CP_ZHONG = ord("中")  # W  → full
CP_NEUTRAL = 0x23F5  # ⏵ N  → half
CP_AMBIGUOUS = 0x25B6  # ▶ A  → user's choice, left alone by default
CP_WIDE = 0x2630  # ☰ W  → full
CP_PUA = 0xE0B0  # Powerline separator (also EAW=A, being PUA)


@pytest.fixture
def make_font(tmp_path):
    def _make(name="test.ttf", **kwargs):
        return build_font(tmp_path / name, **kwargs)

    return _make
