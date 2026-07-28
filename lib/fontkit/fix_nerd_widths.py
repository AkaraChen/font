#!/usr/bin/env python3
"""Force Nerd / PUA icon advances to half-cell after the patcher.

The official patcher with `--single-width-glyphs` usually sets icons to 1 cell,
but on dual-width bases (EN 600 / CJK 1200) some Powerline glyphs still land at
full (1200). Terminals size Nerd icons as 1 cell; a 2-cell advance leaves a gap
or misaligns prompts.

For every cmap'd codepoint in common Nerd PUA ranges whose advance is not the
half-cell, x-scale the outline into the half-cell and centre it.

Run as: python3 -m fontkit.fix_nerd_widths FONT.ttf [...]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

# BMP PUA + Supplementary Private Use Area-A (Material Design Icons, etc.)
PUA_RANGES = (
    (0xE000, 0xF8FF),
    (0xF0000, 0xFFFFD),
    (0x100000, 0x10FFFD),
)


def in_pua(cp: int) -> bool:
    return any(a <= cp <= b for a, b in PUA_RANGES)


def half_unit(font: TTFont) -> int:
    cmap = font.getBestCmap() or {}
    name = cmap.get(ord("A"))
    if not name:
        raise SystemExit("missing 'A'")
    return font["hmtx"][name][0]


def scale_glyph_x(glyph, glyf, scale: float, x_off: float = 0.0) -> None:
    if glyph.numberOfContours == 0:
        return
    if glyph.isComposite():
        for component in glyph.components:
            component.x = int(round(component.x * scale + x_off))
            if hasattr(component, "transform"):
                xx, xy, yx, yy = component.transform
                component.transform = (xx * scale, xy, yx * scale, yy)
        glyph.recalcBounds(glyf)
        return
    coords = glyph.coordinates
    if not coords:
        return
    glyph.coordinates = GlyphCoordinates(
        [(int(round(x * scale + x_off)), y) for x, y in coords]
    )
    glyph.recalcBounds(glyf)


def fix_font(path: Path, *, dry_run: bool = False) -> list[str]:
    lines: list[str] = []
    font = TTFont(path)
    try:
        half = half_unit(font)
        full = half * 2
        cmap = font.getBestCmap() or {}
        hmtx = font["hmtx"]
        glyf = font["glyf"]

        # unique glyph names that need fixing (one glyph may map to many cps)
        to_fix: dict[str, int] = {}  # gname -> current advance
        for cp, gname in cmap.items():
            if not in_pua(cp):
                continue
            adv = hmtx[gname][0]
            if adv != half:
                to_fix[gname] = adv

        fixed = 0
        for gname, adv in to_fix.items():
            if adv <= 0:
                continue
            scale = half / adv
            # centre after scale: old centre at adv/2 → new at half/2
            # x' = x * scale + (half - adv * scale) / 2 = x * scale + 0
            # since adv*scale = half. Good for pure scale-to-half.
            # If adv was full and we scale 0.5: left-aligned ink stays left half —
            # better centre: x' = x*scale + (half - (xMax-xMin)*scale)/2 using bounds
            glyph = glyf[gname]
            if glyph.numberOfContours == 0:
                hmtx.metrics[gname] = (half, hmtx.metrics[gname][1])
                fixed += 1
                continue
            # scale first
            scale_glyph_x(glyph, glyf, scale, 0.0)
            # then centre within [0, half]
            try:
                glyph.recalcBounds(glyf)
                x_min, x_max = glyph.xMin, glyph.xMax
                width = x_max - x_min
                target_lsb = (half - width) / 2.0
                dx = target_lsb - x_min
                if abs(dx) >= 0.5:
                    scale_glyph_x(glyph, glyf, 1.0, dx)
            except Exception:
                pass
            try:
                glyph.recalcBounds(glyf)
                hmtx.metrics[gname] = (half, int(glyph.xMin))
            except Exception:
                hmtx.metrics[gname] = (half, 0)
            fixed += 1

        lines.append(
            f"{path.name}: nerd/PUA width fix — {fixed} glyphs → advance {half} "
            f"(scanned {len(to_fix)} non-half PUA glyphs)"
        )
        if not dry_run:
            font.save(path)
    finally:
        font.close()
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    for path in args.fonts:
        for line in fix_font(path, dry_run=args.dry_run):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
