#!/usr/bin/env python3
"""Measure the real slant of a face, and recommend CJK_SLANT_DEG.

`post.italicAngle` is a declaration, not a measurement: Monaspace Radon declares
0 while its stems visibly lean right — it is a handwriting design. Pairing an
upright Kai with it looks wrong for exactly that reason, so the shear applied to
WenKai is derived from the outlines instead.

Method: for each sample glyph, walk horizontal scanlines through the middle 50 %
of the ink, take the ink-weighted centre x of each line, and least-squares fit
x against y. The slope is the glyph's axis; report degrees. Straight-stem glyphs
(H I T k E) are the honest sample — round or asymmetric letters (o a d) read
several degrees high because their widest point is not at mid-height, so they
are measured but excluded from the recommendation.

Usage:
  measure-slant.py FONT.ttf [FONT2.otf …]
  measure-slant.py --chars l,I,H,k --stem-chars I,H work/src/*.otf
"""

from __future__ import annotations

import argparse
import math
import statistics
import sys
from pathlib import Path

from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fontTools.ttLib import TTFont

try:
    import pathops
except ImportError as exc:  # pragma: no cover
    print("error: skia-pathops is required (pip install skia-pathops)", file=sys.stderr)
    raise SystemExit(2) from exc

DEFAULT_CHARS = "l,I,H,h,k,d,b,n,o,x,a,E,T"
# Straight-stemmed letters: their axis *is* the design slant
DEFAULT_STEM_CHARS = "I,H,T,k,E"
CURVE_STEPS = 8


def flatten(font: TTFont, char: str) -> list[list[tuple[float, float]]]:
    cmap = font.getBestCmap() or {}
    name = cmap.get(ord(char))
    if name is None:
        return []
    glyph_set = font.getGlyphSet()
    path = pathops.Path()
    decomposed = DecomposingRecordingPen(glyph_set)
    glyph_set[name].draw(decomposed)
    decomposed.replay(path.getPen())
    path.convertConicsToQuads()

    recorded = RecordingPen()
    path.draw(recorded)
    polylines: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    last: tuple[float, float] | None = None

    for op, args in recorded.value:
        if op == "moveTo":
            last = (float(args[0][0]), float(args[0][1]))
            current = [last]
        elif op == "lineTo":
            last = (float(args[0][0]), float(args[0][1]))
            current.append(last)
        elif op in ("qCurveTo", "curveTo"):
            points = [(float(p[0]), float(p[1])) for p in args]
            if last is not None and len(points) == 2 and op == "qCurveTo":
                p0, p1, p2 = last, points[0], points[1]
                for i in range(1, CURVE_STEPS + 1):
                    t = i / CURVE_STEPS
                    u = 1 - t
                    current.append(
                        (
                            u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
                        )
                    )
            else:
                current.append(points[-1])
            last = points[-1]
        elif op in ("closePath", "endPath"):
            if current:
                if current[0] != current[-1]:
                    current.append(current[0])
                polylines.append(current)
            current = []
            last = None
    if current:
        polylines.append(current)
    return polylines


def ink_centre(polylines, y: float) -> float | None:
    crossings: list[float] = []
    for poly in polylines:
        for i in range(len(poly) - 1):
            x0, y0 = poly[i]
            x1, y1 = poly[i + 1]
            if y0 == y1:
                continue
            lo, hi = (y0, y1) if y0 < y1 else (y1, y0)
            if lo <= y < hi:
                crossings.append(x0 + (y - y0) / (y1 - y0) * (x1 - x0))
    crossings.sort()
    area = span = 0.0
    for i in range(0, len(crossings) - 1, 2):
        run = crossings[i + 1] - crossings[i]
        area += (crossings[i] + crossings[i + 1]) / 2 * run
        span += run
    return area / span if span > 0 else None


def slant_degrees(font: TTFont, char: str, samples: int = 20) -> float | None:
    polylines = flatten(font, char)
    if not polylines:
        return None
    ys = [p[1] for poly in polylines for p in poly]
    y_lo, y_hi = min(ys), max(ys)
    points = []
    for i in range(samples):
        y = y_lo + (y_hi - y_lo) * (0.25 + 0.5 * i / max(samples - 1, 1))
        centre = ink_centre(polylines, y)
        if centre is not None:
            points.append((y, centre))
    if len(points) < 5:
        return None
    mean_y = statistics.fmean(p[0] for p in points)
    mean_x = statistics.fmean(p[1] for p in points)
    denominator = sum((p[0] - mean_y) ** 2 for p in points)
    if denominator == 0:
        return None
    slope = sum((p[0] - mean_y) * (p[1] - mean_x) for p in points) / denominator
    return math.degrees(math.atan(slope))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument("--chars", default=DEFAULT_CHARS)
    ap.add_argument("--stem-chars", default=DEFAULT_STEM_CHARS)
    args = ap.parse_args()

    chars = [c for c in args.chars.split(",") if c]
    stem_chars = {c for c in args.stem_chars.split(",") if c}

    for path in args.fonts:
        if not path.exists():
            print(f"missing file: {path}", file=sys.stderr)
            return 2
        font = TTFont(path)
        print(f"\n=== {path.name} (post.italicAngle = {font['post'].italicAngle}) ===")
        stems: list[float] = []
        for char in chars:
            angle = slant_degrees(font, char)
            if angle is None:
                continue
            mark = " ← stem" if char in stem_chars else ""
            print(f"  {char}  {angle:+6.2f}°{mark}")
            if char in stem_chars:
                stems.append(angle)
        font.close()
        if stems:
            median = statistics.median(stems)
            print(f"  >> stem median {median:+.2f}°  → CJK_SLANT_DEG={median:.1f}")
        else:
            print("  >> no straight-stem glyphs measured", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
