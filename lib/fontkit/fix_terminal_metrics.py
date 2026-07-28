#!/usr/bin/env python3
"""Terminal-oriented OS/2 / head metric hygiene for dual-width (2:1) monos.

Run as: python3 -m fontkit.fix_terminal_metrics FONT.ttf [...]

Why:
  Sarasa-style dual-width fonts legitimately mix advance 500 (half) and 1000
  (full). FontTools / the Nerd patcher often leave OS/2.xAvgCharWidth as a
  glyph-average (~800+) rather than the half-cell unit. Some terminal and GUI
  layout paths treat that average as "the" monospaced cell width, which shows
  up as a large empty band on the right of the window after switching fonts.

  head.xMin/xMax also expand to rare multi-em glyphs (e.g. U+2E3B ⸻) and
  combining ornaments; a few hosts use the font bbox when estimating cell
  size. We recompute head bounds from glyphs whose advance is half or full
  only (still honest for normal text; multi-em dashes keep their advances).

  post.isFixedPitch is the flag hosts actually read to answer "is this a
  monospaced font?" -- macOS Core Text (kCTFontTraitMonoSpace), fontconfig,
  Chromium/VS Code font pickers, and most terminals' "monospace only" filters.
  FontForge (and therefore the Nerd patcher) recomputes it from the advance
  histogram, sees a dual-width font, and clears it to 0, so the patched build
  stops being offered as a mono font even though upstream Sarasa ships
  isFixedPitch=1 on exactly the same 2:1 grid. We restore it, and pin the
  PANOSE proportion byte to 9 (Monospaced) for the hosts that read PANOSE.

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


def fix_font(
    path: Path, *, dry_run: bool = False, keep_bbox: bool = False
) -> list[str]:
    """Apply the metric fixes to `path` in place.

    keep_bbox pins the half/full-only head bbox computed below by disabling
    TTFont.recalcBBoxes before the save. Only serif passes it. Without it
    fontTools recomputes head from *every* glyph on save and the bbox written
    here is discarded — which is what pixel / rounded / sans / typewriter have
    always shipped, so the flag defaults to off to keep their products
    byte-identical. See docs/build-toolchain.md; flipping it for the other four
    is a deliberate product change, not a refactor.
    """
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

        if glyf is not None:
            x_min = y_min = 10**9
            x_max = y_max = -(10**9)
            used = 0
            for gname, (adv, _lsb) in hmtx.metrics.items():
                if adv not in (half, full):
                    continue
                g = glyf.get(gname)
                if g is None or g.numberOfContours == 0:
                    continue
                try:
                    gx0, gy0, gx1, gy1 = g.xMin, g.yMin, g.xMax, g.yMax
                except AttributeError:
                    continue
                x_min = min(x_min, gx0)
                y_min = min(y_min, gy0)
                x_max = max(x_max, gx1)
                y_max = max(y_max, gy1)
                used += 1
            if used and x_min < x_max:
                old = (head.xMin, head.yMin, head.xMax, head.yMax)
                head.xMin, head.yMin, head.xMax, head.yMax = (
                    int(x_min),
                    int(y_min),
                    int(x_max),
                    int(y_max),
                )
                lines.append(
                    f"{path.name}: head bbox {old} → "
                    f"({head.xMin},{head.yMin},{head.xMax},{head.yMax}) "
                    f"(from {used} half/full glyphs)"
                )
            else:
                lines.append(f"{path.name}: head bbox unchanged (no glyf bounds)")

        if not dry_run:
            if keep_bbox:
                # TTFont.recalcBBoxes (constructor default True) recomputes head
                # from *all* glyphs on save and undoes the half/full-only bbox.
                font.recalcBBoxes = False
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
    ap.add_argument(
        "--keep-bbox",
        action="store_true",
        help="pin the half/full-only head bbox instead of letting fontTools "
        "recompute it from every glyph on save (serif only — see fix_font)",
    )
    args = ap.parse_args(argv)

    any_err = False
    for path in args.fonts:
        if not path.is_file():
            print(f"error: not a file: {path}", file=sys.stderr)
            any_err = True
            continue
        for line in fix_font(path, dry_run=args.dry_run, keep_bbox=args.keep_bbox):
            print(line)
    return 1 if any_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
