#!/usr/bin/env python3
"""Force terminal cell advances to match Unicode East_Asian_Width.

Why:
  Terminals never ask the font how wide a character is — they size cells from
  the Unicode EAW table via wcwidth(). EAW N/Na/H always get exactly 1 cell;
  W/F always get 2. Any advance that disagrees draws into the wrong number of
  cells (overlap or empty half-cell).

  Merged dual-width products mostly inherit correct half-cell symbols from
  their Latin source, but a handful of codepoints still ship wrong (e.g. U+205D
  at full, ⚡ and some CJK radicals/IDCs at half). Sarasa's *Mono* families are
  worse: they draw whole blocks of neutral-width symbols at full advance, which
  is the '⏵ looks fullwidth' bug. This script:

    1. narrows EAW N/Na/H glyphs currently at full advance into the half cell
       (optional donor transplant — Sarasa *Term* carries properly redrawn
       half-width outlines; default is a geometric fit / recentre)
    2. widens EAW W/F glyphs currently at half advance into the full cell
       (recentre only — never scale up)

Ambiguous-width (EAW=A) codepoints are left alone by default — CJK users who
set "ambiguous = wide" legitimately want those at 2 cells. --include-ambiguous
narrows them too (matching upstream Sarasa Term behaviour).

Two behaviours differ per family and are therefore flags, not forks:

  --protect-ambiguous   never narrow an outline that is *also* reachable from
                        an EAW=A codepoint. serif wants this: its Sarasa source
                        shares one outline across N and A codepoints far more
                        often, and squashing those regresses the A set for CJK
                        users. Elsewhere half wins on a shared N/A outline,
                        because a terminal gives N exactly one cell.
  --widen-shared        what to do when an EAW=W/F glyph at half advance shares
                        its outline with a half-required codepoint (Nerd PUA,
                        N/Na/H):
                          fork — copy the outline, widen the copy and repoint
                                 only the W/F cmap entries (default)
                          skip — leave it alone (serif)
  --narrow-shared       the mirror image: an EAW=N/Na/H codepoint at full
                        advance whose outline is also reachable from an EAW=W/F
                        codepoint. IBM Plex Sans TC/JP/KR map U+FF64 ､ (H) and
                        U+FE51 ︑ (W) to one glyph, so narrowing in place would
                        squash the wide one and skipping leaves ､ two cells wide
                        in a terminal.
                          fork — copy the outline, narrow the copy and repoint
                                 only the N/Na/H cmap entries (default)
                          skip — leave it alone (the behaviour before KIT-282)

Run as:
  python3 -m fontkit.narrow_symbol_widths FONT.ttf --no-donor
  python3 -m fontkit.narrow_symbol_widths FONT.ttf --donor SarasaTermSlabSC-Regular.ttf
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


def _wide_names(cmap: dict) -> set[str]:
    """Glyph names reachable from an EAW=W/F codepoint.

    Narrowing one of these in place would squash a character that genuinely
    needs two cells, so they are never narrowed in place. They can still be
    *forked* — see `--narrow-shared`, and `_ambiguous_names` for the softer
    protection that deliberately cannot be.
    """
    return {gname for cp, gname in cmap.items() if _eaw(cp) in WIDE_EAW}


def _ambiguous_names(
    cmap: dict, include_ambiguous: bool, protect_ambiguous: bool
) -> set[str]:
    """Glyph names --protect-ambiguous refuses to touch at all.

    When a glyph is shared by EAW=N and EAW=A (common for dual-mapped PUA
    stubs) terminals still allocate exactly 1 cell to N, so half wins by
    default. serif asks for the opposite with --protect-ambiguous, because
    Sarasa shares outlines across width classes far more often and squashing
    those regresses the A set for CJK users.

    Not forkable, deliberately: --protect-ambiguous is a request to leave the
    outline alone, and forking would hand N a narrow copy — a different product
    decision than the flag asks for.
    """
    if not protect_ambiguous or include_ambiguous:
        return set()
    return {gname for cp, gname in cmap.items() if _eaw(cp) == "A"}


def _reverse_cmap(cmap: dict) -> dict[str, list[int]]:
    rev: dict[str, list[int]] = {}
    for cp, gname in cmap.items():
        rev.setdefault(gname, []).append(cp)
    return rev


def _unique_glyph_name(glyf, base: str, prefix: str = "wide") -> str:
    name = f"{prefix}.{base}"
    n = 0
    while name in glyf:
        n += 1
        name = f"{prefix}.{base}.{n}"
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


WIDEN_MODES = ("fork", "skip")
NARROW_MODES = ("fork", "skip")


def narrow_font(
    path: Path,
    donor_path: Path | None,
    *,
    include_ambiguous: bool = False,
    widen: bool = True,
    widen_shared: str = "fork",
    narrow_shared: str = "fork",
    protect_ambiguous: bool = False,
    dry_run: bool = False,
) -> list[str]:
    if widen_shared not in WIDEN_MODES:
        raise SystemExit(f"--widen-shared must be one of {WIDEN_MODES}")
    if narrow_shared not in NARROW_MODES:
        raise SystemExit(f"--narrow-shared must be one of {NARROW_MODES}")
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
        wide_names = _wide_names(cmap)
        untouchable = _ambiguous_names(cmap, include_ambiguous, protect_ambiguous)

        targets: list[tuple[int, str]] = []
        # gname -> the narrow-required codepoints that want their own copy of it
        forks: dict[str, list[int]] = {}
        for cp, gname in sorted(cmap.items()):
            if _eaw(cp) not in classes:
                continue
            if hmtx[gname][0] != full:
                continue
            if gname in untouchable:
                continue
            if gname in wide_names:
                # Shared with a codepoint that genuinely needs two cells. In
                # place is wrong (it squashes the wide one) and skipping is
                # wrong too (a terminal gives this cp one cell either way), so
                # the only correct answer is a private narrow copy.
                if narrow_shared == "fork":
                    forks.setdefault(gname, []).append(cp)
                continue
            targets.append((cp, gname))

        lines.append(
            f"{path.name}: half={half} full={full}; "
            f"{len(targets)} narrow-required codepoint(s) at full advance"
            + (f", {len(forks)} shared with a wide codepoint" if forks else "")
        )

        def fit_narrow(dst: str, src: str, donor_cp: int) -> str:
            """Draw `src` into `dst` at half advance. dst may equal src."""
            donor_name = donor_cmap.get(donor_cp) if donor_cmap else None
            if donor_name is not None and donor_hmtx[donor_name][0] == half:
                glyf[dst] = _draw_glyph(donor_set, donor_name)
                how = "donor"
            else:
                # No donor, or the donor keeps this one wide too.
                # EAW is not negotiable in a terminal, so fit it anyway.
                bounds = _bounds(glyph_set, src)
                if bounds is None:
                    glyf[dst] = _draw_glyph(glyph_set, src)
                    how = "blank"
                else:
                    x0, _y0, x1, _y1 = bounds
                    width = x1 - x0
                    scale = min(1.0, half / width) if width > 0 else 1.0
                    new_w = width * scale
                    dx = (half - new_w) / 2.0 - x0 * scale
                    glyf[dst] = _draw_glyph(glyph_set, src, (scale, 0, 0, 1, dx, 0))
                    how = "fitted" if scale < 1.0 else "recentred"
            glyf[dst].recalcBounds(glyf)
            lsb = glyf[dst].xMin if glyf[dst].numberOfContours else 0
            hmtx[dst] = (half, lsb)
            return how

        done: dict[str, str] = {}  # gname -> how it was fixed
        for cp, gname in targets:
            if gname in done:
                continue
            done[gname] = fit_narrow(gname, gname, cp)

        # The forks, after the in-place pass so a forked source is never itself
        # a narrow target.
        narrow_forked = 0
        for gname, cps in sorted(forks.items()):
            new_name = _unique_glyph_name(glyf, gname, prefix="narrow")
            _ensure_glyph_slot(font, new_name)
            hmtx[new_name] = hmtx[gname]
            if vmtx is not None and gname in vmtx:
                vmtx[new_name] = vmtx[gname]
            fit_narrow(new_name, gname, cps[0])
            _remap_codepoints(font, cps, new_name)
            taken = set(cps)
            for c in cps:
                cmap[c] = new_name
            rev[new_name] = list(cps)
            rev[gname] = [c for c in rev.get(gname, []) if c not in taken]
            narrow_forked += 1
        if narrow_forked:
            lines.append(
                f"{path.name}: forked {narrow_forked} outline(s) so a "
                "narrow-required codepoint could keep the half cell"
            )

        # Symmetric case: EAW=W/F at half advance → re-centre in full cell.
        # If the outline is also used by a half-required codepoint (Nerd PUA,
        # N/Na/H, …), duplicate it so those mappings keep half advance.
        widened = 0
        duplicated = 0
        if widen and widen_shared == "skip":
            # serif: an outline shared with a half-required codepoint is left
            # alone entirely. Sarasa reuses outlines across width classes far
            # more than the merged families do, and forking every one of them
            # inflates the glyph count for a gap nobody reported.
            narrow_names = {
                gname for cp, gname in cmap.items() if _eaw(cp) in NARROW_EAW
            }
            seen_skip: set[str] = set()
            for cp, gname in sorted(cmap.items()):
                if _eaw(cp) not in WIDE_EAW or hmtx[gname][0] != half:
                    continue
                if gname in seen_skip or gname in narrow_names:
                    continue
                seen_skip.add(gname)
                bounds = _bounds(glyph_set, gname)
                dx = (full - (bounds[2] - bounds[0])) / 2.0 - bounds[0] if bounds else 0
                glyf[gname] = _draw_glyph(glyph_set, gname, (1, 0, 0, 1, dx, 0))
                glyf[gname].recalcBounds(glyf)
                lsb = glyf[gname].xMin if glyf[gname].numberOfContours else 0
                hmtx[gname] = (full, lsb)
                widened += 1
            lines.append(f"{path.name}: widened {widened} glyph(s) to full cell")
        elif widen:
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
        help="fit existing outlines geometrically (the merged families' path — "
        "they have no Sarasa Term donor on their grid)",
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
    ap.add_argument(
        "--widen-shared",
        choices=WIDEN_MODES,
        default="fork",
        help="EAW=W/F glyph at half advance whose outline is shared with a "
        "half-required codepoint: fork a full-width copy (default) or skip it "
        "(serif)",
    )
    ap.add_argument(
        "--narrow-shared",
        choices=NARROW_MODES,
        default="fork",
        help="EAW=N/Na/H glyph at full advance whose outline is shared with an "
        "EAW=W/F codepoint: fork a half-width copy (default) or skip it",
    )
    ap.add_argument(
        "--protect-ambiguous",
        action="store_true",
        help="never narrow an outline also reachable from an EAW=A codepoint "
        "(serif); ignored under --include-ambiguous",
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
            widen_shared=args.widen_shared,
            narrow_shared=args.narrow_shared,
            protect_ambiguous=args.protect_ambiguous,
            dry_run=args.dry_run,
        ):
            print(line)
    return 1 if any_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
