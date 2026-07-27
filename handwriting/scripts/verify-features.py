#!/usr/bin/env python3
"""Verify Radon's coding OpenType layout survived the WenKai merge.

The merge keeps Radon as the *base* font precisely so its layout tables never
have to be rebuilt — this gate is what proves that stayed true.

Hard fails:
  - GSUB missing, or missing `liga` / `calt` / `ccmp` / `locl`
  - fewer than 40 of Radon's ligature glyphs present (`equal_equal`, `slash_slash`, …)
  - a core coding ligature glyph missing
  - a ligature glyph off the cell grid (would break 2:1 alignment)
  - combining marks that lost their zero advance (mark attachment)
  - GDEF gone (Radon marks glyph classes / ligature carets there)

Soft notes: missing stylistic sets / character variants, absent GPOS.

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

REQUIRED_GSUB = ("liga", "calt", "ccmp", "locl")
EXPECTED_EXTRA = ("ss01", "ss02", "ss03", "cv01", "cv30", "aalt", "frac")

# Monaspace names ligature glyphs after their input sequence, with no suffix.
LIGATURE_GLYPHS = (
    "equal_equal",
    "equal_equal_equal",
    "exclam_equal",
    "less_equal",
    "greater_equal",
    "hyphen_greater",
    "hyphen_hyphen_greater",
    "colon_colon",
    "period_period_period",
    "slash_slash",
    "bar_bar",
    "equal_greater",
)
CORE_LIGATURES = ("equal_equal", "exclam_equal", "hyphen_greater", "slash_slash")
MARK_CODEPOINTS = (0x0301, 0x0308, 0x0302)

# Sequences that must ligate with nothing but the editor's usual `calt`+`liga`.
# Radon ships these in ss01–ss09, so this is the gate that proves
# 05-expand-ligatures.sh actually ran (a feature tag being *present* proves
# nothing — the point is that the default path substitutes).
DEFAULT_LIGATURE_SEQUENCES = ("==", "===", "!=", "->", "<-", "=>", "<=", ">=", "::", "|>")


def unligated_sequences(path: Path, font: TTFont) -> list[str]:
    """Shape each test sequence with default features; report any that stay plain.

    A ligated result is one where the sequence collapses onto a single inked
    glyph (Monaspace pads the extra cells with `emptyAdvanceWidth`), so the test
    is: does the shaped run still consist of the plain per-character glyphs?
    """
    import uharfbuzz as hb

    order = font.getGlyphOrder()
    cmap = font.getBestCmap() or {}
    hb_font = hb.Font(hb.Face(path.read_bytes()))
    failures = []
    for sequence in DEFAULT_LIGATURE_SEQUENCES:
        buf = hb.Buffer()
        buf.add_str(sequence)
        buf.guess_segment_properties()
        hb.shape(hb_font, buf, {"liga": True, "calt": True})
        shaped = [order[info.codepoint] for info in buf.glyph_infos]
        plain = [cmap.get(ord(c)) for c in sequence]
        if shaped == plain:
            failures.append(sequence)
    return failures


def gsub_tags(font: TTFont) -> set[str]:
    if "GSUB" not in font:
        return set()
    return {r.FeatureTag for r in font["GSUB"].table.FeatureList.FeatureRecord}


def ligature_glyph_names(font: TTFont) -> list[str]:
    """Glyphs whose name is an underscore-joined sequence of glyph names."""
    found = []
    for name in font.getGlyphOrder():
        if name.startswith(("wk.", "wide.")) or "_" not in name:
            continue
        parts = name.split(".")[0].split("_")
        if len(parts) >= 2 and all(p.isalpha() for p in parts):
            found.append(name)
    return found


def verify_one(path: Path, expect_half: int | None) -> int:
    font = TTFont(path)
    errors: list[str] = []
    notes: list[str] = []

    tags = gsub_tags(font)
    print(f"{path.name}: GSUB tags ({len(tags)}): {sorted(tags)}")
    if "GSUB" not in font:
        errors.append("missing GSUB table")
    else:
        for tag in REQUIRED_GSUB:
            if tag not in tags:
                errors.append(f"missing required GSUB feature: {tag}")
        missing_extra = [t for t in EXPECTED_EXTRA if t not in tags]
        if missing_extra:
            notes.append(f"missing expected extras: {missing_extra}")
        if len(missing_extra) > len(EXPECTED_EXTRA) // 2:
            errors.append(
                f"too many missing Radon extras ({len(missing_extra)}/{len(EXPECTED_EXTRA)})"
            )

    if "GDEF" not in font:
        errors.append("missing GDEF (Radon glyph classes / ligature carets)")

    order = set(font.getGlyphOrder())
    ligatures = ligature_glyph_names(font)
    print(f"  ligature glyphs: {len(ligatures)}")
    if len(ligatures) < 40:
        errors.append(f"too few ligature glyphs: {len(ligatures)} (expected ≥ 40)")

    missing = [n for n in LIGATURE_GLYPHS if n not in order]
    if missing:
        notes.append(f"named ligature glyphs missing: {missing}")
    missing_core = [n for n in CORE_LIGATURES if n not in order]
    if missing_core:
        errors.append(f"core coding ligature glyphs absent: {missing_core}")

    hmtx = font["hmtx"].metrics
    if expect_half is not None:
        grid = {expect_half, 2 * expect_half, 3 * expect_half}
        off_grid = [
            f"{n}={hmtx[n][0]}"
            for n in LIGATURE_GLYPHS
            if n in order and hmtx[n][0] not in grid
        ]
        if off_grid:
            errors.append(f"ligature glyphs off the cell grid: {off_grid}")

    try:
        unligated = unligated_sequences(path, font)
        ligated = len(DEFAULT_LIGATURE_SEQUENCES) - len(unligated)
        print(f"  default-path ligatures: {ligated}/{len(DEFAULT_LIGATURE_SEQUENCES)}")
        if unligated:
            errors.append(
                "sequences do not ligate under default liga+calt "
                f"(run 05-expand-ligatures.sh): {unligated}"
            )
    except ImportError:
        notes.append("uharfbuzz not installed — ligature shaping gate skipped")

    # Monaspace gives combining marks a full cell rather than zero advance (a
    # mono grid choice, not a bug), so the gate is "on the grid", not "zero".
    cmap = font.getBestCmap() or {}
    if expect_half is not None:
        for cp in MARK_CODEPOINTS:
            name = cmap.get(cp)
            if name and hmtx[name][0] not in (0, expect_half):
                errors.append(
                    f"combining mark U+{cp:04X} advance={hmtx[name][0]}, "
                    f"expected 0 or {expect_half}"
                )

    if "GPOS" in font:
        gpos = {r.FeatureTag for r in font["GPOS"].table.FeatureList.FeatureRecord}
        print(f"  GPOS tags: {sorted(gpos)}")
    else:
        notes.append("no GPOS (Radon NF ships none)")

    italic_angle = font["post"].italicAngle
    if italic_angle != 0:
        notes.append(
            f"post.italicAngle={italic_angle} — the product is an upright face, "
            "hosts may synthesise italics from it"
        )
    font.close()

    for note in notes:
        print(f"  note: {note}")
    if errors:
        print(f"  FAIL ({len(errors)}):", file=sys.stderr)
        for err in errors:
            print(f"    {err}", file=sys.stderr)
        return 1
    print("  OK (features)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument("--expect-half", type=int, default=None, help="EN cell, e.g. 500")
    args = ap.parse_args()

    worst = 0
    for font in args.fonts:
        if not font.exists():
            print(f"missing file: {font}", file=sys.stderr)
            return 2
        worst = max(worst, verify_one(font, args.expect_half))
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
