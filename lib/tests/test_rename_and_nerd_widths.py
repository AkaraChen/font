"""The two modules that were byte-identical across families — no flags, no drift."""
from __future__ import annotations

from fontTools.ttLib import TTFont

from fontkit import fix_nerd_widths as fnw
from fontkit import rename_nerd_family as rnf

from conftest import CP_A, CP_PUA, CP_ZHONG, FULL, HALF


def test_rename_rewrites_every_name_id_and_the_filename(make_font, tmp_path):
    path = make_font(
        name="Whatever-Bold.ttf",
        glyphs={"A": (HALF, (20, 0, 480, 700))},
        cmap={CP_A: "A"},
    )
    rc = rnf.main(
        ["--family", "Test NFM", "--family-ps", "TestNFM", "--rename-file", str(path)]
    )
    assert rc == 0

    out = tmp_path / "TestNFM-Bold.ttf"
    assert out.is_file()
    assert not path.exists()

    font = TTFont(out)
    name = font["name"]
    assert name.getName(1, 3, 1, 0x409).toUnicode() == "Test NFM"
    # The synthetic font's name table says Regular; the filename says Bold and
    # wins, which is the case the per-family copies all carried.
    assert name.getName(2, 3, 1, 0x409).toUnicode() == "Bold"
    assert name.getName(4, 3, 1, 0x409).toUnicode() == "Test NFM Bold"
    assert name.getName(6, 3, 1, 0x409).toUnicode() == "TestNFMBold"
    assert name.getName(16, 3, 1, 0x409).toUnicode() == "Test NFM"
    font.close()


def test_rename_reads_the_typographic_subfamily_not_the_legacy_one(make_font, tmp_path):
    """A Light survives the Nerd pass (KIT-282).

    Since the merge does the RIBBI split, a Light product carries
    `ID2 = "Regular"` and `ID17 = "Light"`. This step used to read ID 2 first,
    which would have restamped the Light as a second Regular — same family, same
    subfamily, same PostScript name as the real Regular, and only the file name
    left to tell them apart.
    """
    path = make_font(
        name="AKRSansSCNFM-Light.ttf",
        glyphs={"A": (HALF, (20, 0, 480, 700))},
        cmap={CP_A: "A"},
    )
    font = TTFont(path)
    for nid, value in ((1, "X Light"), (2, "Regular"), (16, "X"), (17, "Light")):
        font["name"].setName(value, nid, 3, 1, 0x409)
    font.save(path)
    font.close()

    assert rnf.main(["--family", "AKR Sans SC NFM", "--family-ps", "AKRSansSCNFM", str(path)]) == 0

    font = TTFont(path)
    name = font["name"]
    assert name.getName(17, 3, 1, 0x409).toUnicode() == "Light"
    assert name.getName(1, 3, 1, 0x409).toUnicode() == "AKR Sans SC NFM Light"
    assert name.getName(2, 3, 1, 0x409).toUnicode() == "Regular"
    assert name.getName(16, 3, 1, 0x409).toUnicode() == "AKR Sans SC NFM"
    assert name.getName(6, 3, 1, 0x409).toUnicode() == "AKRSansSCNFMLight"
    font.close()


def test_rename_requires_the_family_names(make_font, capsys):
    path = make_font(glyphs={"A": (HALF, (20, 0, 480, 700))}, cmap={CP_A: "A"})
    try:
        rnf.main([str(path)])
    except SystemExit as exc:
        assert exc.code == 2
        return
    raise AssertionError("expected argparse to reject the missing --family")


def test_pua_icons_are_scaled_into_the_half_cell(make_font):
    path = make_font(
        glyphs={
            "A": (HALF, (20, 0, 480, 700)),
            "zhong": (FULL, (20, 0, 980, 700)),
            "sep": (FULL, (0, 0, 1000, 700)),
        },
        cmap={CP_A: "A", CP_ZHONG: "zhong", CP_PUA: "sep"},
    )
    fnw.fix_font(path)

    font = TTFont(path, lazy=False)
    assert font["hmtx"]["sep"][0] == HALF
    glyph = font["glyf"]["sep"]
    assert glyph.xMax <= HALF, "the outline must be scaled, not just the advance"
    # Non-PUA glyphs are untouched.
    assert font["hmtx"]["zhong"][0] == FULL
    font.close()
