#!/usr/bin/env python3
"""Apply a mild pseudo-oblique shear to CJK (and other) glyphs.

Matches Monaspace Radon Italic lean (post.italicAngle ≈ −11°) but typically
uses a gentler angle (default 8°) so upright Radon + WenKai still feel related
without full italicization.

Formula (α = post-style italic angle in degrees, negative = right-leaning):
    x' = x - y * tan(α · π/180)

Advances are preserved; LSB is recomputed from the sheared outline xMin.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates


def shear_glyph(glyph, glyf_table, skew: float) -> None:
    """skew = tan(radians); x' = x + y * skew  (skew > 0 → right lean)."""
    if glyph.numberOfContours == 0:
        return
    if glyph.isComposite():
        for component in glyph.components:
            # shift component origin; approximate shear on translation only
            component.x = int(round(component.x + component.y * skew))
            if hasattr(component, "transform"):
                xx, xy, yx, yy = component.transform
                # apply horizontal shear: [1 skew; 0 1] * existing
                # new_xx = xx + skew*yx, new_xy = xy + skew*yy
                component.transform = (xx + skew * yx, xy + skew * yy, yx, yy)
        glyph.recalcBounds(glyf_table)
        return

    coords = glyph.coordinates
    if not coords:
        return
    glyph.coordinates = GlyphCoordinates(
        [(int(round(x + y * skew)), y) for x, y in coords]
    )
    glyph.recalcBounds(glyf_table)


def is_cjk_side(cp: int) -> bool:
    ranges = (
        (0x2E80, 0x2EFF),
        (0x2F00, 0x2FDF),
        (0x3000, 0x303F),
        (0x3040, 0x30FF),
        (0x3100, 0x312F),
        (0x3190, 0x319F),
        (0x31A0, 0x31BF),
        (0x31C0, 0x31EF),
        (0x31F0, 0x31FF),
        (0x3200, 0x32FF),
        (0x3300, 0x33FF),
        (0x3400, 0x4DBF),
        (0x4E00, 0x9FFF),
        (0xF900, 0xFAFF),
        (0xFE30, 0xFE4F),
        (0xFF00, 0xFFEF),
        (0x20000, 0x2A6DF),
        (0x2A700, 0x2B73F),
        (0x2B740, 0x2B81F),
        (0x2B820, 0x2CEAF),
        (0x2F800, 0x2FA1F),
    )
    return any(a <= cp <= b for a, b in ranges)


def oblique_font(
    src: Path,
    dst: Path,
    angle_deg: float,
    *,
    only_cjk: bool = True,
    min_width: int = 0,
) -> dict:
    """angle_deg: post.italicAngle convention (negative = right lean)."""
    font = TTFont(str(src), recalcBBoxes=True, recalcTimestamp=False)
    glyf = font["glyf"]
    hmtx = font["hmtx"].metrics
    cmap = font.getBestCmap() or {}

    # right-leaning when angle_deg < 0 → positive skew on x += y*skew
    skew = -math.tan(math.radians(angle_deg))

    targets: set[str] = set()
    if only_cjk:
        for cp, name in cmap.items():
            if is_cjk_side(cp):
                targets.add(name)
        # close components
        stack = list(targets)
        while stack:
            n = stack.pop()
            g = glyf[n]
            if g.isComposite():
                for c in g.components:
                    if c.glyphName not in targets:
                        targets.add(c.glyphName)
                        stack.append(c.glyphName)
    else:
        targets = set(font.getGlyphOrder())

    n_done = 0
    for name in targets:
        w, _lsb = hmtx[name]
        if min_width and w < min_width:
            continue
        g = glyf[name]
        if g.numberOfContours == 0:
            continue
        shear_glyph(g, glyf, skew)
        # re-center horizontally inside original advance
        if hasattr(g, "xMin") and hasattr(g, "xMax") and g.numberOfContours != 0:
            ink = g.xMax - g.xMin
            new_lsb = (w - ink) // 2
            shift = new_lsb - g.xMin
            if shift and not g.isComposite():
                coords = g.coordinates
                g.coordinates = GlyphCoordinates(
                    [(x + shift, y) for x, y in coords]
                )
                g.recalcBounds(glyf)
                hmtx[name] = (w, new_lsb)
            elif shift and g.isComposite():
                for c in g.components:
                    c.x = int(round(c.x + shift))
                g.recalcBounds(glyf)
                hmtx[name] = (w, new_lsb)
        n_done += 1
        if n_done % 5000 == 0:
            print(f"  … oblique {n_done} glyphs", flush=True)

    # advertise mild italic angle for hosts that read post
    font["post"].italicAngle = float(angle_deg)

    dst.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(dst))
    font.close()
    return {"glyphs": n_done, "angle_deg": angle_deg, "skew": skew}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument(
        "--angle",
        type=float,
        default=-8.0,
        help="post.italicAngle degrees (default -8, right-leaning)",
    )
    ap.add_argument(
        "--all-glyphs",
        action="store_true",
        help="shear every glyph, not only CJK-side codepoints",
    )
    ap.add_argument("--min-width", type=int, default=0)
    args = ap.parse_args()
    if not args.src.exists():
        print(f"missing {args.src}", file=sys.stderr)
        return 1
    info = oblique_font(
        args.src,
        args.dst,
        args.angle,
        only_cjk=not args.all_glyphs,
        min_width=args.min_width,
    )
    print(f"oblique → {args.dst}  {info}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
