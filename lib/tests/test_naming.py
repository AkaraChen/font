"""The RIBBI split and the name composition it feeds.

Both exist for consumers this repo cannot test against — Windows' GDI font
menu, installers that read only name IDs 1 and 2 — so the assertions here are
the whole gate. `just verify` cannot see them: a fingerprint records the name
table it was given and would happily bless `ID2 = "Light"` forever.
"""

from __future__ import annotations

import pytest
from fontTools.ttLib import TTFont

from fontkit import merge, naming


@pytest.mark.parametrize(
    ("subfamily", "expected"),
    [
        ("Regular", ("", "Regular")),
        ("Bold", ("", "Bold")),
        # The case the whole split exists for: name ID 2 has no `Light`, so the
        # weight moves into name ID 1 and ID 2 falls back to Regular.
        ("Light", ("Light", "Regular")),
        ("Medium", ("Medium", "Regular")),
        # The italic interface. Nothing builds these yet; the point is that
        # adding a slope later does not need a second rename change.
        ("Italic", ("", "Italic")),
        ("Bold Italic", ("", "Bold Italic")),
        ("Light Italic", ("Light", "Italic")),
    ],
)
def test_ribbi_split(subfamily, expected):
    assert naming.ribbi_split(subfamily) == expected


@pytest.mark.parametrize(
    ("subfamily", "id1", "id4"),
    [
        ("Regular", "AKR Sans SC NFM", "AKR Sans SC NFM"),
        ("Bold", "AKR Sans SC NFM", "AKR Sans SC NFM Bold"),
        ("Light", "AKR Sans SC NFM Light", "AKR Sans SC NFM Light"),
        ("Light Italic", "AKR Sans SC NFM Light", "AKR Sans SC NFM Light Italic"),
    ],
)
def test_the_three_legacy_ids_agree(subfamily, id1, id4):
    """ID 4 is built from the ID 1 / ID 2 pair, so it cannot contradict them."""
    assert naming.legacy_family("AKR Sans SC NFM", subfamily) == id1
    assert naming.full_name("AKR Sans SC NFM", subfamily) == id4


def test_compose_upper_cases_the_region_axis():
    assert naming.compose("AKR", "Sans", "jp", "NFM") == "AKR Sans JP NFM"
    assert naming.postscript("AKR Sans JP NFM") == "AKRSansJPNFM"


def _spec(**overrides):
    base = dict(
        family="AKR Sans SC NFM",
        family_ps="AKRSansSCNFM",
        version="1.000",
        sources_note="A + B",
        en_adv=500,
        cjk_adv=1000,
        metrics={},
        profile="coding",
        slope="upright",
        slant_deg=0.0,
        latin="none",
        cjk="as-is",
        import_policy="cjk-side",
        placement="center",
        declares_fixed_grid=True,
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
    return merge.MergeSpec(**base)


def _names(font: TTFont) -> dict[int, str]:
    return {
        rec.nameID: rec.toUnicode()
        for rec in font["name"].names
        if (rec.platformID, rec.platEncID, rec.langID) == (3, 1, 0x409)
    }


@pytest.fixture
def font(make_font, tmp_path):
    path = make_font(glyphs={"A": (500, (0, 0, 400, 700))}, cmap={ord("A"): "A"})
    return TTFont(path)


def test_a_light_does_not_claim_name_id_2(font):
    """`ID2 = "Light"` is not a RIBBI value; Windows would mis-group the face."""
    merge.rename_family(font, "Light", _spec())
    names = _names(font)

    assert names[1] == "AKR Sans SC NFM Light"
    assert names[2] == "Regular"
    assert names[4] == "AKR Sans SC NFM Light"
    assert names[6] == "AKRSansSCNFM-Light"
    # …while the typographic pair keeps the real grouping, which is what a host
    # that understands three weights reads.
    assert names[16] == "AKR Sans SC NFM"
    assert names[17] == "Light"


@pytest.mark.parametrize(
    ("subfamily", "id1", "id2"),
    [("Regular", "AKR Sans SC NFM", "Regular"), ("Bold", "AKR Sans SC NFM", "Bold")],
)
def test_the_ribbi_weights_are_untouched(font, subfamily, id1, id2):
    """Regular and Bold are legal name ID 2 values and stay there.

    This is the half that must NOT change: moving Bold into name ID 1 would
    split every existing two-weight family in two.
    """
    merge.rename_family(font, subfamily, _spec())
    names = _names(font)
    assert (names[1], names[2], names[16], names[17]) == (id1, id2, id1, subfamily)


def test_the_unique_id_stays_unique_across_the_split(font):
    """Name ID 3 keys on ID 16/17, because ID 1/2 stop being a unique pair.

    `AKR Sans SC NFM Light` and `AKR Sans SC NFM` both have `ID2 = "Regular"`,
    so a unique ID built from the legacy pair would collide the moment a Light
    exists.
    """
    light = _names(font)
    merge.rename_family(font, "Light", _spec())
    light = _names(font)[3]

    merge.rename_family(font, "Regular", _spec())
    assert light != _names(font)[3]


def test_a_name_id_1_over_the_windows_budget_is_an_error(font):
    """Caught at build time rather than by a user reading a truncated menu."""
    spec = _spec(family="A" * 28)  # 28 + " Light" = 34
    with pytest.raises(SystemExit, match="31-character"):
        merge.rename_family(font, "Light", spec)
