#!/usr/bin/env python3
"""Prepare Monaspace Radon NF as the Latin half-cell of a 2:1 dual-width face.

Three things happen here, in one pass over the outlines:

1. **CFF → glyf.** The CJK side (WenKai) is TrueType; a font cannot hold both
   outline formats, and quadratics are the format that can absorb 45 k imported
   Han glyphs. Curves are converted with cu2qu at `--max-err` (font units of the
   *output* UPM).
2. **Narrow + scale.** Monaspace's cell is 1240/2000 em (0.62 em) — pair that
   2:1 with a 1 em Han glyph and either the CJK looks lost in its cell or the
   Latin needs a brutal squeeze. Same recipe as LXGW Bright Code: x-narrow
   1240 → 1111, then scale the whole face to 90 %, which lands the cell exactly
   on 0.5 em. Net: x × 0.4032, y × 0.45 into a 1000 UPM box.
3. **Keep the OpenType logic.** GSUB/GDEF (Radon `liga`, `calt` texture healing,
   `ss01`–`ss10`, `cv**`) are untouched, so ligatures survive the merge. GDEF
   caret x-coordinates and any GPOS x-values are scaled with the outlines.

Nerd icons need no special casing: the pre-patched `MonaspaceRadonNF-*` ships
every glyph — icons included — at the single 1240 cell, so they land on the
half cell like the ASCII does. That is what makes the product "NFM".
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.misc.transform import Transform


DROP_TABLES = ("CFF ", "CFF2", "VORG", "hdmx", "LTSH", "VDMX", "kern")


def convert_outlines(font: TTFont, transform: Transform, max_err: float) -> None:
    """Draw every glyph through transform → cu2qu → TTGlyphPen; install glyf."""
    glyph_set = font.getGlyphSet()
    order = font.getGlyphOrder()
    glyf = newTable("glyf")
    glyf.glyphOrder = list(order)
    glyphs = {}

    for i, name in enumerate(order):
        pen = TTGlyphPen(None)
        # Transform outermost: cu2qu then sees already-scaled cubics, so its
        # error tolerance is measured in output units.
        source = TransformPen(Cu2QuPen(pen, max_err), transform)
        glyph_set[name].draw(source)
        glyphs[name] = pen.glyph()
        if i and i % 4000 == 0:
            print(f"    … {i}/{len(order)} glyphs converted")

    glyf.glyphs = glyphs
    # OTF ships post 3.0 (names live in the CFF charset we are about to drop).
    # Keep the names in post 2.0 instead: `equal_equal`, `wk.u4E2D` and friends
    # are what the feature gate and any later debugging read.
    post = font["post"]
    post.formatType = 2.0
    post.extraNames = []
    post.mapping = {}
    post.glyphOrder = None
    for tag in DROP_TABLES:
        if tag in font:
            del font[tag]
    font["glyf"] = glyf
    font["loca"] = newTable("loca")
    font.sfntVersion = "\x00\x01\x00\x00"
    font["maxp"].tableVersion = 0x00010000
    for attr, value in (
        ("maxZones", 1),
        ("maxTwilightPoints", 0),
        ("maxStorage", 0),
        ("maxFunctionDefs", 0),
        ("maxInstructionDefs", 0),
        ("maxStackElements", 0),
        ("maxSizeOfInstructions", 0),
        ("maxComponentElements", 0),
        ("maxComponentDepth", 0),
    ):
        setattr(font["maxp"], attr, value)
    for name in order:
        glyph = glyf[name]
        if glyph.numberOfContours != 0:
            glyph.recalcBounds(glyf)
    font["maxp"].recalc(font)


def scale_metrics(font: TTFont, x_scale: float, y_scale: float, en_adv: int, src_adv: int) -> None:
    hmtx = font["hmtx"].metrics
    glyf = font["glyf"]
    for name in font.getGlyphOrder():
        width, _lsb = hmtx[name]
        glyph = glyf[name]
        lsb = glyph.xMin if glyph.numberOfContours != 0 else 0
        if width == 0:
            new_width = 0  # combining marks: keep zero advance for mark attach
        elif width == src_adv:
            new_width = en_adv  # the mono cell, snapped (no rounding drift)
        else:
            new_width = max(0, round(width * x_scale))
        hmtx[name] = (new_width, lsb)

    hhea = font["hhea"]
    hhea.advanceWidthMax = max(w for w, _ in hmtx.values())
    for attr in ("caretSlopeRun", "minLeftSideBearing", "minRightSideBearing", "xMaxExtent"):
        if hasattr(hhea, attr):
            setattr(hhea, attr, 0)

    os2 = font["OS/2"]
    for attr, scale in (
        ("sxHeight", y_scale),
        ("sCapHeight", y_scale),
        ("ySubscriptXSize", x_scale),
        ("ySubscriptYSize", y_scale),
        ("ySubscriptXOffset", x_scale),
        ("ySubscriptYOffset", y_scale),
        ("ySuperscriptXSize", x_scale),
        ("ySuperscriptYSize", y_scale),
        ("ySuperscriptXOffset", x_scale),
        ("ySuperscriptYOffset", y_scale),
        ("yStrikeoutSize", y_scale),
        ("yStrikeoutPosition", y_scale),
    ):
        value = getattr(os2, attr, None)
        if value:
            setattr(os2, attr, round(value * scale))
    os2.xAvgCharWidth = en_adv

    post = font["post"]
    for attr in ("underlinePosition", "underlineThickness"):
        value = getattr(post, attr, None)
        if value:
            setattr(post, attr, round(value * y_scale))


def scale_gdef_gpos_x(font: TTFont, x_scale: float) -> None:
    """Scale x-coordinates that live in layout tables (carets, GPOS values)."""
    if "GDEF" in font:
        lig_carets = getattr(font["GDEF"].table, "LigCaretList", None)
        if lig_carets and lig_carets.LigGlyph:
            for lig in lig_carets.LigGlyph:
                for caret in lig.CaretValue or []:
                    if getattr(caret, "Coordinate", None):
                        caret.Coordinate = round(caret.Coordinate * x_scale)
    if "GPOS" not in font:
        return
    gpos = font["GPOS"].table
    if not gpos.LookupList:
        return

    def scale_value(record) -> None:
        if record is None:
            return
        for attr in ("XAdvance", "XPlacement"):
            value = getattr(record, attr, None)
            if value:
                setattr(record, attr, round(value * x_scale))

    def scale_anchor(anchor) -> None:
        if anchor is not None and getattr(anchor, "XCoordinate", None):
            anchor.XCoordinate = round(anchor.XCoordinate * x_scale)

    for lookup in gpos.LookupList.Lookup:
        for sub in lookup.SubTable:
            for attr in ("Value", "Value1", "Value2"):
                scale_value(getattr(sub, attr, None))
            for pair_set in getattr(sub, "PairSet", None) or []:
                for record in pair_set.PairValueRecord or []:
                    scale_value(getattr(record, "Value1", None))
                    scale_value(getattr(record, "Value2", None))
            for row in getattr(sub, "Class1Record", None) or []:
                for record in row.Class2Record or []:
                    scale_value(getattr(record, "Value1", None))
                    scale_value(getattr(record, "Value2", None))
            mark_array = getattr(sub, "MarkArray", None)
            if mark_array is not None:
                for record in mark_array.MarkRecord or []:
                    scale_anchor(record.MarkAnchor)
            for array_attr, record_attr, anchor_attr in (
                ("BaseArray", "BaseRecord", "BaseAnchor"),
                ("Mark2Array", "Mark2Record", "Mark2Anchor"),
            ):
                array = getattr(sub, array_attr, None)
                if array is None:
                    continue
                for record in getattr(array, record_attr) or []:
                    for anchor in getattr(record, anchor_attr) or []:
                        scale_anchor(anchor)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--src-upm", type=int, default=2000)
    ap.add_argument("--upm", type=int, default=1000)
    ap.add_argument("--src-adv", type=int, default=1240)
    ap.add_argument("--narrow-adv", type=int, default=1111, help="x-only narrowing target, in src UPM")
    ap.add_argument("--uniform-scale", type=float, default=0.9)
    ap.add_argument("--en-adv", type=int, default=500)
    ap.add_argument("--max-err", type=float, default=0.5, help="cu2qu error, output units")
    args = ap.parse_args()

    upm_scale = args.upm / args.src_upm
    x_scale = (args.narrow_adv / args.src_adv) * args.uniform_scale * upm_scale
    y_scale = args.uniform_scale * upm_scale
    landed = args.src_adv * x_scale
    if abs(landed - args.en_adv) > 1.0:
        raise SystemExit(
            f"error: cell lands on {landed:.2f}, not --en-adv {args.en_adv}; "
            "check --narrow-adv / --uniform-scale"
        )

    print(f"Loading {args.src.name}")
    font = TTFont(args.src, recalcBBoxes=True, recalcTimestamp=False)
    print(f"  x × {x_scale:.6f}  y × {y_scale:.6f}  → cell {args.en_adv} @ UPM {args.upm}")
    print("  converting CFF → glyf (cu2qu) …")
    convert_outlines(font, Transform(x_scale, 0, 0, y_scale, 0, 0), args.max_err)
    font["head"].unitsPerEm = args.upm
    scale_metrics(font, x_scale, y_scale, args.en_adv, args.src_adv)
    scale_gdef_gpos_x(font, x_scale)

    # Vertical metrics are re-set from pins at merge time; scale them meanwhile
    # so the intermediate is viewable on its own.
    hhea, os2 = font["hhea"], font["OS/2"]
    hhea.ascent = round(hhea.ascent * y_scale)
    hhea.descent = round(hhea.descent * y_scale)
    hhea.lineGap = round(hhea.lineGap * y_scale)
    os2.sTypoAscender = round(os2.sTypoAscender * y_scale)
    os2.sTypoDescender = round(os2.sTypoDescender * y_scale)
    os2.sTypoLineGap = round(os2.sTypoLineGap * y_scale)
    os2.usWinAscent = round(os2.usWinAscent * y_scale)
    os2.usWinDescent = round(os2.usWinDescent * y_scale)

    args.dst.parent.mkdir(parents=True, exist_ok=True)
    font.save(args.dst)
    font.close()

    check = TTFont(args.dst)
    cmap = check.getBestCmap()
    hmtx = check["hmtx"]
    widths = {ch: hmtx[cmap[ord(ch)]][0] for ch in "Aa0i" if ord(ch) in cmap}
    icons = [cmap[cp] for cp in cmap if 0xE000 <= cp <= 0xF8FF]
    icon_widths = sorted({hmtx[g][0] for g in icons})
    print(f"  saved {args.dst}  upm={check['head'].unitsPerEm} advances={widths}")
    print(f"  nerd/PUA icons: {len(icons)} glyphs, advances={icon_widths}")
    check.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
