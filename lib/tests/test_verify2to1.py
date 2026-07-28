"""compact vs dense — neither profile is a superset of the other."""
from __future__ import annotations

import string

from fontkit import verify2to1 as v

from conftest import CP_A, CP_PUA, CP_ZHONG, FULL, HALF

COMPACT = v.PROFILES["compact"]
DENSE = v.PROFILES["dense"]


def _ok_font(make_font, name="ok.ttf", extra=None, **overrides):
    """A font that satisfies both profiles: full ASCII, the fixed CJK samples.

    extra maps codepoint -> advance for anything the test wants on top.
    """
    glyphs = {}
    cmap = {}
    for i, ch in enumerate(string.printable[:95]):
        cp = ord(ch)
        if not 0x20 <= cp <= 0x7E:
            continue
        glyphs[f"ascii{cp:02X}"] = (HALF, (20, 0, 480, 700))
        cmap[cp] = f"ascii{cp:02X}"
    for cp in set(v.CJK_FIXED) | set(v.CJK_FIXED_COMPACT_EXTRA):
        glyphs[f"cjk{cp:04X}"] = (FULL, (20, 0, 980, 700))
        cmap[cp] = f"cjk{cp:04X}"
    for cp, adv in (extra or {}).items():
        glyphs[f"x{cp:04X}"] = (adv, (20, 0, adv - 20, 700))
        cmap[cp] = f"x{cp:04X}"
    kwargs = {"glyphs": glyphs, "cmap": cmap}
    kwargs.update(overrides)
    return make_font(name=name, **kwargs)


def _rc(path, profile, **kwargs):
    rc, _lines = v.verify_font(path, profile=profile, **kwargs)
    return rc


def test_a_clean_font_passes_both_profiles(make_font):
    path = _ok_font(make_font)
    assert _rc(path, COMPACT) == 0
    assert _rc(path, DENSE) == 0


def test_only_compact_gates_xavgcharwidth(make_font):
    path = _ok_font(make_font, avg_char_width=832)
    assert _rc(path, COMPACT) == 1
    assert _rc(path, DENSE) == 0, "serif's products do not hold this invariant"


def test_only_compact_requires_ascii_to_be_present(make_font):
    path = _ok_font(make_font)
    from fontTools.ttLib import TTFont

    font = TTFont(path)
    for table in font["cmap"].tables:
        table.cmap.pop(ord("~"), None)
    font.save(path)
    font.close()

    assert _rc(path, COMPACT) == 1
    assert _rc(path, DENSE) == 0


def test_both_profiles_gate_the_mono_flags(make_font):
    for profile in (COMPACT, DENSE):
        path = _ok_font(make_font, name=f"mono-{profile.name}.ttf", is_fixed_pitch=0)
        assert _rc(path, profile) == 1


def test_both_profiles_gate_missing_cjk_unless_allowed(make_font):
    glyphs = {"A": (HALF, (20, 0, 480, 700))}
    cmap = {CP_A: "A"}
    for cp in range(0x20, 0x7F):
        glyphs[f"ascii{cp:02X}"] = (HALF, (20, 0, 480, 700))
        cmap[cp] = f"ascii{cp:02X}"
    path = make_font(name="nocjk.ttf", glyphs=glyphs, cmap=cmap)

    for profile in (COMPACT, DENSE):
        assert _rc(path, profile) == 1
        assert _rc(path, profile, require_cjk=False) == 0


def test_nerd_scan_range_differs_between_profiles(make_font):
    # U+F8FF sits in the BMP PUA block but outside the published Nerd ranges.
    # compact sweeps all of PUA and gates it; dense walks NERD_RANGES and
    # never looks at it. Both see the Powerline separator at U+E0B0.
    path = _ok_font(make_font, name="nerd.ttf", extra={CP_PUA: HALF, 0xF8FF: FULL})

    assert _rc(path, COMPACT, check_nerd=True) == 1
    assert _rc(path, DENSE, check_nerd=True) == 0


def test_expect_half_pins_the_cell(make_font):
    path = _ok_font(make_font)
    assert _rc(path, COMPACT, expect_half=HALF) == 0
    assert _rc(path, COMPACT, expect_half=600) == 1


def test_missing_reference_glyph_is_a_usage_error(make_font):
    path = make_font(
        name="noA.ttf",
        glyphs={"zhong": (FULL, (20, 0, 980, 700))},
        cmap={CP_ZHONG: "zhong"},
    )
    assert _rc(path, COMPACT) == 2
    assert _rc(path, DENSE) == 2


def test_dense_gates_four_more_bracket_punctuation_marks():
    assert set(DENSE.cjk_punct) - set(COMPACT.cjk_punct) == {
        0x3014,
        0x3015,
        0x3016,
        0x3017,
    }


def test_dense_samples_cjk_far_more_densely():
    assert len(v.collect_full_required(DENSE)) > 2 * len(
        v.collect_full_required(COMPACT)
    )
