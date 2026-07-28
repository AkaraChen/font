#!/usr/bin/env python3
"""The `text` profile gate — a reading face, checked as a reading face.

`fontkit verify-2to1` is the coding gate and every one of its assertions is a
statement about a terminal cell: strict 2:1, `post.isFixedPitch`, East_Asian_Width
conformance, Nerd icons at the half cell. Pointing it at a text product would
fail it for being correct, which is why this is a second gate rather than a
`--profile text` flag on the first one.

What a text face has to get right instead, one check per row of the Phase 6
判据 table:

  not-mono        `post.isFixedPitch == 0` and PANOSE bProportion != 9. Both
                  donors are monospaced, so these arrive *set* and the merge has
                  to clear them. A text face listed in a terminal's font picker
                  is the exact bug this catches.
  no-nerd         no Nerd Font icon codepoints. The coding profile's Latin donor
                  is a pre-patched Nerd build; taking the wrong one is a one-word
                  mistake in a derivation and produces a face that looks fine
                  until someone asks why a reading font carries 2 320 icons. Not
                  "no PUA": the plain donor legitimately ships Powerline — see
                  NERD_PATCH_RANGES.
  cjk-full        Han, CJK punctuation and fullwidth forms sit on the full cell.
  cjk-ambiguous   … and — are full width, i.e. they came from the CJK donor.
                  The coding gate asserts the *opposite* — a terminal gives
                  EAW=Ambiguous one cell — which is why the two profiles cannot
                  share a gate. The wider candidate set (‘ ’ “ ” ·) is checked
                  more weakly, at exactly the strength the rule has: each must
                  be on the half cell or the full cell and nothing in between,
                  because "in between" is the CJK donor's own proportional Latin
                  leaking in. LXGW WenKai draws those five at 350/1000, so the
                  merge is supposed to have declined them and kept Radon's.
  latin-cell      Latin is still the Latin design: ASCII is narrower than the
                  full cell, and it is not the CJK donor's fallback shapes.
  layout          `liga` is present and the stylistic sets are still separate
                  features — the coding profile folds ss01–ss10 into `calt` so
                  an editor turns every ligature on, and a reading face must not
                  have had that done to it. GPOS is reported, and required only
                  under `--require-gpos`: Monaspace ships none at all (it is a
                  mono design), so for handwriting the "keep the Latin kerning"
                  row is vacuous rather than violated. A family whose Latin
                  donor does kern turns the flag on.
  line-box        typographic vertical metrics: USE_TYPO_METRICS set, and a
                  non-zero typo line gap. A terminal wants the line box tight;
                  prose wants leading, and `sTypoLineGap == 0` is what a
                  terminal-tuned metric set looks like.

Exit codes match the coding gate: 0 pass, 1 a failed check, 2 usage / I/O.

Run as:
  python3 -m fontkit.verify_text [--expect-full 1000] FONT.ttf …
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

from fontkit.merge import CJK_PREFERRED_AMBIGUOUS

# Everyday Han that must be present and full width. Deliberately the same shape
# of check as the coding gate's, and deliberately smaller: this gate is about
# what makes a face *readable*, and a dense sweep of the Unified block is the
# coding gate's job.
CJK_FULL_REQUIRED = [ord(c) for c in "中文测试字体阅读排版汉字标点正文"]

# CJK punctuation whose whole purpose is to occupy a full cell.
CJK_PUNCT_FULL = [
    0x3000,  # ideographic space
    0x3001,  # 、
    0x3002,  # 。
    0x300C,  # 「
    0x300D,  # 」
    0xFF0C,  # ，
    0xFF1A,  # ：
    0xFF1B,  # ；
    0xFF1F,  # ？
    0xFF01,  # ！
]

# The icon sets a Nerd Font patch brings, and nothing else.
#
# "no Private Use codepoints at all" was the first version of this check and it
# is wrong: the plain Monaspace Radon ships 55 of them — Powerline (U+E0A0–E0D4)
# plus a handful of Monaspace's own — because plenty of un-patched monos draw
# Powerline separators. Failing on those would fail the correct donor.
#
# What only a patch produces is the icon corpus: Devicons, Codicons, Font
# Awesome, Octicons, Weather, Seti-UI, Material Design. Measured on the pins, the
# patched donor has 2 320 PUA glyphs and the plain one 55, so this is not a fine
# distinction in practice — but the ranges are the reason, not the count.
NERD_PATCH_RANGES = [
    (0xE200, 0xE2A9),  # Font Awesome Extension
    (0xE300, 0xE3E3),  # Weather
    (0xE5FA, 0xE6B1),  # Seti-UI + Custom
    (0xE700, 0xE7C5),  # Devicons
    (0xEA60, 0xEBEB),  # Codicons
    (0xED00, 0xEDEB),  # Codicons cont.
    (0xF000, 0xF2E0),  # Font Awesome
    (0xF300, 0xF372),  # Font Logos
    (0xF400, 0xF532),  # Octicons
    (0xF0001, 0xF1AF0),  # Material Design Icons (SMP)
]

# The features a coding build folds together. Seeing them still separate is the
# evidence that `fontkit expand-ligatures` did not run on this product.
STYLISTIC_SETS = tuple(f"ss{n:02d}" for n in range(1, 21))


def _label(cp: int) -> str:
    ch = chr(cp) if cp <= 0x10FFFF else "?"
    if ch.isprintable() and not ch.isspace():
        return f"U+{cp:04X} '{ch}'"
    return f"U+{cp:04X}"


def _features(font: TTFont, tag: str) -> set[str]:
    if tag not in font:
        return set()
    feature_list = getattr(font[tag].table, "FeatureList", None)
    if feature_list is None:
        return set()
    return {record.FeatureTag for record in feature_list.FeatureRecord}


def verify_font(
    path: Path,
    *,
    expect_full: int | None = None,
    require_layout: bool = True,
    require_gpos: bool = False,
) -> tuple[int, list[str]]:
    """Return (exit_code, report_lines). 0 pass · 1 failed check · 2 usage/I/O."""
    lines: list[str] = []
    failures: list[str] = []

    font = TTFont(path)
    try:
        cmap = font.getBestCmap() or {}
        hmtx = font["hmtx"]
        upm = font["head"].unitsPerEm

        han = ord("中")
        if han not in cmap:
            return 2, [f"{path}: missing reference glyph 中 — is this a CJK product?"]
        full = hmtx[cmap[han]][0]
        if full <= 0:
            return 2, [f"{path}: advance(中)={full} is not a positive full cell"]
        if expect_full is not None and full != expect_full:
            return 1, [f"{path}: full cell advance(中)={full}, expected {expect_full}"]

        lines.append(f"==> {path.name}  [text]")
        lines.append(f"    path={path}")
        lines.append(f"    UPM={upm}  full_cell(中)={full}")

        # --- not-mono ------------------------------------------------------
        if font["post"].isFixedPitch != 0:
            failures.append(
                f"post.isFixedPitch = {font['post'].isFixedPitch}: a text face must "
                "not advertise a fixed grid (it would be offered in every "
                "'monospace only' picker)"
            )
        panose = font["OS/2"].panose
        if panose.bProportion == 9:
            failures.append("PANOSE bProportion = 9 (Monospaced) on a text face")

        # --- no-nerd -------------------------------------------------------
        icons = [cp for cp in cmap if any(lo <= cp <= hi for lo, hi in NERD_PATCH_RANGES)]
        if icons:
            failures.append(
                f"{len(icons)} Nerd Font icon codepoints present (first: "
                f"{_label(min(icons))}): the text profile takes the un-patched "
                "Latin donor, so an icon here means the wrong source"
            )

        # --- cjk-full ------------------------------------------------------
        for cp in CJK_FULL_REQUIRED + CJK_PUNCT_FULL:
            if cp not in cmap:
                failures.append(f"{_label(cp)}: missing (expected the full cell)")
                continue
            adv = hmtx[cmap[cp]][0]
            if adv != full:
                failures.append(f"{_label(cp)}: advance {adv}, expected {full}")

        # --- latin-cell ----------------------------------------------------
        half = None
        for ch in "Aa0":
            cp = ord(ch)
            if cp not in cmap:
                failures.append(f"{_label(cp)}: missing")
                continue
            adv = hmtx[cmap[cp]][0]
            half = adv if half is None else half
            if adv >= full:
                failures.append(
                    f"{_label(cp)}: advance {adv} is not narrower than the full "
                    f"cell {full} — the Latin side looks like CJK fallback"
                )

        # --- cjk-ambiguous -------------------------------------------------
        # Unicode calls these Ambiguous and leaves the width to the environment.
        # In prose set by a CJK face … and — are full-width marks, and the only
        # way to get there is to have taken them from the CJK donor. The rest of
        # the candidate set is checked at the strength the rule actually has:
        # whichever donor won, the result must be a whole cell.
        for cp in (0x2026, 0x2014):
            if cp not in cmap:
                failures.append(f"{_label(cp)}: missing — full-width CJK punctuation")
                continue
            adv = hmtx[cmap[cp]][0]
            if adv != full:
                failures.append(
                    f"{_label(cp)}: advance {adv}, expected the full cell {full} "
                    "(it came from the Latin donor, not the CJK one)"
                )
        if half is not None:
            for cp in CJK_PREFERRED_AMBIGUOUS:
                if cp not in cmap:
                    continue
                adv = hmtx[cmap[cp]][0]
                if adv not in (half, full):
                    failures.append(
                        f"{_label(cp)}: advance {adv} is neither the half cell "
                        f"{half} nor the full cell {full} — a donor's own "
                        "proportional punctuation leaked into the merge"
                    )

        # --- layout --------------------------------------------------------
        gsub = _features(font, "GSUB")
        gpos = _features(font, "GPOS")
        if require_layout:
            if require_gpos and "GPOS" not in font:
                failures.append(
                    "no GPOS: this family's Latin donor kerns, and a reading face "
                    "keeps that positioning — the terminal grid is allowed to "
                    "flatten it and prose is not"
                )
            if "liga" not in gsub:
                failures.append("GSUB has no 'liga'")
            if not any(tag in gsub for tag in STYLISTIC_SETS):
                failures.append(
                    "no stylistic sets left in GSUB: the coding profile folds "
                    "ss01–ss10 into 'calt' — a text product must not have been "
                    "through `fontkit expand-ligatures`"
                )

        # --- line-box ------------------------------------------------------
        os2 = font["OS/2"]
        if not os2.fsSelection & 0x80:
            failures.append("USE_TYPO_METRICS (fsSelection bit 7) is not set")
        if os2.sTypoLineGap <= 0:
            failures.append(
                f"OS/2.sTypoLineGap = {os2.sTypoLineGap}: a terminal wants the line "
                "box tight and sets this to 0; prose wants leading"
            )
        if os2.sTypoAscender <= 0 or os2.sTypoDescender >= 0:
            failures.append(
                f"implausible typo metrics: ascender={os2.sTypoAscender} "
                f"descender={os2.sTypoDescender}"
            )
        line = os2.sTypoAscender - os2.sTypoDescender + os2.sTypoLineGap
        lines.append(
            f"    line box: typo {os2.sTypoAscender}/{os2.sTypoDescender}"
            f"+{os2.sTypoLineGap} = {line / upm:.3f} em"
        )
        lines.append(f"    GSUB: {sorted(gsub)}")
        lines.append(f"    GPOS: {sorted(gpos)}")

        if failures:
            lines.append(f"    FAIL: {len(failures)} check(s)")
            lines += [f"      {message}" for message in failures[:80]]
            if len(failures) > 80:
                lines.append(f"      … and {len(failures) - 80} more")
            return 1, lines

        lines.append("    OK")
        return 0, lines
    finally:
        font.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("fonts", nargs="+", type=Path, help="TTF/OTF file(s) to check")
    ap.add_argument(
        "--expect-full",
        type=int,
        default=None,
        help="hard pin for the CJK cell, e.g. 1000 — fails fast if advance(中) differs",
    )
    ap.add_argument(
        "--no-layout",
        action="store_true",
        help="skip the liga / stylistic-set checks (donors without them)",
    )
    ap.add_argument(
        "--require-gpos",
        action="store_true",
        help="fail if GPOS is absent — for families whose Latin donor kerns",
    )
    args = ap.parse_args(argv)

    worst = 0
    for font_path in args.fonts:
        if not font_path.is_file():
            print(f"error: not a file: {font_path}", file=sys.stderr)
            return 2
        rc, report = verify_font(
            font_path,
            expect_full=args.expect_full,
            require_layout=not args.no_layout,
            require_gpos=args.require_gpos,
        )
        print("\n".join(report))
        worst = max(worst, rc)

    if worst:
        print("\ntext profile verification FAILED", file=sys.stderr)
    else:
        print("\ntext profile verification passed")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
