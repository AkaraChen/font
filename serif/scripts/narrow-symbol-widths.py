#!/usr/bin/env python3
"""Force terminal-narrow symbols to half-cell advance in a dual-width mono.

Why:
  Sarasa's *Mono* families draw neutral- and ambiguous-width symbols at FULL
  (2-cell) advance. Terminals do not ask the font how wide a character is --
  they use the Unicode East_Asian_Width table via wcwidth(). For every
  codepoint with EAW in {N, Na, H} a terminal allocates exactly ONE cell,
  unconditionally and with no user setting to change it.

  So a glyph like U+23F5 '⏵' (EAW=N) shipped at advance 1000 gets one cell of
  space and two cells of ink: it looks "full width", overlaps its neighbour,
  and drags the rest of the line out of alignment. This is a real metric bug,
  not a terminal preference -- unlike EAW=A (ambiguous) codepoints such as
  U+25B6 '▶', which terminals *can* be configured to treat as wide.

  Sarasa's *Term* families already carry properly redesigned half-width
  drawings of these symbols. The cleanest fix is therefore to transplant the
  donor outlines rather than squash the Mono ones.

Usage:
  narrow-symbol-widths.py FONT.ttf --donor SarasaTermSlabSC-Regular.ttf

Without a donor (--no-donor) the script falls back to geometric fitting:
recentre the outline in the half cell, x-compressing it first if it is wider.
That keeps the metrics correct but the shapes are less refined.

Ambiguous-width (EAW=A) codepoints are left alone by default -- CJK users who
set "ambiguous = wide" legitimately want those at 2 cells. --include-ambiguous
narrows them too (matching upstream Sarasa Term behaviour).
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

try:
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.ttLib import TTFont
except ImportError as exc:  # pragma: no cover
    print("error: fontTools is required (pip install fonttools)", file=sys.stderr)
    raise SystemExit(2) from exc


NARROW_EAW = ("N", "Na", "H")  # terminals always give these exactly 1 cell
WIDE_EAW = ("W", "F")  # terminals always give these exactly 2 cells


def _half_unit(font: TTFont) -> int:
    cmap = font.getBestCmap() or {}
    name = cmap.get(ord("A"))
    if not name:
        raise SystemExit("missing reference glyph 'A'")
    half = font["hmtx"][name][0]
    if half <= 0:
        raise SystemExit(f"advance('A')={half} invalid")
    return half


def _eaw(cp: int) -> str:
    try:
        return unicodedata.east_asian_width(chr(cp))
    except (ValueError, TypeError):
        return "N"


def _draw_glyph(glyph_set, gname: str, transform=None):
    """Decompose gname into a TTGlyphPen-ready recording, optionally transformed."""
    rec = DecomposingRecordingPen(glyph_set)
    glyph_set[gname].draw(rec)
    pen = TTGlyphPen(None)
    rec.replay(TransformPen(pen, transform) if transform else pen)
    return pen.glyph()


def _bounds(glyph_set, gname: str):
    from fontTools.pens.boundsPen import BoundsPen

    bp = BoundsPen(glyph_set)
    glyph_set[gname].draw(bp)
    return bp.bounds


def _protected_names(cmap: dict, include_ambiguous: bool) -> set[str]:
    """Glyph names also reachable from a codepoint that must stay full width.

    A single outline can be shared by several codepoints; narrowing it would
    silently break the ones that legitimately need 2 cells.
    """
    keep_wide = set(WIDE_EAW) if include_ambiguous else set(WIDE_EAW) | {"A"}
    return {gname for cp, gname in cmap.items() if _eaw(cp) in keep_wide}


def narrow_font(
    path: Path,
    donor_path: Path | None,
    *,
    include_ambiguous: bool = False,
    widen: bool = True,
    dry_run: bool = False,
) -> list[str]:
    lines: list[str] = []
    font = TTFont(path)
    donor = TTFont(donor_path) if donor_path else None
    try:
        half = _half_unit(font)
        full = half * 2
        cmap = font.getBestCmap() or {}
        hmtx = font["hmtx"]
        glyf = font["glyf"]
        glyph_set = font.getGlyphSet()

        donor_cmap = donor.getBestCmap() if donor else {}
        donor_hmtx = donor["hmtx"] if donor else None
        donor_set = donor.getGlyphSet() if donor else None
        if donor is not None and donor["head"].unitsPerEm != font["head"].unitsPerEm:
            raise SystemExit(
                f"donor UPM {donor['head'].unitsPerEm} != font UPM "
                f"{font['head'].unitsPerEm}; refusing to mix"
            )

        classes = set(NARROW_EAW) | ({"A"} if include_ambiguous else set())
        protected = _protected_names(cmap, include_ambiguous)

        targets: list[tuple[int, str]] = []
        for cp, gname in sorted(cmap.items()):
            if _eaw(cp) not in classes:
                continue
            if hmtx[gname][0] != full:
                continue
            if gname in protected:
                continue
            targets.append((cp, gname))

        lines.append(
            f"{path.name}: half={half} full={full}; "
            f"{len(targets)} narrow-required codepoint(s) at full advance"
        )

        done: dict[str, str] = {}  # gname -> how it was fixed
        for cp, gname in targets:
            if gname in done:
                continue
            donor_name = donor_cmap.get(cp) if donor_cmap else None
            if donor_name is not None and donor_hmtx[donor_name][0] == half:
                glyf[gname] = _draw_glyph(donor_set, donor_name)
                done[gname] = "donor"
            else:
                # No donor, or the donor keeps this one wide too (upstream Term
                # still has a handful, e.g. the long arrows U+27F5..U+27FF).
                # EAW is not negotiable in a terminal, so fit it anyway.
                bounds = _bounds(glyph_set, gname)
                if bounds is None:
                    # blank glyph: advance-only fix
                    glyf[gname] = _draw_glyph(glyph_set, gname)
                    done[gname] = "blank"
                else:
                    x0, _y0, x1, _y1 = bounds
                    width = x1 - x0
                    scale = min(1.0, half / width) if width > 0 else 1.0
                    # scale about the outline's own left edge, then centre
                    new_w = width * scale
                    dx = (half - new_w) / 2.0 - x0 * scale
                    glyf[gname] = _draw_glyph(
                        glyph_set, gname, (scale, 0, 0, 1, dx, 0)
                    )
                    done[gname] = "fitted" if scale < 1.0 else "recentred"
            glyf[gname].recalcBounds(glyf)
            lsb = glyf[gname].xMin if glyf[gname].numberOfContours else 0
            hmtx[gname] = (half, lsb)

        # Symmetric case: a handful of EAW=W codepoints (☰ ⚡ ㆴ …) ship at half
        # advance, so terminals reserve 2 cells and draw 1 -- a gap instead of
        # an overlap. Re-centre them in the full cell; never scale up.
        widened = 0
        if widen:
            narrow_names = {
                gname for cp, gname in cmap.items() if _eaw(cp) in NARROW_EAW
            }
            seen: set[str] = set()
            for cp, gname in sorted(cmap.items()):
                if _eaw(cp) not in WIDE_EAW or hmtx[gname][0] != half:
                    continue
                if gname in seen or gname in narrow_names:
                    continue
                seen.add(gname)
                bounds = _bounds(glyph_set, gname)
                dx = (full - (bounds[2] - bounds[0])) / 2.0 - bounds[0] if bounds else 0
                glyf[gname] = _draw_glyph(glyph_set, gname, (1, 0, 0, 1, dx, 0))
                glyf[gname].recalcBounds(glyf)
                lsb = glyf[gname].xMin if glyf[gname].numberOfContours else 0
                hmtx[gname] = (full, lsb)
                widened += 1
            lines.append(f"{path.name}: widened {widened} glyph(s) to full cell")

        by_how: dict[str, int] = {}
        for how in done.values():
            by_how[how] = by_how.get(how, 0) + 1
        lines.append(
            f"{path.name}: narrowed {len(done)} glyph(s) "
            + (", ".join(f"{k}={v}" for k, v in sorted(by_how.items())) or "none")
        )
        if dry_run:
            lines.append(f"{path.name}: dry-run (not saved)")
        else:
            font.save(path)
            lines.append(f"{path.name}: saved")
        return lines
    finally:
        font.close()
        if donor is not None:
            donor.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument(
        "--donor",
        type=Path,
        help="Sarasa Term* TTF to take half-width symbol outlines from",
    )
    ap.add_argument(
        "--no-donor",
        action="store_true",
        help="skip the donor and fit the existing outlines geometrically",
    )
    ap.add_argument(
        "--include-ambiguous",
        action="store_true",
        help="also narrow EAW=A codepoints (▶ ① × …); off by default",
    )
    ap.add_argument(
        "--no-widen",
        action="store_true",
        help="do not re-centre EAW=W glyphs that ship at half advance",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if not args.donor and not args.no_donor:
        print(
            "error: pass --donor <SarasaTerm*.ttf> or --no-donor", file=sys.stderr
        )
        return 2
    if args.donor and not args.donor.is_file():
        print(f"error: donor not found: {args.donor}", file=sys.stderr)
        return 2

    any_err = False
    for path in args.fonts:
        if not path.is_file():
            print(f"error: not a file: {path}", file=sys.stderr)
            any_err = True
            continue
        for line in narrow_font(
            path,
            None if args.no_donor else args.donor,
            include_ambiguous=args.include_ambiguous,
            widen=not args.no_widen,
            dry_run=args.dry_run,
        ):
            print(line)
    return 1 if any_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
