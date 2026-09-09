"""The two forked behaviours serif kept, now flags."""
from __future__ import annotations

from fontTools.ttLib import TTFont

from fontkit import narrow_symbol_widths as nsw

from conftest import CP_A, CP_AMBIGUOUS, CP_NEUTRAL, CP_WIDE, CP_ZHONG, FULL, HALF

CP_CIRCLE_ZERO = 0x24EA  # ⓪ EAW=N


def _shared_neutral_and_ambiguous(make_font):
    """One outline reachable from both ⏵ (EAW=N) and ▶ (EAW=A), at full width."""
    return make_font(
        glyphs={
            "A": (HALF, (20, 0, 480, 700)),
            "zhong": (FULL, (20, 0, 980, 700)),
            "tri": (FULL, (100, 100, 900, 800)),
        },
        cmap={CP_A: "A", CP_ZHONG: "zhong", CP_NEUTRAL: "tri", CP_AMBIGUOUS: "tri"},
    )


def test_shared_neutral_ambiguous_outline_is_narrowed_by_default(make_font):
    path = _shared_neutral_and_ambiguous(make_font)
    nsw.narrow_font(path, None)

    font = TTFont(path)
    assert font["hmtx"]["tri"][0] == HALF
    font.close()


def test_protect_ambiguous_leaves_it_alone(make_font):
    path = _shared_neutral_and_ambiguous(make_font)
    nsw.narrow_font(path, None, protect_ambiguous=True)

    font = TTFont(path)
    assert font["hmtx"]["tri"][0] == FULL
    font.close()


def _shared_wide_and_neutral(make_font):
    """One outline at half advance reachable from あ (EAW=W) and ⏵ (EAW=N)."""
    return make_font(
        glyphs={
            "A": (HALF, (20, 0, 480, 700)),
            "zhong": (FULL, (20, 0, 980, 700)),
            "bars": (HALF, (50, 100, 450, 700)),
        },
        cmap={CP_A: "A", CP_ZHONG: "zhong", CP_WIDE: "bars", CP_NEUTRAL: "bars"},
    )


def test_widen_shared_fork_duplicates_the_outline(make_font):
    path = _shared_wide_and_neutral(make_font)
    nsw.narrow_font(path, None, widen_shared="fork")

    font = TTFont(path)
    cmap = font.getBestCmap()
    assert cmap[CP_NEUTRAL] == "bars"
    assert cmap[CP_WIDE] != "bars", "the W codepoint must get its own full-width copy"
    assert font["hmtx"]["bars"][0] == HALF
    assert font["hmtx"][cmap[CP_WIDE]][0] == FULL
    font.close()


def test_widen_shared_skip_leaves_the_outline_alone(make_font):
    path = _shared_wide_and_neutral(make_font)
    nsw.narrow_font(path, None, widen_shared="skip")

    font = TTFont(path)
    cmap = font.getBestCmap()
    assert cmap[CP_WIDE] == "bars"
    assert font["hmtx"]["bars"][0] == HALF
    font.close()


def test_unshared_wide_glyph_is_widened_in_both_modes(make_font):
    for mode in nsw.WIDEN_MODES:
        path = make_font(
            name=f"unshared-{mode}.ttf",
            glyphs={
                "A": (HALF, (20, 0, 480, 700)),
                "zhong": (FULL, (20, 0, 980, 700)),
                "bars": (HALF, (50, 100, 450, 700)),
            },
            cmap={CP_A: "A", CP_ZHONG: "zhong", CP_WIDE: "bars"},
        )
        nsw.narrow_font(path, None, widen_shared=mode)

        font = TTFont(path)
        assert font["hmtx"]["bars"][0] == FULL, mode
        font.close()


def test_no_widen_leaves_half_width_wide_glyphs(make_font):
    path = _shared_wide_and_neutral(make_font)
    nsw.narrow_font(path, None, widen=False)

    font = TTFont(path)
    assert font["hmtx"]["bars"][0] == HALF
    font.close()


def test_rejects_an_unknown_widen_mode(make_font):
    path = _shared_wide_and_neutral(make_font)
    try:
        nsw.narrow_font(path, None, widen_shared="nonsense")
    except SystemExit:
        return
    raise AssertionError("expected SystemExit")


# --------------------------------------------------------------------------- #
# Phase 7 (KIT-282) — a narrow codepoint sharing an outline with a wide one
# --------------------------------------------------------------------------- #

CP_FF64 = 0xFF64  # ､ HALFWIDTH IDEOGRAPHIC COMMA — EAW=H, one cell
CP_FE51 = 0xFE51  # ︑ SMALL IDEOGRAPHIC COMMA     — EAW=W, two cells


def _shared_comma_font(make_font):
    """IBM Plex Sans TC/JP/KR map both commas to one glyph, drawn full width."""
    return make_font(
        glyphs={
            "A": (HALF, (20, 0, 480, 700)),
            "zhong": (FULL, (20, 0, 980, 700)),
            "uniFE51": (FULL, (600, 0, 800, 200)),
        },
        cmap={CP_A: "A", CP_ZHONG: "zhong", CP_FF64: "uniFE51", CP_FE51: "uniFE51"},
    )


def test_a_narrow_codepoint_sharing_a_wide_outline_gets_its_own_copy(make_font):
    """Neither narrowing in place nor skipping is right, so fork.

    In place would squash U+FE51, which genuinely needs two cells. Skipping
    leaves U+FF64 two cells wide, and a terminal gives it one — which is the
    `eaw-half` violation that failed the sans TC/JP/KR gate.
    """
    path = _shared_comma_font(make_font)
    nsw.narrow_font(path, None)

    font = TTFont(path, lazy=False)
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]

    assert cmap[CP_FF64] != cmap[CP_FE51], "the two commas must not share a glyph"
    assert hmtx[cmap[CP_FF64]][0] == HALF
    assert hmtx[cmap[CP_FE51]][0] == FULL, "the wide comma must be untouched"
    # Unrelated glyphs are not disturbed.
    assert hmtx[cmap[CP_ZHONG]][0] == FULL
    font.close()


def test_narrow_shared_skip_keeps_the_old_behaviour(make_font):
    """serif asks for this: Sarasa shares outlines across width classes far more
    often, and forking every one of them inflates the glyph count."""
    path = _shared_comma_font(make_font)
    nsw.narrow_font(path, None, narrow_shared="skip")

    font = TTFont(path, lazy=False)
    cmap = font.getBestCmap()
    assert cmap[CP_FF64] == cmap[CP_FE51]
    assert font["hmtx"][cmap[CP_FF64]][0] == FULL
    font.close()


CP_CIRCLE_THREE = 0x2462  # ③ EAW=A
CP_DINGBAT_THREE = 0x2782  # ➂ EAW=N — RHR aliases this onto ③


def test_ambiguous_circled_digit_is_forked_from_its_neutral_dingbat(make_font):
    """①/③ must keep the full cell when ➀/➂ share the outline.

    RHR (and several other CJK donors) map both to one full-cell circle.
    The N dingbat has to occupy one terminal cell; narrowing in place was
    how Round's ③ became a 500×500 bead after a correct CJK import.
    """
    path = make_font(
        glyphs={
            "A": (HALF, (20, 0, 480, 700)),
            "zhong": (FULL, (20, 0, 980, 700)),
            "three": (FULL, (50, 50, 950, 950)),
        },
        cmap={
            CP_A: "A",
            CP_ZHONG: "zhong",
            CP_CIRCLE_THREE: "three",
            CP_DINGBAT_THREE: "three",
        },
    )
    nsw.narrow_font(path, None)

    font = TTFont(path)
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    assert cmap[CP_CIRCLE_THREE] != cmap[CP_DINGBAT_THREE]
    assert hmtx[cmap[CP_CIRCLE_THREE]][0] == FULL
    glyph = font["glyf"][cmap[CP_CIRCLE_THREE]]
    assert abs((glyph.yMax - glyph.yMin) / (glyph.xMax - glyph.xMin) - 1.0) < 0.05
    assert hmtx[cmap[CP_DINGBAT_THREE]][0] == HALF
    dingbat = font["glyf"][cmap[CP_DINGBAT_THREE]]
    dw = dingbat.xMax - dingbat.xMin
    dh = dingbat.yMax - dingbat.yMin
    assert dw <= HALF
    assert abs(dh / dw - 1.0) < 0.08, (dw, dh)
    font.close()


def test_neutral_circled_zero_is_fitted_uniformly(make_font):
    """⓪ must occupy one cell, but X-only fit would make it twice as tall as wide."""
    path = make_font(
        glyphs={
            "A": (HALF, (20, 0, 480, 700)),
            "zhong": (FULL, (20, 0, 980, 700)),
            "zero": (FULL, (50, 50, 950, 950)),
        },
        cmap={CP_A: "A", CP_ZHONG: "zhong", CP_CIRCLE_ZERO: "zero"},
    )
    nsw.narrow_font(path, None)

    font = TTFont(path)
    glyph = font["glyf"]["zero"]
    assert font["hmtx"]["zero"][0] == HALF
    width = glyph.xMax - glyph.xMin
    height = glyph.yMax - glyph.yMin
    assert width <= HALF
    assert abs(height / width - 1.0) < 0.08, (width, height)
    font.close()
