#!/usr/bin/env python3
"""Force terminal cell advances to match Unicode East_Asian_Width.

Why:
  Terminals never ask the font how wide a character is — they size cells from
  the Unicode EAW table via wcwidth(). EAW N/Na/H always get exactly 1 cell;
  W/F always get 2. Any advance that disagrees draws into the wrong number of
  cells (overlap or empty half-cell).

  LilexSansSC NFM mostly inherits correct half-cell symbols from Lilex, but a
  handful of codepoints still ship wrong (e.g. U+205D at full, ⚡ and some
  CJK radicals/IDCs at half). This script:

    1. narrows EAW N/Na/H glyphs currently at full advance into the half cell
       (optional donor transplant; default geometric fit / recentre)
    2. widens EAW W/F glyphs currently at half advance into the full cell
       (recentre only — never scale up)

Ambiguous-width (EAW=A) codepoints are left alone by default — CJK users who
set "ambiguous = wide" legitimately want those at 2 cells. --include-ambiguous
narrows them too.

Usage:
  narrow-symbol-widths.py FONT.ttf --no-donor
  narrow-symbol-widths.py FONT.ttf --donor OtherHalfWidth.ttf
"""
from __future__ import annotations

import argparse
import copy
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

    Only W/F are hard full-width. Ambiguous (A) is *not* protected: when a
    glyph is shared by EAW=N and EAW=A (common for dual-mapped PUA stubs),
    terminals always allocate 1 cell to N, so half wins. Pure-A glyphs are
    simply not selected as narrow targets unless --include-ambiguous.
    """
    del include_ambiguous  # kept for call-site compatibility with serif
    return {gname for cp, gname in cmap.items() if _eaw(cp) in WIDE_EAW}


def _reverse_cmap(cmap: dict) -> dict[str, list[int]]:
    rev: dict[str, list[int]] = {}
    for cp, gname in cmap.items():
        rev.setdefault(gname, []).append(cp)
    return rev


def _unique_glyph_name(glyf, base: str) -> str:
    name = f"wide.{base}"
    n = 0
    while name in glyf:
        n += 1
        name = f"wide.{base}.{n}"
    return name


def _remap_codepoints(font: TTFont, codepoints: list[int], new_gname: str) -> None:
    want = set(codepoints)
    for table in font["cmap"].tables:
        data = getattr(table, "cmap", None)
        if not data:
            continue
        for cp in want:
            if cp in data:
                data[cp] = new_gname


def _ensure_glyph_slot(font: TTFont, name: str) -> None:
    """Register a new glyph name in glyph order / maxp before writing glyf+hmtx."""
    order = font.getGlyphOrder()
    if name not in order:
        order.append(name)
        font.setGlyphOrder(order)
        font["maxp"].numGlyphs = len(order)


def _shift_glyph_x(glyph, glyf, dx: float) -> None:
    """Translate a simple or composite glyf glyph by dx (in place)."""
    if glyph.numberOfContours == 0:
        return
    if glyph.isComposite():
        for component in glyph.components:
            component.x += int(round(dx))
    else:
        coords = glyph.coordinates
        glyph.coordinates = type(coords)(
            [(x + dx, y) for x, y in coords]
        )
    glyph.recalcBounds(glyf)


def _glyph_x_bounds(glyph) -> tuple[float, float] | None:
    if glyph.numberOfContours == 0:
        return None
    try:
        return float(glyph.xMin), float(glyph.xMax)
    except AttributeError:
        return None


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
        # Force-load glyf/hmtx/(optional vmtx) before mutating maxp/glyphOrder.
        half = _half_unit(font)
        full = half * 2
        cmap = font.getBestCmap() or {}
        glyf = font["glyf"]
        hmtx = font["hmtx"].metrics
        # Intermediate Dual may ship a stub/broken vmtx. If it cannot be
        # decompiled, drop vmtx/vhea so later save (after glyf edits) succeeds.
        vmtx = None
        if "vmtx" in font:
            try:
                vmtx = font["vmtx"].metrics
            except Exception:
                del font.reader.tables["vmtx"]
                if "vmtx" in font.tables:
                    del font.tables["vmtx"]
                if "vhea" in font:
                    try:
                        del font.reader.tables["vhea"]
                    except Exception:
                        pass
                    if "vhea" in font.tables:
                        del font.tables["vhea"]
                vmtx = None
        _ = font.getGlyphOrder()
        glyph_set = font.getGlyphSet()
        rev = _reverse_cmap(cmap)

        donor_cmap = donor.getBestCmap() if donor else {}
        donor_hmtx = donor["hmtx"].metrics if donor else None
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
                # No donor, or the donor keeps this one wide too.
                # EAW is not negotiable in a terminal, so fit it anyway.
                bounds = _bounds(glyph_set, gname)
                if bounds is None:
                    glyf[gname] = _draw_glyph(glyph_set, gname)
                    done[gname] = "blank"
                else:
                    x0, _y0, x1, _y1 = bounds
                    width = x1 - x0
                    scale = min(1.0, half / width) if width > 0 else 1.0
                    new_w = width * scale
                    dx = (half - new_w) / 2.0 - x0 * scale
                    glyf[gname] = _draw_glyph(
                        glyph_set, gname, (scale, 0, 0, 1, dx, 0)
                    )
                    done[gname] = "fitted" if scale < 1.0 else "recentred"
            glyf[gname].recalcBounds(glyf)
            lsb = glyf[gname].xMin if glyf[gname].numberOfContours else 0
            hmtx[gname] = (half, lsb)

        # Symmetric case: EAW=W/F at half advance → re-centre in full cell.
        # If the outline is also used by a half-required codepoint (Nerd PUA,
        # N/Na/H, …), duplicate it so those mappings keep half advance.
        widened = 0
        duplicated = 0
        if widen:
            seen: set[str] = set()
            for cp, gname in sorted(cmap.items()):
                if _eaw(cp) not in WIDE_EAW or hmtx[gname][0] != half:
                    continue
                if gname in seen:
                    continue
                seen.add(gname)

                wide_cps = [c for c in rev[gname] if _eaw(c) in WIDE_EAW]
                other_cps = [c for c in rev[gname] if _eaw(c) not in WIDE_EAW]

                xb = _glyph_x_bounds(glyf[gname])
                dx = (full - (xb[1] - xb[0])) / 2.0 - xb[0] if xb else (full - half) / 2.0

                if other_cps:
                    # Shared with Nerd/half codepoints: fork a private full copy
                    # and remap only the W/F cmap entries (handwriting pattern).
                    new_name = _unique_glyph_name(glyf, gname)
                    _ensure_glyph_slot(font, new_name)
                    glyf[new_name] = copy.deepcopy(glyf[gname])
                    hmtx[new_name] = hmtx[gname]
                    if vmtx is not None and gname in vmtx:
                        vmtx[new_name] = vmtx[gname]
                    _shift_glyph_x(glyf[new_name], glyf, dx)
                    lsb = (
                        glyf[new_name].xMin
                        if glyf[new_name].numberOfContours
                        else hmtx[new_name][1]
                    )
                    hmtx[new_name] = (full, lsb)
                    _remap_codepoints(font, wide_cps, new_name)
                    for c in wide_cps:
                        cmap[c] = new_name
                    rev[new_name] = wide_cps
                    rev[gname] = other_cps
                    duplicated += 1
                else:
                    _shift_glyph_x(glyf[gname], glyf, dx)
                    lsb = (
                        glyf[gname].xMin
                        if glyf[gname].numberOfContours
                        else hmtx[gname][1]
                    )
                    hmtx[gname] = (full, lsb)
                widened += 1
            lines.append(
                f"{path.name}: widened {widened} glyph(s) to full cell "
                f"(duplicated={duplicated})"
            )

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
        help="optional half-width TTF to transplant outlines from",
    )
    ap.add_argument(
        "--no-donor",
        action="store_true",
        help="fit existing outlines geometrically (default path for LilexSansSC)",
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
            "error: pass --donor <half-width.ttf> or --no-donor", file=sys.stderr
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
