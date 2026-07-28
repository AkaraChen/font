#!/usr/bin/env python3
"""Scale a monospaced TrueType face onto a 2:1 half-cell (default 500 @ UPM 1000).

Recursive Mono Casual ships as TrueType glyf with a 600-unit mono cell. This
script scales outlines + advances in place (no CFF→glyf redraw), so composite
glyphs survive. Uniform scale (x and y) keeps proportions; the cell lands on
exactly --en-adv.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates


def scale_glyph(glyph, glyf, sx: float, sy: float) -> None:
    if glyph.numberOfContours == 0:
        return
    if glyph.isComposite():
        for c in glyph.components:
            c.x = int(round(c.x * sx))
            c.y = int(round(c.y * sy))
        return
    glyph.coordinates = GlyphCoordinates(
        [(int(round(x * sx)), int(round(y * sy))) for x, y in glyph.coordinates]
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--src-adv", type=int, default=600)
    ap.add_argument("--en-adv", type=int, default=500)
    ap.add_argument(
        "--uniform",
        action="store_true",
        default=True,
        help="scale x and y by en/src (default)",
    )
    ap.add_argument(
        "--x-only",
        action="store_true",
        help="scale only x (horizontal squeeze)",
    )
    args = ap.parse_args()

    if args.x_only:
        sx = args.en_adv / args.src_adv
        sy = 1.0
    else:
        sx = sy = args.en_adv / args.src_adv

    font = TTFont(args.src, recalcBBoxes=True, recalcTimestamp=False)
    glyf = font["glyf"]
    hmtx = font["hmtx"].metrics
    print(f"scale {args.src.name}: x×{sx:.6f} y×{sy:.6f}  cell {args.src_adv}→{args.en_adv}")

    for name in font.getGlyphOrder():
        g = glyf[name]
        scale_glyph(g, glyf, sx, sy)
        if g.numberOfContours != 0:
            g.recalcBounds(glyf)
            lsb = g.xMin
        else:
            lsb = int(round(hmtx[name][1] * sx))
        w, _ = hmtx[name]
        if w == 0:
            new_w = 0
        elif w == args.src_adv:
            new_w = args.en_adv
        else:
            new_w = max(0, int(round(w * sx)))
        hmtx[name] = (new_w, lsb)

    hhea, os2, post = font["hhea"], font["OS/2"], font["post"]
    for attr in ("ascent", "descent", "lineGap"):
        if hasattr(hhea, attr) and getattr(hhea, attr):
            setattr(hhea, attr, int(round(getattr(hhea, attr) * sy)))
    hhea.advanceWidthMax = max(w for w, _ in hmtx.values())
    hhea.minLeftSideBearing = 0
    hhea.minRightSideBearing = 0
    hhea.xMaxExtent = 0

    for attr in (
        "sTypoAscender",
        "sTypoDescender",
        "sTypoLineGap",
        "usWinAscent",
        "usWinDescent",
        "sxHeight",
        "sCapHeight",
        "yStrikeoutSize",
        "yStrikeoutPosition",
    ):
        v = getattr(os2, attr, None)
        if v:
            setattr(os2, attr, int(round(v * sy)))
    os2.xAvgCharWidth = args.en_adv

    for attr in ("underlinePosition", "underlineThickness"):
        v = getattr(post, attr, None)
        if v:
            setattr(post, attr, int(round(v * sy)))

    for tag in ("prep", "fpgm", "cvt ", "hdmx", "LTSH", "VDMX"):
        if tag in font:
            del font[tag]

    font["maxp"].recalc(font)
    args.dst.parent.mkdir(parents=True, exist_ok=True)
    font.save(args.dst)
    font.close()

    check = TTFont(args.dst)
    cm = check.getBestCmap()
    h = check["hmtx"]
    print("  advances:", {ch: h[cm[ord(ch)]][0] for ch in "Aa0i" if ord(ch) in cm})
    print(f"  saved {args.dst}")
    check.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
