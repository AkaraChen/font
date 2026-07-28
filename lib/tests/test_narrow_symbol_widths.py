"""The two forked behaviours serif kept, now flags."""
from __future__ import annotations

from fontTools.ttLib import TTFont

from fontkit import narrow_symbol_widths as nsw

from conftest import CP_A, CP_AMBIGUOUS, CP_NEUTRAL, CP_WIDE, CP_ZHONG, FULL, HALF


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
    """One outline at half advance reachable from ☰ (EAW=W) and ⏵ (EAW=N)."""
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
