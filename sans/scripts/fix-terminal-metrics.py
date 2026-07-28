#!/usr/bin/env python3
"""Terminal-oriented OS/2 / head / post metric hygiene for dual-width pixel mono.

Same rationale as serif/scripts/fix-terminal-metrics.py:
  - OS/2.xAvgCharWidth → half-cell
  - post.isFixedPitch → 1
  - PANOSE bProportion → 9 (Monospaced)
  - head bbox from half/full advances only
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont


def half_unit(font: TTFont) -> int:
    cmap = font.getBestCmap() or {}
    name = cmap.get(ord("A"))
    if not name:
        raise SystemExit("missing reference glyph 'A'")
    half = font["hmtx"][name][0]
    if half <= 0:
        raise SystemExit(f"advance('A')={half} invalid")
    return half


def fix_font(path: Path, *, dry_run: bool = False) -> list[str]:
    lines: list[str] = []
    font = TTFont(path)
    try:
        half = half_unit(font)
        full = half * 2
        os2 = font["OS/2"]
        head = font["head"]
        hmtx = font["hmtx"]
        glyf = font["glyf"] if "glyf" in font else None

        old_avg = os2.xAvgCharWidth
        os2.xAvgCharWidth = half
        lines.append(f"{path.name}: OS/2.xAvgCharWidth {old_avg} → {half}")

        post = font["post"]
        if post.isFixedPitch != 1:
            lines.append(f"{path.name}: post.isFixedPitch {post.isFixedPitch} → 1")
            post.isFixedPitch = 1

        panose = os2.panose
        if panose.bFamilyType == 2 and panose.bProportion != 9:
            lines.append(
                f"{path.name}: PANOSE bProportion {panose.bProportion} → 9"
            )
            panose.bProportion = 9

        if glyf is not None:
            xs: list[int] = []
            ys: list[int] = []
            for gname, (adv, _lsb) in hmtx.metrics.items():
                if adv not in (half, full):
                    continue
                g = glyf.get(gname)
                if g is None or g.numberOfContours == 0:
                    continue
                if g.isComposite():
                    try:
                        g.recalcBounds(glyf)
                    except Exception:
                        continue
                if not hasattr(g, "xMin"):
                    continue
                xs.extend([g.xMin, g.xMax])
                ys.extend([g.yMin, g.yMax])
            if xs and ys:
                old = (head.xMin, head.yMin, head.xMax, head.yMax)
                head.xMin, head.xMax = min(xs), max(xs)
                head.yMin, head.yMax = min(ys), max(ys)
                new = (head.xMin, head.yMin, head.xMax, head.yMax)
                if old != new:
                    lines.append(f"{path.name}: head bbox {old} → {new}")

        if not dry_run:
            font.save(path)
    finally:
        font.close()
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    for path in args.fonts:
        for line in fix_font(path, dry_run=args.dry_run):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
