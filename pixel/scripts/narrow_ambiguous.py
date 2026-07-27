#!/usr/bin/env python3
"""Narrow East_Asian_Width=Ambiguous punctuation to the half cell.

Why this exists
---------------
A terminal never asks the font how wide a character is -- it sizes the cell
from wcwidth, and EAW=Ambiguous codepoints (“ ” ‘ ’ … · ‥ ․ ‧) get exactly one
cell in every default configuration. Fusion's ``zh_hans`` / ``zh_hant`` flavors
draw those nine at 1200 (two cells) with the ink parked in the right half, so
``“心`` renders the quote straight on top of the following character.

Fusion's own ``latin`` / ``ja`` / ``ko`` flavors of the *same release* draw the
same nine at 600 on the same 12px grid. This step transplants those drawings
into the product, so the ink lands where the terminal put the cell.

Targets are derived, not hard-coded: a codepoint qualifies when the base draws
it full-width and the donor draws it half-width. Anything whose donor ink does
not fit inside [0, half] is a hard failure rather than a silent squeeze.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates


def half_unit(font: TTFont) -> int:
    cmap = font.getBestCmap() or {}
    name = cmap.get(ord("A"))
    if not name:
        raise SystemExit("missing reference glyph 'A'")
    half = font["hmtx"][name][0]
    if half <= 0:
        raise SystemExit(f"advance('A')={half} invalid")
    return half


def reverse_cmap(font: TTFont) -> dict[str, list[int]]:
    rev: dict[str, list[int]] = {}
    for cp, name in (font.getBestCmap() or {}).items():
        rev.setdefault(name, []).append(cp)
    return rev


def copy_outline(dst_glyph, dst_glyf, src_glyph) -> None:
    """Overwrite dst's contours with src's (both simple, same UPM/grid)."""
    if src_glyph.isComposite():
        raise SystemExit("donor glyph is composite; expected a simple outline")
    dst_glyph.numberOfContours = src_glyph.numberOfContours
    if src_glyph.numberOfContours == 0:
        for attr in ("coordinates", "flags", "endPtsOfContours"):
            if hasattr(dst_glyph, attr):
                delattr(dst_glyph, attr)
        dst_glyph.xMin = dst_glyph.yMin = dst_glyph.xMax = dst_glyph.yMax = 0
        return
    dst_glyph.coordinates = GlyphCoordinates(list(src_glyph.coordinates))
    dst_glyph.flags = list(src_glyph.flags)
    dst_glyph.endPtsOfContours = list(src_glyph.endPtsOfContours)
    dst_glyph.program = src_glyph.program if hasattr(src_glyph, "program") else None
    if dst_glyph.program is None and hasattr(dst_glyph, "program"):
        del dst_glyph.program
    dst_glyph.recalcBounds(dst_glyf)


def narrow_font(path: Path, donor_path: Path, *, dry_run: bool = False) -> list[str]:
    lines: list[str] = []
    font = TTFont(path)
    donor = TTFont(donor_path)
    try:
        if font["head"].unitsPerEm != donor["head"].unitsPerEm:
            raise SystemExit(
                f"UPM mismatch: {path.name}={font['head'].unitsPerEm} "
                f"{donor_path.name}={donor['head'].unitsPerEm}"
            )
        half = half_unit(font)
        full = half * 2
        if half_unit(donor) != half:
            raise SystemExit(f"donor half cell {half_unit(donor)} != {half}")

        cmap = font.getBestCmap() or {}
        dcmap = donor.getBestCmap() or {}
        hmtx = font["hmtx"]
        dhmtx = donor["hmtx"]
        glyf = font["glyf"]
        dglyf = donor["glyf"]
        rev = reverse_cmap(font)

        targets = [
            cp
            for cp, name in sorted(cmap.items())
            if hmtx[name][0] == full
            and cp in dcmap
            and dhmtx[dcmap[cp]][0] == half
        ]

        for cp in targets:
            name = cmap[cp]
            dname = dcmap[cp]
            shared = [c for c in rev.get(name, []) if c != cp]
            if shared:
                raise SystemExit(
                    f"U+{cp:04X}: glyph {name} is shared with "
                    + ", ".join(f"U+{c:04X}" for c in shared)
                )
            dglyph = dglyf[dname]
            if dglyph.numberOfContours and not (0 <= dglyph.xMin and dglyph.xMax <= half):
                raise SystemExit(
                    f"U+{cp:04X}: donor ink [{dglyph.xMin}, {dglyph.xMax}] "
                    f"escapes the half cell [0, {half}]"
                )
            copy_outline(glyf[name], glyf, dglyph)
            hmtx.metrics[name] = (half, dhmtx[dname][1])
            lines.append(
                f"{path.name}: U+{cp:04X} {chr(cp)!r} {name} ← {donor_path.name}:{dname} "
                f"advance {full} → {half}"
            )

        if not targets:
            lines.append(f"{path.name}: no full-width ambiguous punctuation found")
        else:
            lines.append(f"{path.name}: narrowed {len(targets)} glyph(s) to {half}")
        if not dry_run and targets:
            font.save(path)
    finally:
        font.close()
        donor.close()
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument(
        "--donor",
        required=True,
        type=Path,
        help="half-width donor (Fusion latin/ja flavor, same release)",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    for path in args.fonts:
        for line in narrow_font(path, args.donor, dry_run=args.dry_run):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
