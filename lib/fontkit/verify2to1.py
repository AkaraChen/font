#!/usr/bin/env python3
"""Strict 2:1 dual-width metric verification.

Designed for coding monos on a half-cell Latin / full-cell CJK grid.

  half_unit = advance('A')     # 500 (serif), 550 (sans), 600 (typewriter), …
  full_unit = 2 * half_unit

Exit codes:
  0  all checks passed
  1  one or more advance-width / flag failures
  2  usage / I/O / missing reference glyph

Always checked:
  MUST half   ASCII printable, box drawing + block elements, halfwidth kana
  MUST full   fullwidth forms, CJK punctuation, fixed CJK samples
  mono flags  post.isFixedPitch == 1 and PANOSE bProportion == 9, so hosts list
              the font as monospaced (FontForge clears isFixedPitch on
              dual-width fonts during the Nerd patch)

Optional gates:
  --check-nerd  present Nerd/PUA icons must be half_unit (after font-patcher
                --single-width-glyphs; NOT --mono)
  --check-eaw   every mapped advance must match East_Asian_Width — N/Na/H →
                half, W/F → full. Ambiguous (A) is deliberately not gated: it
                is genuinely user-configurable in a terminal.

Profiles
--------
serif and the merged families ran forked copies of this gate and the two
drifted. Both sets of checks survive here, selected by --profile:

  compact (default)  what rounded / sans / typewriter gate on. ASCII must be
                     *present*, OS/2.xAvgCharWidth must equal the half cell,
                     and --check-nerd sweeps the whole PUA out of the cmap.
  dense              what serif / handwriting / casual gate on. Samples CJK
                     Unified Ideographs far more densely, gates four more
                     bracket punctuation marks, and --check-nerd walks the
                     published Nerd Font ranges instead of all of PUA.

Neither is a superset of the other, so neither could simply be dropped:
compact's xAvgCharWidth check does not hold for serif's products, and dense's
extra punctuation would gate glyphs the merged families never promised.

Run as:
  python3 -m fontkit.verify2to1 [--profile dense] [--check-nerd] [--check-eaw] FONT.ttf …
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, replace as _replace_dataclass
from pathlib import Path
from typing import Iterable

try:
    from fontTools.ttLib import TTFont
except ImportError as exc:  # pragma: no cover
    print("error: fontTools is required (pip install fonttools)", file=sys.stderr)
    raise SystemExit(2) from exc


# --- character sets ---------------------------------------------------------

def _range(lo: int, hi: int) -> list[int]:
    return list(range(lo, hi + 1))


# ASCII printable space..~
ASCII_PRINTABLE = _range(0x20, 0x7E)

# Box Drawing + Block Elements (terminal grid; dual-width monos = half cell)
BOX_AND_BLOCK = _range(0x2500, 0x259F)

# Halfwidth Katakana / punctuation (FF61–FF9F)
HALFWIDTH_KANA = _range(0xFF61, 0xFF9F)

# Fullwidth ASCII-ish forms (FF01–FF5E) + fullwidth yen/won/etc through FF60
FULLWIDTH_FORMS = _range(0xFF01, 0xFF60)

# Common CJK / ideographic punctuation that must be full cell.
CJK_PUNCT = [
    0x3000,  # ideographic space
    0x3001,  # 、
    0x3002,  # 。
    0x3008,
    0x3009,
    0x300A,
    0x300B,
    0x300C,
    0x300D,
    0x300E,
    0x300F,
    0x3010,
    0x3011,
    0xFF08,  # （
    0xFF09,  # ）
    0xFF0C,  # ，
    0xFF0E,  # ．
    0xFF1A,  # ：
    0xFF1B,  # ；
    0xFF1F,  # ？
    0xFF01,  # ！
]

# 〔〕〖〗 — dense profile only. Sarasa ships them full-cell; the merged
# families inherit whatever their Latin source had, so gating these everywhere
# would be a new product requirement rather than a refactor.
CJK_PUNCT_DENSE_EXTRA = [0x3014, 0x3015, 0x3016, 0x3017]

# Fixed everyday CJK samples (must exist and be full).
CJK_FIXED = [ord(c) for c in "中文测试字体等宽对齐汉字编程注释字符串"]
CJK_FIXED_COMPACT_EXTRA = [ord(c) for c in "荷塘月色"]

# Systematic CJK Unified Ideographs samples (BMP block), dense profile only.
CJK_SAMPLE_STARTS = [
    0x4E00, 0x4E8C, 0x4E09, 0x56DB, 0x4E94, 0x516D, 0x4E03, 0x516B,
    0x4E5D, 0x5341, 0x767E, 0x5343, 0x4E07, 0x4EAC, 0x6D77, 0x897F,
    0x5317, 0x4E0A, 0x4E0B, 0x5DE6, 0x53F3, 0x5927, 0x5C0F, 0x4EBA,
    0x5DE5, 0x7A0B, 0x5E8F, 0x6E90, 0x7801, 0x53D8, 0x91CF,
]

# Published Nerd Font Private Use ranges — what the dense profile scans.
# See https://github.com/ryanoasis/nerd-fonts/wiki/Glyph-Sets-and-Code-Points
NERD_RANGES = [
    (0xE0A0, 0xE0A2),  # Powerline extra
    (0xE0B0, 0xE0B3),  # Powerline
    (0xE0B4, 0xE0C8),  # Powerline extra
    (0xE0CA, 0xE0CA),
    (0xE0CC, 0xE0D4),
    (0xE200, 0xE2A9),  # Font Awesome Extension (approx)
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

# BMP PUA + SPUA-A/B — what the compact profile scans. Broader than
# NERD_RANGES: it also catches icons the patcher placed outside the published
# ranges, at the cost of gating any other PUA glyph the base font shipped.
PUA_RANGES = [
    (0xE000, 0xF8FF),
    (0xF0000, 0xFFFFD),
    (0x100000, 0x10FFFD),
]

# Documented EAW exceptions: codepoints whose advance may disagree with the
# Unicode width table without it being a bug.
EAW_EXCEPTIONS = {
    0x2E3A,  # ⸺ two-em dash: deliberately 2 em wide
    0x2E3B,  # ⸻ three-em dash: deliberately 3 em wide
    0xFE19,  # ︙ vertical presentation form, shares its outline with U+22EE
    0xFE30,  # ︰ vertical presentation form, shares its outline with U+2025
}


@dataclass(frozen=True)
class Profile:
    name: str
    cjk_punct: tuple[int, ...]
    cjk_fixed: tuple[int, ...]
    dense_cjk_sample: bool
    require_ascii: bool
    check_avg_width: bool
    nerd_ranges: tuple[tuple[int, int], ...]


PROFILES = {
    "compact": Profile(
        name="compact",
        cjk_punct=tuple(CJK_PUNCT),
        cjk_fixed=tuple(CJK_FIXED + CJK_FIXED_COMPACT_EXTRA),
        dense_cjk_sample=False,
        require_ascii=True,
        check_avg_width=True,
        nerd_ranges=tuple(PUA_RANGES),
    ),
    "dense": Profile(
        name="dense",
        cjk_punct=tuple(CJK_PUNCT + CJK_PUNCT_DENSE_EXTRA),
        cjk_fixed=tuple(CJK_FIXED),
        dense_cjk_sample=True,
        require_ascii=False,
        check_avg_width=False,
        nerd_ranges=tuple(NERD_RANGES),
    ),
}


def _cp_label(cp: int) -> str:
    ch = chr(cp) if cp <= 0x10FFFF else "?"
    if ch.isprintable() and not ch.isspace():
        return f"U+{cp:04X} '{ch}'"
    return f"U+{cp:04X}"


def _advance(cmap: dict, hmtx, cp: int) -> int | None:
    name = cmap.get(cp)
    if name is None:
        return None
    return hmtx[name][0]


def _eaw(cp: int) -> str | None:
    try:
        return unicodedata.east_asian_width(chr(cp))
    except (ValueError, TypeError):
        return None


def _iter_present(codepoints: Iterable[int], cmap: dict) -> list[int]:
    return [cp for cp in codepoints if cp in cmap]


def _dedupe(codepoints: Iterable[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for cp in codepoints:
        if cp not in seen:
            seen.add(cp)
            out.append(cp)
    return out


def collect_half_required() -> list[int]:
    return ASCII_PRINTABLE + BOX_AND_BLOCK + HALFWIDTH_KANA


def collect_full_required(profile: Profile) -> list[int]:
    out = list(FULLWIDTH_FORMS) + list(profile.cjk_punct) + list(profile.cjk_fixed)
    if profile.dense_cjk_sample:
        out.extend(CJK_SAMPLE_STARTS)
        # denser sample every 0x80 in CJK Unified Ideographs
        out.extend(range(0x4E00, 0x9FFF, 0x80))
    return _dedupe(out)


def collect_nerd_codepoints(cmap: dict, profile: Profile) -> list[int]:
    return sorted(
        cp for cp in cmap if any(lo <= cp <= hi for lo, hi in profile.nerd_ranges)
    )


def verify_font(
    path: Path,
    *,
    profile: Profile,
    epsilon: int = 0,
    expect_half: int | None = None,
    check_nerd: bool = False,
    check_eaw: bool = False,
    require_cjk: bool = True,
) -> tuple[int, list[str]]:
    """Return (exit_code, report_lines). 0 pass · 1 metric fail · 2 usage/I/O."""
    lines: list[str] = []
    failures: list[tuple[str, int, int, int]] = []  # set, cp, expected, actual

    font = TTFont(path)
    try:
        cmap = font.getBestCmap() or {}
        hmtx = font["hmtx"]
        upm = font["head"].unitsPerEm

        half = _advance(cmap, hmtx, ord("A"))
        if half is None:
            return 2, [f"{path}: missing reference glyph 'A'"]
        if half <= 0:
            return 2, [f"{path}: advance('A')={half} is not a positive half-cell"]
        if expect_half is not None and half != expect_half:
            return 1, [
                f"{path}: half_unit advance('A')={half}, expected {expect_half}"
            ]

        full = half * 2
        lines.append(f"==> {path.name}  [{profile.name}]")
        lines.append(f"    path={path}")
        lines.append(f"    UPM={upm}  half_unit(A)={half}  full_unit={full}")

        # half set
        half_cps = _iter_present(collect_half_required(), cmap)
        if profile.require_ascii:
            for cp in ASCII_PRINTABLE:
                if cp not in cmap:
                    failures.append(("half-missing", cp, half, -1))
        for cp in half_cps:
            adv = _advance(cmap, hmtx, cp)
            if adv is not None and abs(adv - half) > epsilon:
                failures.append(("half", cp, half, adv))

        # full set
        full_required = collect_full_required(profile)
        if require_cjk:
            for cp in profile.cjk_fixed:
                if cp not in cmap:
                    failures.append(("full-missing", cp, full, -1))
        for cp in _iter_present(full_required, cmap):
            adv = _advance(cmap, hmtx, cp)
            if adv is not None and abs(adv - full) > epsilon:
                failures.append(("full", cp, full, adv))

        # Monospace advertisement: hosts answer "is this mono?" from
        # post.isFixedPitch (macOS Core Text, fontconfig, Chromium/VS Code font
        # pickers) and PANOSE bProportion. FontForge clears isFixedPitch on
        # dual-width fonts during the Nerd patch, which drops the font out of
        # every "monospace only" list.
        if font["post"].isFixedPitch != 1:
            failures.append(("mono-flag", -1, 1, font["post"].isFixedPitch))
        panose = font["OS/2"].panose
        if panose.bFamilyType == 2 and panose.bProportion != 9:
            failures.append(("mono-panose", -2, 9, panose.bProportion))
        if profile.check_avg_width:
            avg = font["OS/2"].xAvgCharWidth
            if avg != half:
                failures.append(("avg-width", -3, half, avg))

        # East_Asian_Width gate: a terminal sizes a cell from Unicode's EAW
        # table, never from the font. EAW N/Na/H always get 1 cell and W/F
        # always get 2, so any font advance that disagrees is ink in the wrong
        # number of cells — the '⏵ looks fullwidth' class of bug.
        eaw_violations = 0
        if check_eaw:
            for cp, gname in cmap.items():
                if cp in EAW_EXCEPTIONS:
                    continue
                adv = hmtx[gname][0]
                if adv == 0:
                    continue
                w = _eaw(cp)
                if w in ("N", "Na", "H") and abs(adv - half) > epsilon:
                    failures.append(("eaw-half", cp, half, adv))
                    eaw_violations += 1
                elif w in ("W", "F") and abs(adv - full) > epsilon:
                    failures.append(("eaw-full", cp, full, adv))
                    eaw_violations += 1

        nerd_cps: list[int] = []
        if check_nerd:
            nerd_cps = collect_nerd_codepoints(cmap, profile)
            if not nerd_cps:
                lines.append("    nerd: no Nerd/PUA icons found (is the font patched?)")
                failures.append(("nerd-missing", 0, half, -1))
            for cp in nerd_cps:
                adv = _advance(cmap, hmtx, cp)
                # skip zero-width placeholders
                if adv is None or adv == 0:
                    continue
                if abs(adv - half) > epsilon:
                    failures.append(("nerd-half", cp, half, adv))

        lines.append(
            f"    checked: half={len(half_cps)} full={len(full_required)}"
            + (f" nerd={len(nerd_cps)}" if check_nerd else "")
            + (f" eaw-violations={eaw_violations}" if check_eaw else "")
        )

        if failures:
            by_set: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
            for s, cp, exp, act in failures:
                by_set[s].append((cp, exp, act))
            lines.append(f"    FAIL: {len(failures)} codepoint(s)")
            for s, items in by_set.items():
                lines.append(f"    --- {s} ({len(items)}) ---")
                for cp, exp, act in items[:80]:
                    if cp == -1:
                        lines.append(
                            f"      post.isFixedPitch: expected {exp}, got {act} "
                            "(font will not be listed as monospaced)"
                        )
                    elif cp == -2:
                        lines.append(
                            f"      PANOSE bProportion: expected {exp}, got {act}"
                        )
                    elif cp == -3:
                        lines.append(
                            f"      OS/2.xAvgCharWidth: expected {exp} (half-cell), "
                            f"got {act}"
                        )
                    elif act < 0:
                        lines.append(
                            f"      {_cp_label(cp)}: missing (expected advance {exp})"
                        )
                    else:
                        lines.append(f"      {_cp_label(cp)}: expected {exp}, got {act}")
                if len(items) > 80:
                    lines.append(f"      … and {len(items) - 80} more")
            return 1, lines

        lines.append("    OK")
        return 0, lines
    finally:
        font.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Strict 2:1 dual-width mono advance-width verification"
    )
    ap.add_argument("fonts", nargs="+", type=Path, help="TTF/OTF file(s) to check")
    ap.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default="compact",
        help="which check set to run (see module docstring); default compact",
    )
    ap.add_argument(
        "--epsilon",
        type=int,
        default=0,
        help="allowed |actual-expected| (default 0 = exact)",
    )
    ap.add_argument(
        "--expect-half",
        type=int,
        default=None,
        help="hard pin for the EN cell, e.g. 550 — fails fast if advance('A') differs",
    )
    ap.add_argument(
        "--check-nerd",
        action="store_true",
        help="require present Nerd/PUA icons to be half-cell width",
    )
    ap.add_argument(
        "--check-eaw",
        action="store_true",
        help="require every advance to match the codepoint's East_Asian_Width",
    )
    ap.add_argument(
        "--cjk-sample",
        default=None,
        help="replace the profile's fixed CJK sample with these characters. "
        "The default sample is Simplified (测试宽对编释 …) and is the right "
        "question for an SC product and the wrong one for any other: IBM Plex "
        "Sans TC has no 测, and Plex Sans KR has no Han at all. Narrowing the "
        "gate to what every region happens to share would be the other way to "
        "make it pass, and it would stop gating what the SC product must draw.",
    )
    ap.add_argument(
        "--allow-missing-cjk",
        action="store_true",
        help="do not fail if the fixed CJK samples are absent",
    )
    args = ap.parse_args(argv)

    profile = PROFILES[args.profile]
    if args.cjk_sample:
        profile = _replace_dataclass(
            profile, cjk_fixed=tuple(ord(c) for c in args.cjk_sample)
        )

    worst = 0
    for font_path in args.fonts:
        if not font_path.is_file():
            print(f"error: not a file: {font_path}", file=sys.stderr)
            return 2
        rc, report = verify_font(
            font_path,
            profile=profile,
            epsilon=args.epsilon,
            expect_half=args.expect_half,
            check_nerd=args.check_nerd,
            check_eaw=args.check_eaw,
            require_cjk=not args.allow_missing_cjk,
        )
        print("\n".join(report))
        worst = max(worst, rc)

    if worst:
        print("\n2:1 verification FAILED", file=sys.stderr)
    else:
        print("\n2:1 verification passed")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
