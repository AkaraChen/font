#!/usr/bin/env python3
"""Prepare LXGW WenKai as the full-cell CJK side: weight match, then slant.

Order matters. Embolden runs first, on the upright outlines, so the strength
calibrated by `calibrate_cjk_weight.py` (which measures upright stems) is the
strength actually applied. The shear comes second and is pure geometry — it does
not change perpendicular stroke thickness, only the axis it rides on.

Slant: Radon is nominally upright (`post.italicAngle = 0`) yet its straight
stems lean ~7.5° right — it is a handwriting design. Shearing WenKai by the
measured Radon angle (see `measure-slant.py`) makes the Kai brush strokes lean
with the Latin instead of standing square beside it. The shear pivots at
`--pivot-y` (≈ half the Han ink height) so glyphs stay centred in their cell
instead of drifting right at the top.

Advances are left alone (WenKai's native 1000 = the full cell of a 500/1000
grid); only side bearings are recomputed.
"""

from __future__ import annotations

import argparse
import math
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

from fontkit.embolden import embolden_font

DROP_TABLES = ("prep", "fpgm", "cvt ", "gasp", "hdmx", "LTSH", "VDMX")


def shear_font(font: TTFont, degrees: float, pivot_y: float) -> int:
    """x' = x + tan(a)·(y − pivot); returns number of glyphs touched."""
    tan = math.tan(math.radians(degrees))
    glyf = font["glyf"]
    hmtx = font["hmtx"].metrics
    touched = 0

    for name in font.getGlyphOrder():
        glyph = glyf[name]
        if glyph.numberOfContours == 0:
            continue
        if glyph.isComposite():
            # Components reference already-sheared bases, so only the offset
            # needs the shear applied (no 2×2 transforms in WenKai; bail if that
            # ever changes rather than emitting a silently wrong outline).
            for component in glyph.components:
                transform = getattr(component, "transform", None)
                if transform is not None and tuple(
                    round(v, 6) for row in transform for v in row
                ) != (1.0, 0.0, 0.0, 1.0):
                    raise SystemExit(
                        f"error: composite {name} has a 2×2 transform; "
                        "shear needs a decomposing path for this glyph"
                    )
                component.x = int(round(component.x + tan * component.y))
        else:
            glyph.coordinates = GlyphCoordinates(
                [(int(round(x + tan * (y - pivot_y))), y) for x, y in glyph.coordinates]
            )
        glyph.recalcBounds(glyf)
        width, _lsb = hmtx[name]
        hmtx[name] = (width, glyph.xMin)
        touched += 1

    # italicAngle is negative for a right-leaning face
    font["post"].italicAngle = -abs(degrees)
    hhea = font["hhea"]
    hhea.caretSlopeRise = 1000
    hhea.caretSlopeRun = int(round(tan * 1000))
    return touched


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--embolden", type=float, default=0.0, help="pathops stroke strength (0 = off)")
    ap.add_argument("--slant-deg", type=float, default=7.5)
    ap.add_argument("--pivot-y", type=float, default=375.0)
    ap.add_argument("--min-embolden-width", type=int, default=900)
    args = ap.parse_args(argv)

    args.dst.parent.mkdir(parents=True, exist_ok=True)
    source = args.src

    with tempfile.TemporaryDirectory() as tmp:
        if args.embolden > 0:
            emboldened = Path(tmp) / "emboldened.ttf"
            print(f"Embolden {args.src.name} strength={args.embolden:g} (full-cell glyphs only)")
            stats = embolden_font(
                args.src,
                emboldened,
                args.embolden,
                only_wide=True,
                min_width=args.min_embolden_width,
            )
            print(f"  {stats}")
            source = emboldened
        else:
            print(f"Embolden skipped (strength 0) — {args.src.name} used as designed")

        print(f"Shear {args.slant_deg:g}° about y={args.pivot_y:g}")
        font = TTFont(source, recalcBBoxes=True, recalcTimestamp=False)
        touched = shear_font(font, args.slant_deg, args.pivot_y)
        for tag in DROP_TABLES:
            if tag in font:
                del font[tag]
        font["maxp"].recalc(font)
        font.save(args.dst)
        font.close()

    check = TTFont(args.dst)
    cmap = check.getBestCmap()
    hmtx = check["hmtx"]
    for ch in "中永国":
        name = cmap.get(ord(ch))
        if name:
            glyph = check["glyf"][name]
            print(
                f"  {ch}: adv={hmtx[name][0]} "
                f"bbox=({glyph.xMin},{glyph.yMin},{glyph.xMax},{glyph.yMax})"
            )
    check.close()
    print(f"  saved {args.dst} ({touched} glyphs sheared)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
