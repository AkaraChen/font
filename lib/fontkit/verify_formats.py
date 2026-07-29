#!/usr/bin/env python3
"""Gate the `format` axis: prove what each format claims about itself.

`fontkit convert` makes two very different promises (see convert.py), so this
asks two very different questions:

**WOFF2 claims to be lossless.** Not "close enough for the web" — the same
`glyf` outlines in a Brotli container. So the check is byte equality: every
glyph's compiled `glyf` record, plus `hmtx` and `cmap`, must be identical to the
source TTF's. Anything less and the WOFF2 is a second product that happens to
look similar, and shipping it under the same version would be a lie about which
bytes a reader is rendering.

**OTF claims only to be the same design.** It cannot claim byte equality: qu2cu
refits every curve within a tolerance and the contours are reversed. What it can
be held to is the set of things a format conversion must not quietly change —
the glyph inventory, the advance widths, the character map, the family name —
plus the tolerance itself: no glyph's bounding box may move further than
`--max-err` (with a unit of slack for the bbox being a max over refitted points
rather than a single fitted one). Whether the outlines are *right* is a question
for the OTF's own fingerprint baseline, which is why it has one.

A converted product with no source TTF beside it is a failure, not a skip: it
means the build shipped a format whose provenance nobody can check.

Usage
  fontkit verify-formats <dir|font> [...] [--max-err 1.0]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

# The bbox of a refitted contour is a maximum over its points, so it can sit up
# to one fitting tolerance away in each direction plus the rounding the
# charstring integers introduce.
BBOX_SLACK = 1.0

DERIVED_SUFFIXES = (".woff2", ".woff", ".otf")


def _digest(chunks) -> str:
    h = hashlib.sha256()
    for chunk in chunks:
        h.update(chunk)
    return h.hexdigest()


def _glyf_bytes(font: TTFont) -> dict[str, bytes]:
    glyf = font["glyf"]
    out = {}
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        glyph.expand(glyf)
        out[name] = glyph.compile(glyf)
    return out


def _advances(font: TTFont) -> dict[str, int]:
    hmtx = font["hmtx"]
    return {name: hmtx[name][0] for name in font.getGlyphOrder()}


def _cmap(font: TTFont) -> dict[int, str]:
    return dict(font["cmap"].getBestCmap())


def _bounds(font: TTFont) -> dict[str, tuple | None]:
    glyph_set = font.getGlyphSet()
    out = {}
    for name in font.getGlyphOrder():
        pen = BoundsPen(glyph_set)
        glyph_set[name].draw(pen)
        out[name] = pen.bounds
    return out


def check_woff2(ttf: Path, derived: Path, failures: list[str]) -> None:
    """Container re-wrap: the outlines must be the same bytes."""
    source = TTFont(ttf, recalcBBoxes=False, recalcTimestamp=False)
    target = TTFont(derived, recalcBBoxes=False, recalcTimestamp=False)
    try:
        if target.flavor != derived.suffix.lstrip("."):
            failures.append(f"{derived.name}: flavor is {target.flavor!r}")

        src_glyphs, dst_glyphs = _glyf_bytes(source), _glyf_bytes(target)
        if src_glyphs.keys() != dst_glyphs.keys():
            failures.append(
                f"{derived.name}: glyph inventory differs from {ttf.name} "
                f"({len(src_glyphs)} → {len(dst_glyphs)})"
            )
        moved = sorted(
            name for name in src_glyphs.keys() & dst_glyphs.keys()
            if src_glyphs[name] != dst_glyphs[name]
        )
        if moved:
            failures.append(
                f"{derived.name}: {len(moved)} glyph outline(s) are not byte-identical "
                f"to {ttf.name} — WOFF2 must be a re-wrap, not a rebuild. "
                f"First: {', '.join(moved[:5])}"
            )
        if _advances(source) != _advances(target):
            failures.append(f"{derived.name}: advance widths differ from {ttf.name}")
        if _cmap(source) != _cmap(target):
            failures.append(f"{derived.name}: cmap differs from {ttf.name}")

        digest = _digest(src_glyphs[n] for n in sorted(src_glyphs))
        print(
            f"  {derived.name:<44} lossless re-wrap of {ttf.name} "
            f"({len(src_glyphs)} glyphs, outline digest {digest[:16]})"
        )
    finally:
        source.close()
        target.close()


def check_otf(ttf: Path, derived: Path, max_err: float, failures: list[str]) -> None:
    """Curve conversion: same design, same metrics, outlines within tolerance."""
    source = TTFont(ttf, recalcBBoxes=False, recalcTimestamp=False)
    target = TTFont(derived, recalcBBoxes=False, recalcTimestamp=False)
    try:
        if target.sfntVersion != "OTTO" or "CFF " not in target:
            failures.append(f"{derived.name}: not a CFF font — an .otf with glyf is a mislabelled TTF")
            return
        leftover = [tag for tag in ("glyf", "loca", "fpgm", "prep", "cvt ") if tag in target]
        if leftover:
            failures.append(
                f"{derived.name}: carries TrueType-only table(s) {leftover} — "
                "CFF has no interpreter to run them"
            )
        if source.getGlyphOrder() != target.getGlyphOrder():
            failures.append(f"{derived.name}: glyph order differs from {ttf.name}")
            return
        if _advances(source) != _advances(target):
            failures.append(
                f"{derived.name}: advance widths differ from {ttf.name} — "
                "a curve conversion must not move the cell"
            )
        if _cmap(source) != _cmap(target):
            failures.append(f"{derived.name}: cmap differs from {ttf.name}")
        src_name = source["name"].getDebugName(1)
        dst_name = target["name"].getDebugName(1)
        if src_name != dst_name:
            failures.append(
                f"{derived.name}: family name is {dst_name!r}, source says {src_name!r}"
            )

        tolerance = max_err + BBOX_SLACK
        src_bounds, dst_bounds = _bounds(source), _bounds(target)
        worst, worst_glyph = 0.0, None
        for name, before in src_bounds.items():
            after = dst_bounds[name]
            if before is None or after is None:
                if before != after:
                    failures.append(f"{derived.name}: {name} is empty on one side only")
                continue
            delta = max(abs(a - b) for a, b in zip(before, after))
            if delta > worst:
                worst, worst_glyph = delta, name
        if worst > tolerance:
            failures.append(
                f"{derived.name}: {worst_glyph} moved {worst:.2f} units, over the "
                f"{tolerance:.2f} the qu2cu fit is allowed"
            )
        print(
            f"  {derived.name:<44} CFF conversion of {ttf.name} "
            f"({len(src_bounds)} glyphs, worst bbox drift {worst:.2f} ≤ {tolerance:.2f})"
        )
    finally:
        source.close()
        target.close()


def collect(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found += [
                p for p in sorted(path.rglob("*"))
                if p.is_file() and p.suffix.lower() in DERIVED_SUFFIXES
            ]
        elif path.suffix.lower() in DERIVED_SUFFIXES:
            found.append(path)
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", type=Path, help="product directories or files")
    ap.add_argument(
        "--max-err",
        type=float,
        default=1.0,
        help="the qu2cu tolerance the OTFs were built with (default 1.0)",
    )
    args = ap.parse_args(argv)

    derived = collect(args.paths)
    if not derived:
        print(
            "notice: no .woff2 / .otf products found — nothing to verify. "
            "A family that declares only `formats = [\"ttf\"]` reaches this.",
            file=sys.stderr,
        )
        return 0

    failures: list[str] = []
    for product in derived:
        ttf = product.with_suffix(".ttf")
        if not ttf.is_file():
            failures.append(
                f"{product.name}: no {ttf.name} beside it — a converted product "
                "whose source is not shipped cannot be checked against anything"
            )
            continue
        if product.suffix.lower() == ".otf":
            check_otf(ttf, product, args.max_err, failures)
        else:
            check_woff2(ttf, product, failures)

    if failures:
        print("\nformat verification failed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print(f"\n{len(derived)} converted product(s) verified against their source TTFs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
