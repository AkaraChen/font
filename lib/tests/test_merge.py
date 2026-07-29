"""The merge engine's behavioural forks, pinned to something that runs in a second.

Four families used to reach these behaviours by having four copies of the same
file. Now they reach them by declaring options, which is only an improvement if
the options still *do* something — a flag nobody tests is a flag that quietly
stops mattering, and the next person deletes it as dead.

The heavyweight gate is elsewhere and stays there: `just verify <family>` diffs
a real build against a committed fingerprint. These tests are for the decisions
that gate cannot see, most of all the ones about faces this repo does not build
yet — the `text` profile and the italic slope.
"""

from __future__ import annotations

import pytest
from fontTools.ttLib import TTFont

from fontkit import merge
from fontkit.manifest import load_manifest

from conftest import CP_A, CP_NEUTRAL, CP_WIDE, CP_ZHONG

REPO = __import__("pathlib").Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- #
# import policy
# --------------------------------------------------------------------------- #


def _spec(**overrides):
    base = dict(
        family="Test Dual",
        family_ps="TestDual",
        version="1.000",
        sources_note="A + B",
        en_adv=500,
        cjk_adv=1000,
        metrics={
            "hhea_ascent": 950,
            "hhea_descent": -250,
            "hhea_line_gap": 0,
            "os2_typo_asc": 880,
            "os2_typo_desc": -220,
            "os2_typo_gap": 0,
            "os2_win_asc": 1032,
            "os2_win_desc": 290,
        },
        profile="coding",
        slope="upright",
        slant_deg=0.0,
        latin="none",
        cjk="as-is",
        import_policy="cjk-side",
        placement="center",
        glyph_prefix="cjk.",
        required_sample="",
        latin_subset="none",
        latin_src_adv=None,
        latin_target_upm=None,
        drop_hinting_on_upem_change=False,
        set_weight_class=False,
        recalc_bounds=False,
        widen_wide_base_glyphs=False,
        drop_vertical_metrics=False,
        check_glyph_budget=False,
    )
    base.update(overrides)
    # The profile decides the grid declaration, so the helper must not let a
    # test set `profile="text"` and still get a face that claims a fixed grid —
    # that combination cannot come out of `spec_from_manifest`.
    base.setdefault(
        "declares_fixed_grid",
        merge.PROFILE_RULES[base["profile"]].declares_fixed_grid,
    )
    return merge.MergeSpec(**base)


LATIN_CMAP = {CP_A: "A", CP_NEUTRAL: "arrow"}
CJK_CMAP = {CP_ZHONG: "zhong", CP_A: "A.cjk", 0x0416: "zhe"}


@pytest.mark.parametrize(
    "policy,expected",
    [
        # The donor's own Latin is a different design — drop it.
        ("cjk-side", {CP_ZHONG}),
        # …unless the base does not cover the codepoint at all.
        ("cjk-side-or-missing", {CP_ZHONG, 0x0416}),
        ("east-asian-width", {CP_ZHONG, 0x0416}),
    ],
)
def test_import_policy_decides_what_the_donor_contributes(policy, expected):
    got = merge.codepoints_to_import(
        _spec(import_policy=policy), LATIN_CMAP, CJK_CMAP
    )
    assert set(got) == expected


def test_east_asian_width_policy_takes_wide_codepoints_the_base_already_covers():
    """A W/F codepoint needs a full cell; the donor already draws it for one."""
    latin = {CP_WIDE: "kana.base"}
    got = merge.codepoints_to_import(
        _spec(import_policy="east-asian-width"), latin, {CP_WIDE: "kana.donor"}
    )
    assert got == {CP_WIDE: "kana.donor"}
    # The narrower policies leave the base's drawing alone.
    assert merge.codepoints_to_import(
        _spec(import_policy="cjk-side-or-missing"), latin, {CP_WIDE: "kana.donor"}
    ) == {CP_WIDE: "kana.donor"}  # U+3042 is in the CJK ranges either way


# --------------------------------------------------------------------------- #
# the metrics split — 2:1 and the line box are separate steps
# --------------------------------------------------------------------------- #


@pytest.fixture
def font(make_font):
    path = make_font(
        glyphs={"A": (600, (50, 0, 550, 700))},
        cmap={CP_A: "A"},
        is_fixed_pitch=0,
        panose_proportion=0,
        avg_char_width=1234,
    )
    return TTFont(path)


def test_vertical_metrics_do_not_declare_a_grid(font):
    """The line box is a reading decision; it must not smuggle in the 2:1 claim.

    Phase 6's `text` profile calls this and nothing else, so anything about the
    terminal cell that leaks in here would ship in a face that has no cells.
    """
    merge.apply_vertical_metrics(font, _spec().metrics)

    assert font["hhea"].ascent == 950
    assert font["OS/2"].usWinDescent == 290
    assert font["OS/2"].fsSelection & 0x80  # USE_TYPO_METRICS
    # Untouched: these belong to declare_strict_2to1.
    assert font["post"].isFixedPitch == 0
    assert font["OS/2"].panose.bProportion == 0
    assert font["OS/2"].xAvgCharWidth == 1234


def test_strict_2to1_is_callable_on_its_own(font):
    merge.declare_strict_2to1(font, 500)

    assert font["post"].isFixedPitch == 1
    assert font["OS/2"].panose.bProportion == 9
    assert font["OS/2"].xAvgCharWidth == 500
    # …and it is not a line-box step.
    assert font["hhea"].ascent == 800


# --------------------------------------------------------------------------- #
# slope — the italic interface, exercised without producing an italic
# --------------------------------------------------------------------------- #


def test_upright_is_written_not_assumed(font):
    font["post"].italicAngle = -9.5
    font["OS/2"].fsSelection |= 0x01
    font["head"].macStyle |= 0x02

    merge.apply_slope(font, "upright")

    assert font["post"].italicAngle == 0
    assert not font["OS/2"].fsSelection & 0x01
    assert not font["head"].macStyle & 0x02


def test_italic_sets_every_bit_a_host_might_read(font):
    merge.apply_slope(font, "italic", angle=7.5)

    assert font["post"].italicAngle == -7.5
    assert font["OS/2"].fsSelection & 0x01
    assert not font["OS/2"].fsSelection & 0x40  # ITALIC and REGULAR are exclusive
    assert font["head"].macStyle & 0x02


def test_slope_leaves_the_weight_bits_alone(font):
    """Bold-ness belongs to the weight; clearing it here would undo the donor."""
    font["OS/2"].fsSelection |= 0x20
    font["head"].macStyle |= 0x01

    merge.apply_slope(font, "italic", angle=7.5)

    assert font["OS/2"].fsSelection & 0x20
    assert font["head"].macStyle & 0x01


def test_unknown_slope_is_refused(font):
    with pytest.raises(SystemExit):
        merge.apply_slope(font, "oblique")


# --------------------------------------------------------------------------- #
# a whole merge, on synthetic fonts
# --------------------------------------------------------------------------- #


def _merged(tmp_path, make_font, **spec_overrides):
    latin = make_font(
        name="latin.ttf",
        glyphs={"A": (500, (50, 0, 450, 700))},
        cmap={CP_A: "A"},
        # Deliberately un-declared, so "the merge set this" and "the donor
        # already had it" cannot be confused for each other.
        is_fixed_pitch=0,
        panose_proportion=0,
        avg_char_width=1234,
    )
    cjk = make_font(
        name="cjk.ttf",
        glyphs={"zhong": (1000, (0, 0, 1000, 800)), "A": (700, (0, 0, 700, 700))},
        cmap={CP_ZHONG: "zhong", CP_A: "A"},
    )
    out = tmp_path / "out" / "TestDual-Regular.ttf"
    merge.merge_pair(latin, cjk, out, "Regular", _spec(**spec_overrides))
    return TTFont(out)


def test_coding_profile_declares_the_grid(tmp_path, make_font):
    font = _merged(tmp_path, make_font)

    assert font["post"].isFixedPitch == 1
    assert font["OS/2"].xAvgCharWidth == 500
    cmap = font.getBestCmap()
    assert font["hmtx"][cmap[CP_ZHONG]][0] == 1000
    assert font["hmtx"][cmap[CP_A]][0] == 500  # the base's Latin, not the donor's
    assert font["name"].getDebugName(1) == "Test Dual"
    assert "A + B" in font["name"].getDebugName(5)


def test_text_profile_ships_the_same_glyphs_without_the_2to1_claim(tmp_path, make_font):
    """`text` is the profile Phase 6 adds. Strict 2:1 is a coding-only constraint;
    optical stroke matching (the embolden, one step earlier) applies to both."""
    font = _merged(tmp_path, make_font, profile="text")

    assert font["post"].isFixedPitch == 0
    assert font["OS/2"].xAvgCharWidth != 500
    # Everything a reader cares about is still there.
    assert font["hhea"].ascent == 950
    assert CP_ZHONG in font.getBestCmap()


def test_italic_slope_reaches_the_product(tmp_path, make_font):
    font = _merged(tmp_path, make_font, slope="italic", slant_deg=7.5)

    assert font["post"].italicAngle == -7.5
    assert font["head"].macStyle & 0x02


def test_glyph_prefix_keeps_a_name_clash_from_overwriting_the_base(tmp_path, make_font):
    font = _merged(tmp_path, make_font, import_policy="cjk-side-or-missing")
    order = font.getGlyphOrder()
    assert "A" in order  # the base's
    assert "cjk.A" not in order  # U+0041 is not imported: the base has it


def test_a_missing_sample_glyph_fails_the_build(tmp_path, make_font):
    with pytest.raises(SystemExit):
        _merged(tmp_path, make_font, required_sample="霞")


# --------------------------------------------------------------------------- #
# the manifests the repo actually ships
# --------------------------------------------------------------------------- #

MERGING_FAMILIES = ["casual", "handwriting", "rounded", "sans", "typewriter"]


@pytest.mark.parametrize("family", MERGING_FAMILIES)
def test_every_merging_family_resolves_a_spec_for_every_weight(family):
    manifest = load_manifest(REPO / family / "font.toml")
    for weight in manifest.build.weights:
        spec = merge.spec_from_manifest(manifest, weight.capitalize())
        assert spec.en_adv * 2 == spec.cjk_adv
        assert spec.family_ps


@pytest.mark.parametrize("family", MERGING_FAMILIES)
def test_calibration_is_per_weight_not_regulars_reused(family):
    """Adding Light means re-measuring the CJK stem against *that* weight.

    An engine that silently fell back to Regular would ship a Light whose CJK is
    as heavy as the Regular's, and nothing downstream would notice. handwriting
    took a Light in Phase 6 and has `[calibration.light]`; the rest have not, and
    for them asking for one must still be an error rather than a silent Regular.
    """
    manifest = load_manifest(REPO / family / "font.toml")
    if "light" in manifest.calibration:
        spec = merge.spec_from_manifest(manifest, "Light")
        regular = merge.spec_from_manifest(manifest, "Regular")
        # Not asserting it is *lighter* — that is the build's job to measure —
        # only that it resolved from its own entry.
        assert spec.family_ps == regular.family_ps
        return
    with pytest.raises(SystemExit, match="calibration"):
        merge.spec_from_manifest(manifest, "Light")


# --------------------------------------------------------------------------- #
# Phase 6 — the text profile is a scene, not a family option
# --------------------------------------------------------------------------- #


def test_profile_overrides_the_familys_cell_policy(tmp_path, make_font):
    """A family declares what its donors need; the profile declares the scene.

    handwriting's `[merge]` says `placement = "fit"` because a terminal sizes
    cells from East_Asian_Width. A reading face has no cells, so the same
    manifest must not produce a face whose CJK was snapped to a grid.
    """
    manifest = load_manifest(REPO / "handwriting" / "font.toml")

    coding = merge.spec_from_manifest(manifest, "Regular", profile="coding")
    text = merge.spec_from_manifest(manifest, "Regular", profile="text")

    assert coding.placement == "fit"
    assert coding.import_policy == "east-asian-width"
    assert coding.declares_fixed_grid

    assert text.placement == "native"
    assert text.import_policy == "cjk-side-plus-cjk-punctuation"
    assert not text.declares_fixed_grid
    # The terminal-cell repair goes with the terminal.
    assert not text.widen_wide_base_glyphs
    # …while the optical work does not: both profiles read the same
    # [calibration.<weight>], because `cjk-prepared` is shared between them.
    assert text.slant_deg == coding.slant_deg


def test_a_second_profile_is_a_second_family_name():
    """Two profiles under one family name would collide in a font menu."""
    manifest = load_manifest(REPO / "handwriting" / "font.toml")

    coding = merge.spec_from_manifest(manifest, "Regular", profile="coding")
    text = merge.spec_from_manifest(manifest, "Regular", profile="text")

    assert coding.family != text.family
    assert coding.family_ps != text.family_ps
    # Inherited, not restated: the override says what differs and nothing else.
    assert manifest.naming.rfn_note


def test_text_withdraws_the_mono_claim_a_donor_arrived_with(font):
    """Both donors are monospaced, so `isFixedPitch` arrives set.

    Not calling `declare_strict_2to1` is not enough — the flag has to be cleared,
    or the reading face turns up in every 'monospace only' font picker.
    """
    font["post"].isFixedPitch = 1
    font["OS/2"].panose.bProportion = 9

    merge.declare_proportional(font)

    assert font["post"].isFixedPitch == 0
    assert font["OS/2"].panose.bProportion != 9


def test_ambiguous_punctuation_comes_from_whoever_drew_a_whole_cell():
    """… is full width in Chinese typography — but only if the donor drew it so.

    LXGW WenKai draws … and — for the full cell and ‘ ’ “ ” · at 350/1000, as
    part of its own proportional Latin. Taking the 350 would put WenKai's Latin
    quotes next to Radon's Latin letters, which is worse than either font alone,
    so the rule is asked of the donor rather than assumed from the codepoint.
    """
    spec = _spec(profile="text", import_policy="cjk-side-plus-cjk-punctuation")
    latin_cmap = {0x2026: "ellipsis", 0x201C: "quotedblleft", CP_A: "A"}
    cjk_cmap = {
        CP_ZHONG: "zhong",
        0x2026: "wk.ellipsis",
        0x201C: "wk.quotedblleft",
    }
    advances = {"zhong": 1000, "wk.ellipsis": 1000, "wk.quotedblleft": 350}

    taken = merge.codepoints_to_import(spec, latin_cmap, cjk_cmap, advances)

    assert taken[0x2026] == "wk.ellipsis"  # full cell — the CJK donor's
    assert 0x201C not in taken  # 350 — leave the Latin donor's alone
    assert CP_A not in taken  # never take the donor's Latin
