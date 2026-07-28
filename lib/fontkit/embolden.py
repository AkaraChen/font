#!/usr/bin/env python3
"""Embolden a TrueType CJK source for optical weight matching (KIT-234).

Stroke-expands full-width glyph outlines via skia-pathops, keeps advance widths,
recenters horizontally. Converts conics→quads so pathops can stroke TT outlines.

Run as: python3 -m fontkit.embolden SRC.ttf DST.ttf --strength N
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
import pathops
from pathops import OpBuilder, PathOp


def glyph_to_path(glyph_set, name: str) -> pathops.Path:
    path = pathops.Path()
    rec = DecomposingRecordingPen(glyph_set)
    glyph_set[name].draw(rec)
    rec.replay(path.getPen())
    path.convertConicsToQuads()
    return path


def embolden_path(path: pathops.Path, strength: float) -> pathops.Path:
    if strength <= 0 or not list(path.contours):
        return path
    stroked = pathops.Path(path)
    # width = 2*strength expands roughly `strength` outward on each side
    stroked.stroke(
        strength * 2.0,
        pathops.LineCap.ROUND_CAP,
        pathops.LineJoin.ROUND_JOIN,
        4.0,
    )
    stroked.convertConicsToQuads()
    builder = OpBuilder(fix_winding=True)
    builder.add(path, PathOp.UNION)
    builder.add(stroked, PathOp.UNION)
    result = builder.resolve()
    result.convertConicsToQuads()
    return result


def path_to_glyph(path: pathops.Path):
    pen = TTGlyphPen(None)
    path.draw(pen)
    return pen.glyph()


def shift_glyph_x(glyph, dx: float) -> None:
    if dx == 0 or glyph.numberOfContours == 0:
        return
    if glyph.isComposite():
        for c in glyph.components:
            c.x = int(round(c.x + dx))
        return
    coords = glyph.coordinates
    for i in range(len(coords)):
        x, y = coords[i]
        coords[i] = (x + dx, y)
    glyph.coordinates = coords


def embolden_font(
    src: Path,
    dst: Path,
    strength: float,
    *,
    only_wide: bool = True,
    min_width: int = 900,
) -> dict:
    font = TTFont(str(src))
    glyf = font["glyf"]
    hmtx = font["hmtx"].metrics
    glyph_set = font.getGlyphSet()
    order = font.getGlyphOrder()

    stats = {"total": 0, "emboldened": 0, "skipped": 0, "errors": 0}
    # Snapshot original midpoints before mutating glyf (glyph_set reads live glyf)
    original: dict[str, tuple[int, float]] = {}
    for name in order:
        g = glyf[name]
        width = hmtx[name][0]
        if g.numberOfContours == 0:
            continue
        if only_wide and width < min_width:
            continue
        try:
            g.recalcBounds(glyf)
            mid = (g.xMin + g.xMax) / 2.0
        except Exception:
            mid = width / 2.0
        original[name] = (width, mid)

    for name, (width, old_mid) in original.items():
        stats["total"] += 1
        try:
            path = glyph_to_path(glyph_set, name)
            if not list(path.contours):
                stats["skipped"] += 1
                continue
            new_path = embolden_path(path, strength)
            new_glyph = path_to_glyph(new_path)
            if new_glyph.numberOfContours > 0 and not new_glyph.isComposite():
                new_glyph.recalcBounds(glyf)
                new_mid = (new_glyph.xMin + new_glyph.xMax) / 2.0
                shift_glyph_x(new_glyph, old_mid - new_mid)
                new_glyph.recalcBounds(glyf)
                hmtx[name] = (width, int(round(new_glyph.xMin)))
            glyf[name] = new_glyph
            stats["emboldened"] += 1
            if stats["emboldened"] % 2000 == 0:
                print(f"  … {stats['emboldened']} glyphs", file=sys.stderr, flush=True)
        except Exception as e:
            stats["errors"] += 1
            if stats["errors"] <= 8:
                print(f"  warn {name}: {e}", file=sys.stderr)

    if "OS/2" in font:
        if strength >= 40:
            font["OS/2"].usWeightClass = 700
        elif strength >= 22:
            font["OS/2"].usWeightClass = 500
        else:
            font["OS/2"].usWeightClass = 400

    dst.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(dst))
    font.close()
    return stats


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--strength", type=float, required=True)
    ap.add_argument("--all-glyphs", action="store_true")
    args = ap.parse_args(argv)
    stats = embolden_font(
        Path(args.src),
        Path(args.dst),
        args.strength,
        only_wide=not args.all_glyphs,
    )
    print(f"saved {args.dst} strength={args.strength} {stats}")


if __name__ == "__main__":
    main()
