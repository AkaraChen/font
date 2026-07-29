"""The two format conversions make two different promises. Both are testable.

WOFF2 claims to be a container change and nothing else, so the test is byte
equality of the outlines. OTF claims only to be the same design in CFF, so the
test is that everything a conversion must *not* touch survives — inventory,
advances, cmap, family name — and that the outlines land inside the qu2cu
tolerance rather than wherever they like.

Curves matter here in a way they do not elsewhere in this suite: conftest's
fixture fonts are axis-aligned squares, and a straight line converts to a
straight line whatever the fitter does. Every glyph below has a quadratic in it.
"""

from __future__ import annotations

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from fontkit import convert, verify_formats

UPM = 1000


def _curved():
    """A closed contour with two quadratic segments and one off-curve run."""
    pen = TTGlyphPen(None)
    pen.moveTo((50, 0))
    pen.qCurveTo((250, 900), (450, 0))
    pen.qCurveTo((400, -120), (200, -120), (50, 0))
    pen.closePath()
    return pen.glyph()


def _boxed():
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((500, 0))
    pen.lineTo((500, 700))
    pen.lineTo((0, 700))
    pen.closePath()
    return pen.glyph()


@pytest.fixture
def product(tmp_path):
    """A minimal but honest product: curves, a composite, a real name table."""
    order = [".notdef", "A", "B", "Aacute"]
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({0x41: "A", 0x42: "B", 0xC1: "Aacute"})

    curved = _curved()
    composite = TTGlyphPen({"A": curved})
    composite.addComponent("A", (1, 0, 0, 1, 10, 20))
    fb.setupGlyf(
        {
            ".notdef": TTGlyphPen(None).glyph(),
            "A": curved,
            "B": _boxed(),
            "Aacute": composite.glyph(),
        }
    )
    fb.setupHorizontalMetrics({name: (500, 0) for name in order})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable(
        {
            "familyName": "AKR Test SC NFM",
            "styleName": "Regular",
            "psName": "AKRTestSCNFM-Regular",
            "version": "1.000",
        }
    )
    fb.setupOS2()
    fb.setupPost()
    path = tmp_path / "AKRTestSCNFM-Regular.ttf"
    fb.save(str(path))
    return path


def _glyf_bytes(path):
    font = TTFont(path, recalcBBoxes=False, recalcTimestamp=False)
    try:
        return verify_formats._glyf_bytes(font)
    finally:
        font.close()


def test_woff2_is_the_same_outlines(product, tmp_path):
    """A re-wrap that changed one coordinate would be a second product."""
    convert.main(["--format", "woff2", "--out-dir", str(tmp_path), str(product)])
    woff2 = tmp_path / "AKRTestSCNFM-Regular.woff2"
    assert woff2.is_file()
    assert _glyf_bytes(woff2) == _glyf_bytes(product)


def test_otf_is_cff_and_carries_no_truetype_leftovers(product, tmp_path):
    convert.main(["--format", "otf", "--out-dir", str(tmp_path), str(product)])
    otf = TTFont(tmp_path / "AKRTestSCNFM-Regular.otf")
    try:
        assert otf.sfntVersion == "OTTO"
        assert "CFF " in otf
        # A `glyf` in an OTF would mean the file is a TTF with a nicer suffix,
        # and `prep`/`fpgm` would advertise hinting the CFF cannot run.
        for tag in ("glyf", "loca", "prep", "fpgm", "cvt "):
            assert tag not in otf
        # maxp 1.0 carries TrueType-only maxima; post 2.0 a second copy of the
        # glyph order that the CFF charset already holds.
        assert otf["maxp"].tableVersion == 0x00005000
        assert otf["post"].formatType == 3.0
    finally:
        otf.close()


def test_otf_keeps_everything_a_format_change_must_not_move(product, tmp_path):
    convert.main(["--format", "otf", "--out-dir", str(tmp_path), str(product)])
    source = TTFont(product)
    target = TTFont(tmp_path / "AKRTestSCNFM-Regular.otf")
    try:
        assert source.getGlyphOrder() == target.getGlyphOrder()
        assert verify_formats._advances(source) == verify_formats._advances(target)
        assert verify_formats._cmap(source) == verify_formats._cmap(target)
        assert source["name"].getDebugName(1) == target["name"].getDebugName(1)
    finally:
        source.close()
        target.close()


def test_otf_outlines_stay_inside_the_qu2cu_tolerance(product, tmp_path):
    """The conversion is lossy, and the tolerance is the whole contract."""
    convert.main(
        ["--format", "otf", "--max-err", "1.0", "--out-dir", str(tmp_path), str(product)]
    )
    source = TTFont(product)
    target = TTFont(tmp_path / "AKRTestSCNFM-Regular.otf")
    try:
        src_set, dst_set = source.getGlyphSet(), target.getGlyphSet()
        for name in source.getGlyphOrder():
            before, after = BoundsPen(src_set), BoundsPen(dst_set)
            src_set[name].draw(before)
            dst_set[name].draw(after)
            if before.bounds is None:
                assert after.bounds is None
                continue
            drift = max(abs(a - b) for a, b in zip(before.bounds, after.bounds))
            assert drift <= 1.0 + verify_formats.BBOX_SLACK, name
    finally:
        source.close()
        target.close()


def test_the_composite_really_was_converted(product, tmp_path):
    """Composites are decomposed before the fit, not passed through.

    A component that reached the charstring pen untouched would be converted by
    the base pen's exact quad→cubic fallback instead, which is a second
    conversion path with a different curve count. The check is that `Aacute` is
    a real charstring rather than an `seac`-style reference — its program has to
    contain drawing operators of its own.

    Subroutinization is off here on purpose: it is the whole point of that step
    to replace those operators with `callsubr`, which would hide what this test
    is looking at.
    """
    convert.main(
        ["--format", "otf", "--no-subroutinize", "--out-dir", str(tmp_path), str(product)]
    )
    font = TTFont(tmp_path / "AKRTestSCNFM-Regular.otf")
    try:
        cff = font["CFF "].cff
        charstrings = cff[cff.fontNames[0]].CharStrings
        charstrings["Aacute"].decompile()
        program = charstrings["Aacute"].program
        assert any(op in program for op in ("rrcurveto", "hhcurveto", "hvcurveto", "vvcurveto"))
    finally:
        font.close()


def test_subroutinization_is_part_of_the_product(product, tmp_path):
    """…so it cannot be a best-effort import.

    An un-subroutinized CFF is a different file with a different fingerprint. If
    `cffsubr` were optional, the OTF a laptop builds and the OTF CI builds would
    differ and the baseline would be a property of who ran the build.
    """
    plain = tmp_path / "plain"
    subr = tmp_path / "subr"
    convert.main(["--format", "otf", "--no-subroutinize", "--out-dir", str(plain), str(product)])
    convert.main(["--format", "otf", "--out-dir", str(subr), str(product)])
    name = "AKRTestSCNFM-Regular.otf"
    assert (plain / name).read_bytes() != (subr / name).read_bytes()


def test_verify_formats_accepts_a_real_conversion(product, tmp_path, capsys):
    convert.main(["--format", "woff2", "--out-dir", str(tmp_path), str(product)])
    convert.main(["--format", "otf", "--out-dir", str(tmp_path), str(product)])
    assert verify_formats.main([str(tmp_path)]) == 0


def test_verify_formats_rejects_a_woff2_that_is_not_a_rewrap(product, tmp_path):
    """The gate has to be able to fail, or it is decoration.

    Build the WOFF2 from a *different* font — one glyph moved — and hand it to
    the checker under the source's name, which is exactly what a "conversion"
    that quietly rebuilt the outlines would produce.
    """
    tampered = TTFont(product, recalcBBoxes=False, recalcTimestamp=False)
    glyf = tampered["glyf"]
    glyph = glyf["B"]
    glyph.expand(glyf)
    glyph.coordinates[0] = (glyph.coordinates[0][0] + 30, glyph.coordinates[0][1])
    tampered.flavor = "woff2"
    tampered.save(tmp_path / product.with_suffix(".woff2").name)
    tampered.close()
    (tmp_path / product.name).write_bytes(product.read_bytes())

    assert verify_formats.main([str(tmp_path)]) == 1


def test_verify_formats_rejects_a_product_with_no_source(tmp_path, product):
    """A shipped WOFF2 whose TTF is not shipped cannot be checked against
    anything, so it is a failure rather than a skip."""
    orphan = tmp_path / "orphan"
    convert.main(["--format", "woff2", "--out-dir", str(orphan), str(product)])
    assert verify_formats.main([str(orphan)]) == 1
