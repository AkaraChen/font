#!/usr/bin/env python3
"""Produce a product in another format.

The `format` axis of the granularity contract (`packaged`) has three values, and
they are not three spellings of one operation. The split is the whole reason
this module is longer than a `font.flavor = ...` assignment:

**WOFF2 — a container, and nothing else.** `fontTools.ttLib.woff2` re-encodes
the same `glyf` outlines and the same tables with Brotli. Nothing is
re-rasterised, re-hinted or subsetted, so a WOFF2 and its source TTF are the
same font and a fingerprint taken through either agrees. `fontkit verify-formats`
proves that per product rather than asserting it here — see verify_formats.py.

**OTF — a real conversion.** OTF means CFF, and CFF means cubic Béziers, and
this entire pipeline is quadratic: the CJK donors are TrueType, and
`handwriting/scripts/prepare_latin.py` converts Monaspace's cubics *to*
quadratics with cu2qu precisely because one `glyf` table cannot hold both. Going
back is `qu2cu`, and it costs three things that are worth saying out loud:

  * **the outlines move.** qu2cu fits cubics to quadratics within `--max-err`
    font units. That is a tolerance, not an identity.
  * **TrueType hinting is gone.** `fpgm` / `prep` / `cvt ` / the per-glyph
    instructions are a TrueType interpreter program; CFF has no place to put
    them. An OTF of a hinted TTF is an unhinted font.
  * **contours reverse.** TrueType fills clockwise-outer, PostScript
    counter-clockwise-outer.

So an OTF is *a different product with the same design*, and it gets its own
fingerprint baseline (tools/fingerprint.py already dumps CFF charstrings) rather
than being diffed against the TTF's. KIT-283 is the phase that decided this is
worth having for the text profile — a reading face gets set in print and on the
desktop, and OTF is what that world asks for — and reversed handwriting's
earlier `[[build.unsupported]] formats = ["otf"]` declaration to get it. The
coding profile still ships TTF + WOFF2: a terminal face is hinted and lives in
editors, so an unhinted CFF version of it would be strictly worse.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont

# Re-wraps: same tables in, same tables out.
FLAVOURS = {"woff2": "woff2", "woff": "woff"}

# Real conversions.
CONVERSIONS = ("otf",)

FORMATS = tuple(sorted(FLAVOURS)) + CONVERSIONS

# The tolerance qu2cu is allowed when it fits a cubic to a run of quadratics, in
# font units at the product UPM (1000 here). Default in fontTools' own ttf2otf
# recipes and in afdko's; 1/1000 em is below what any rasteriser resolves and
# well under the ~5-unit stroke differences the calibration steps deliberately
# introduce. Exposed as a flag because it is the one number that decides how far
# the OTF outlines are allowed to be from the TTF's, and a build that changes it
# should have to say so.
DEFAULT_MAX_ERR = 1.0

# TrueType-only tables. They describe a `glyf` table or feed the TrueType
# interpreter, so in an OTF they are at best dead weight and at worst a lie
# about hinting the font no longer carries.
TRUETYPE_ONLY = (
    "glyf",
    "loca",
    "cvt ",
    "fpgm",
    "prep",
    "gasp",
    "hdmx",
    "LTSH",
    "VDMX",
    "TTFA",
)

# Not TrueType-only — but a digital signature over the old outlines says nothing
# true about the new ones, and a stale DSIG is worse than no DSIG: it is a claim
# of provenance that no longer holds. Upstream donors ship one (IBM Plex does),
# and it survives the merge steps.
INVALIDATED = ("DSIG",)


def rewrap(src: Path, dst: Path, fmt: str) -> None:
    """WOFF/WOFF2: the same font in another container."""
    font = TTFont(src, recalcBBoxes=False, recalcTimestamp=False)
    try:
        font.flavor = FLAVOURS[fmt]
        dst.parent.mkdir(parents=True, exist_ok=True)
        font.save(dst)
    finally:
        font.close()
    print(f"  {src.name} → {dst.name} ({dst.stat().st_size} bytes, container re-wrap)")


def _charstrings(font: TTFont, max_err: float) -> dict:
    """Every glyph, as a Type 2 charstring.

    Composites are decomposed first rather than passed through as CFF `seac` or
    left to the charstring pen: `Qu2CuPen` forwards components untouched, so a
    composite that reached `T2CharStringPen` would be decomposed *there* and its
    quadratics converted one-segment-per-curve by the base pen's exact
    quad→cubic fallback. That is not wrong, but it is a second conversion path
    with a different curve count, and "which of two conversions drew this glyph"
    is not a question a fingerprint diff should have to answer.
    """
    glyph_set = font.getGlyphSet()
    hmtx = font["hmtx"]
    charstrings = {}
    for name in font.getGlyphOrder():
        recorder = DecomposingRecordingPen(glyph_set)
        glyph_set[name].draw(recorder)
        pen = T2CharStringPen(hmtx[name][0], None)
        recorder.replay(
            Qu2CuPen(pen, max_err, all_cubic=True, reverse_direction=True)
        )
        charstrings[name] = pen.getCharString()
    return charstrings


def _font_info(font: TTFont) -> dict:
    """The CFF top dict, taken from the tables that already hold these facts."""
    names = font["name"]

    def name_id(nid: int, default: str = "") -> str:
        record = names.getDebugName(nid)
        return record if record else default

    head = font["head"]
    post = font["post"]
    ps_name = name_id(6) or name_id(4).replace(" ", "") or "Untitled"
    info = {
        "FullName": name_id(4, ps_name),
        "FamilyName": name_id(1, ps_name),
        "Weight": name_id(2, "Regular"),
        "isFixedPitch": bool(post.isFixedPitch),
        "ItalicAngle": post.italicAngle,
        "UnderlinePosition": post.underlinePosition,
        "UnderlineThickness": post.underlineThickness,
        # From head, not recomputed: the TTF's bounding box is the design's, and
        # a qu2cu fit inside --max-err cannot leave it.
        "FontBBox": [head.xMin, head.yMin, head.xMax, head.yMax],
    }
    notice = name_id(0)
    if notice:
        info["Notice"] = notice
    version = name_id(5)
    if version:
        info["version"] = version
    return ps_name, info


# No hinting is carried across, so there are no blue zones and no stem widths to
# declare. They are *absent* rather than present-and-empty: an empty CFF DICT
# array is not the same thing as a missing key, and AFDKO's `tx` — which is what
# `cffsubr` runs — rejects the zero-length form outright ("(cfr) invalid DICT
# array size"). Inventing values instead is what a hinting tool does, and doing
# it silently inside a format conversion would put numbers in the font that
# nobody measured.
#
# The two width keys stay because T2CharStringPen encodes each glyph's advance
# against them; both zero means every charstring carries its own width.
PRIVATE_DICT = {
    "nominalWidthX": 0,
    "defaultWidthX": 0,
}


def to_otf(src: Path, dst: Path, max_err: float, subroutinize: bool) -> None:
    font = TTFont(src, recalcBBoxes=False, recalcTimestamp=False)
    try:
        if "glyf" not in font:
            raise SystemExit(f"error: {src.name} has no glyf table — not a TrueType product")
        charstrings = _charstrings(font, max_err)
        ps_name, info = _font_info(font)

        for tag in TRUETYPE_ONLY + INVALIDATED:
            if tag in font:
                del font[tag]
        # maxp 1.0 carries fourteen TrueType-only maxima; the CFF version is
        # 0.5, which is numGlyphs and nothing else.
        font["maxp"].tableVersion = 0x00005000
        # post 2.0 stores glyph names; in an OTF the CFF charset does, and two
        # copies of the glyph order is exactly the sort of thing that drifts.
        font["post"].formatType = 3.0

        FontBuilder(font=font).setupCFF(ps_name, info, charstrings, PRIVATE_DICT)

        if subroutinize:
            _subroutinize(font)

        dst.parent.mkdir(parents=True, exist_ok=True)
        font.save(dst)
    finally:
        font.close()
    print(
        f"  {src.name} → {dst.name} ({dst.stat().st_size} bytes, "
        f"qu2cu max-err={max_err}{', subroutinized' if subroutinize else ''})"
    )


def _subroutinize(font: TTFont) -> None:
    """Factor repeated charstring runs into subroutines.

    Not cosmetic on these products: a CJK face is tens of thousands of glyphs
    built from a few thousand recurring components, and un-subroutinized CFF
    gives all that repetition back in full.

    Hard-required rather than best-effort. `cffsubr` shells out to AFDKO's `tx`,
    which is pinned in the build (nix/fontkit.nix); making it optional would
    mean the OTF a developer builds and the OTF CI builds are different files,
    and the fingerprint baseline would then be a property of who ran the build.
    """
    try:
        import cffsubr
    except ImportError as exc:  # pragma: no cover - the build always has it
        raise SystemExit(
            "error: cffsubr is not importable, so the CFF cannot be subroutinized. "
            "Build inside the pinned toolchain (`nix develop`), or pass "
            "--no-subroutinize and accept a larger, differently-fingerprinted OTF."
        ) from exc
    cffsubr.subroutinize(font, keep_glyph_names=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("fonts", nargs="+", type=Path, help="built TTF product(s)")
    ap.add_argument("--format", required=True, choices=FORMATS)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument(
        "--max-err",
        type=float,
        default=DEFAULT_MAX_ERR,
        help=f"qu2cu tolerance in font units, OTF only (default {DEFAULT_MAX_ERR})",
    )
    ap.add_argument(
        "--no-subroutinize",
        dest="subroutinize",
        action="store_false",
        help="skip CFF subroutinization (OTF only) — larger file, different fingerprint",
    )
    args = ap.parse_args(argv)

    for src in args.fonts:
        if not src.is_file():
            print(f"error: not a file: {src}", file=sys.stderr)
            return 2
        dst = args.out_dir / f"{src.stem}.{args.format}"
        if args.format in FLAVOURS:
            rewrap(src, dst, args.format)
        else:
            to_otf(src, dst, args.max_err, args.subroutinize)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
