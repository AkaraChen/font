#!/usr/bin/env python3
"""Measure WenKai vs Radon stroke widths and recommend an embolden strength.

Answers the two weight questions this build has to get right:

1. **Which WenKai weight backs which Radon weight?** WenKai ships Light /
   Regular / Medium and no Bold; Monaspace runs heavy for its nominal weight,
   so the pairing has to be measured. `--survey` prints the table.
2. **How much embolden closes the gap?** Only the sample glyphs are stroked (7
   Han glyphs, in memory) instead of all 45 k, so a sweep costs seconds.

Metric: scanline vertical-stem median (shared with `serif/tools/`). Verticals
dominate the optical weight of mixed CN/EN mono text; Kai horizontals and
brush-tapered strokes are thinner by design and are reported but not targeted.

Usage:
  calibrate_cjk_weight.py --latin RadonLatin-Bold.ttf --cjk LXGWWenKai-Medium.ttf
  calibrate_cjk_weight.py --survey --latin A.ttf --latin B.ttf --cjk X.ttf --cjk Y.ttf
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem

TOOLS = Path(__file__).resolve().parents[2] / "serif" / "tools"
sys.path.insert(0, str(TOOLS))

from embolden_cjk import embolden_path  # noqa: E402
from measure_stroke_width import (  # noqa: E402
    DEFAULT_CJK,
    DEFAULT_LATIN,
    glyph_to_path,
    measure_stems,
    path_to_polylines,
)


def open_font(path: Path, upm: int) -> TTFont:
    font = TTFont(str(path))
    if font["head"].unitsPerEm != upm:
        scale_upem(font, upm)
    return font


def stem_medians(font: TTFont, chars: list[str], strength: float = 0.0) -> tuple[float, float]:
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()
    verticals: list[float] = []
    horizontals: list[float] = []
    for ch in chars:
        name = cmap.get(ord(ch))
        if name is None:
            continue
        path = glyph_to_path(glyph_set, name)
        if strength > 0:
            path = embolden_path(path, strength)
        if not list(path.contours):
            continue
        stems = measure_stems(path_to_polylines(path))
        if stems["v_median"] is not None:
            verticals.append(stems["v_median"])
        if stems["h_median"] is not None:
            horizontals.append(stems["h_median"])
    return (
        statistics.median(verticals) if verticals else float("nan"),
        statistics.median(horizontals) if horizontals else float("nan"),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--latin", action="append", type=Path, required=True)
    ap.add_argument("--cjk", action="append", type=Path, required=True)
    ap.add_argument("--upm", type=int, default=1000)
    ap.add_argument("--latin-chars", default=",".join(DEFAULT_LATIN))
    ap.add_argument("--cjk-chars", default=",".join(DEFAULT_CJK))
    ap.add_argument(
        "--strengths",
        default="0,2,4,6,8,10,12,14,16,18",
        help="embolden sweep (only used with a single --latin/--cjk pair)",
    )
    ap.add_argument("--survey", action="store_true", help="cross table only, no sweep")
    args = ap.parse_args()

    latin_chars = [c for c in args.latin_chars.split(",") if c]
    cjk_chars = [c for c in args.cjk_chars.split(",") if c]

    latin_stems: dict[str, tuple[float, float]] = {}
    for path in args.latin:
        font = open_font(path, args.upm)
        latin_stems[path.name] = stem_medians(font, latin_chars)
        font.close()
        v, h = latin_stems[path.name]
        print(f"Latin {path.name:40} v={v:7.2f}  h={h:7.2f}")

    print()
    for path in args.cjk:
        font = open_font(path, args.upm)
        v, h = stem_medians(font, cjk_chars)
        font.close()
        deltas = "  ".join(
            f"{name.split('-')[-1].replace('.ttf', ''):>10}: {v - lv:+7.2f}"
            for name, (lv, _) in latin_stems.items()
        )
        print(f"CJK   {path.name:40} v={v:7.2f}  h={h:7.2f}   Δv vs {deltas}")

    if args.survey or len(args.latin) != 1 or len(args.cjk) != 1:
        return 0

    target_v, target_h = latin_stems[args.latin[0].name]
    font = open_font(args.cjk[0], args.upm)
    print(f"\nsweep: {args.cjk[0].name} → target v={target_v:.2f} ({args.latin[0].name})")
    print(f"{'s':>6} {'cjk v':>8} {'Δv':>8} {'cjk h':>8} {'Δh':>8}")
    best: tuple[float, float] | None = None
    for token in args.strengths.split(","):
        if not token.strip():
            continue
        s = float(token)
        v, h = stem_medians(font, cjk_chars, strength=s)
        print(f"{s:6g} {v:8.2f} {v - target_v:+8.2f} {h:8.2f} {h - target_h:+8.2f}")
        if best is None or abs(v - target_v) < abs(best[1] - target_v):
            best = (s, v)
    font.close()
    if best:
        print(f"\nBEST strength={best[0]:g}  cjk v={best[1]:.2f}  Δv={best[1] - target_v:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
