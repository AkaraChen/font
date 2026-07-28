#!/usr/bin/env python3
"""Advertise a dual-width (2:1) mono as monospaced to the hosts that ask.

Run as: python3 -m fontkit.fix_terminal_metrics FONT.ttf [...]

Why:
  post.isFixedPitch is the flag hosts actually read to answer "is this a
  monospaced font?" -- macOS Core Text (kCTFontTraitMonoSpace), fontconfig,
  Chromium/VS Code font pickers, and most terminals' "monospace only" filters.
  FontForge (and therefore the Nerd patcher) recomputes it from the advance
  histogram, sees a dual-width font, and clears it to 0, so the patched build
  stops being offered as a mono font even though upstream Sarasa ships
  isFixedPitch=1 on exactly the same 2:1 grid. We restore it, and pin the
  PANOSE proportion byte to 9 (Monospaced) for the hosts that read PANOSE.

  OS/2.xAvgCharWidth is left at the half-cell rather than the glyph average
  (~800+ on a dual-width font), which is what a monospaced font is expected to
  advertise. fontkit.verify2to1 --profile compact gates it.

Not done here, deliberately:
  This module used to also rewrite head.xMin/xMax from half/full-advance glyphs
  only, to keep rare multi-em glyphs (U+2E3B ⸻) out of the font bbox. That was
  a workaround for a "large empty band on the right of the terminal" report
  which turned out to be a terminal bug, not a font one -- and the tight bbox
  it wrote is non-conformant: OpenType says head's bbox covers *all* glyphs.
  Removed in KIT-284. Do not reintroduce it without a font-side reproduction.

Does NOT change per-glyph advances (Nerd PUA, CJK, ASCII stay as built).
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
    """Apply the mono advertisement fixes to `path` in place."""
    lines: list[str] = []
    font = TTFont(path)
    try:
        half = half_unit(font)
        os2 = font["OS/2"]

        old_avg = os2.xAvgCharWidth
        os2.xAvgCharWidth = half
        lines.append(
            f"{path.name}: OS/2.xAvgCharWidth {old_avg} → {half} (half-cell)"
        )

        post = font["post"]
        if post.isFixedPitch != 1:
            lines.append(
                f"{path.name}: post.isFixedPitch {post.isFixedPitch} → 1 "
                "(dual-width 2:1 is still a fixed grid; matches upstream Sarasa)"
            )
            post.isFixedPitch = 1

        # PANOSE byte 4 (bProportion) == 9 is "Monospaced" for family kind 2.
        panose = os2.panose
        if panose.bFamilyType == 2 and panose.bProportion != 9:
            lines.append(
                f"{path.name}: PANOSE bProportion {panose.bProportion} → 9 (Monospaced)"
            )
            panose.bProportion = 9

        if not dry_run:
            font.save(path)
            lines.append(f"{path.name}: saved")
        else:
            lines.append(f"{path.name}: dry-run (not saved)")
        return lines
    finally:
        font.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    any_err = False
    for path in args.fonts:
        if not path.is_file():
            print(f"error: not a file: {path}", file=sys.stderr)
            any_err = True
            continue
        for line in fix_font(path, dry_run=args.dry_run):
            print(line)
    return 1 if any_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
