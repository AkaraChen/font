#!/usr/bin/env python3
"""Verify Lilex coding OpenType features survived the dual-width merge.

Checks (hard-fail):
  - GSUB present with `calt` (programming ligatures path)
  - A core set of stylistic / variant tags still registered
  - Enough `.liga` / calt-related private glyphs remain
  - Zero-width combining marks stay advance 0 (mark attach)

Exit: 0 pass · 1 fail · 2 usage / I/O
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from fontTools.ttLib import TTFont
except ImportError as exc:  # pragma: no cover
    print("error: fontTools is required (pip install fonttools)", file=sys.stderr)
    raise SystemExit(2) from exc

# Required GSUB feature tags for a usable Lilex coding product
REQUIRED_GSUB = ("calt", "ccmp", "locl")
# Strongly expected Lilex coding extras (warn if missing, fail if most gone)
EXPECTED_EXTRA = (
    "ss01",
    "ss02",
    "ss03",
    "ss04",
    "cv01",
    "zero",
    "aalt",
)
# Sample ligature glyph stems that Lilex ships for common coding sequences
SAMPLE_LIGA = (
    "equal_equal.liga",
    "equal_equal_equal.liga",
    "exclam_equal.liga",
    "less_equal.liga",
    "greater_equal.liga",
    "hyphen_hyphen.liga",
    "colon_equal.liga",
    "period_period_period.liga",
    "equal_colon_equal.liga",
)


def gsub_tags(font: TTFont) -> set[str]:
    if "GSUB" not in font:
        return set()
    return {fr.FeatureTag for fr in font["GSUB"].table.FeatureList.FeatureRecord}


def verify_one(path: Path) -> int:
    font = TTFont(path)
    errors: list[str] = []
    notes: list[str] = []

    tags = gsub_tags(font)
    print(f"{path.name}: GSUB tags ({len(tags)}): {sorted(tags)}")

    if "GSUB" not in font:
        errors.append("missing GSUB table")
    else:
        for t in REQUIRED_GSUB:
            if t not in tags:
                errors.append(f"missing required GSUB feature: {t}")
        missing_extra = [t for t in EXPECTED_EXTRA if t not in tags]
        if missing_extra:
            notes.append(f"missing expected extras: {missing_extra}")
        if len(missing_extra) > len(EXPECTED_EXTRA) // 2:
            errors.append(
                f"too many missing Lilex extras ({len(missing_extra)}/{len(EXPECTED_EXTRA)})"
            )

    order = set(font.getGlyphOrder())
    liga_glyphs = [n for n in order if ".liga" in n]
    print(f"  .liga glyphs: {len(liga_glyphs)}")
    if len(liga_glyphs) < 50:
        errors.append(f"too few .liga glyphs: {len(liga_glyphs)} (expected ≥ 50)")

    missing_liga = [n for n in SAMPLE_LIGA if n not in order]
    if missing_liga:
        # Some Lilex versions rename; soft-fail only if almost all gone
        notes.append(f"sample liga names missing: {missing_liga}")
        if len(missing_liga) >= len(SAMPLE_LIGA) - 2:
            errors.append("core coding ligature glyphs largely absent")

    # Zero-width marks must stay 0 so mark GPOS still works
    hmtx = font["hmtx"].metrics
    cm = font.getBestCmap() or {}
    mark_cps = (0x0301, 0x0308, 0x0302)  # acute, diaeresis, circumflex comb
    for cp in mark_cps:
        g = cm.get(cp)
        if g is None:
            continue
        w = hmtx[g][0]
        if w != 0:
            errors.append(f"combining mark U+{cp:04X} advance={w}, expected 0")

    if "GPOS" in font:
        gpos_tags = {fr.FeatureTag for fr in font["GPOS"].table.FeatureList.FeatureRecord}
        print(f"  GPOS tags: {sorted(gpos_tags)}")
    else:
        notes.append("no GPOS (Lilex usually has mark)")

    font.close()

    for n in notes:
        print(f"  note: {n}")
    if errors:
        print(f"  FAIL ({len(errors)}):", file=sys.stderr)
        for e in errors:
            print(f"    {e}", file=sys.stderr)
        return 1
    print("  OK (features)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fonts", nargs="+", type=Path)
    args = ap.parse_args()

    worst = 0
    for f in args.fonts:
        if not f.exists():
            print(f"missing file: {f}", file=sys.stderr)
            return 2
        worst = max(worst, verify_one(f))
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
