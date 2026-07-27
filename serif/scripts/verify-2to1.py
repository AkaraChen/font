#!/usr/bin/env python3
"""Strict 2:1 dual-width mono metric verification.

Designed for Sarasa-style coding monos: half-cell Latin / full-cell CJK.

Exit codes:
  0  all checks passed
  1  one or more advance-width failures
  2  usage / I/O / missing reference glyphs

Rules (default epsilon = 0):
  half_unit = advance('A')          # typically 500 at UPM 1000
  full_unit = 2 * half_unit         # typically 1000

  MUST half:  ASCII printable, box drawing, block elements, halfwidth kana
  MUST full:  fullwidth forms, common CJK punctuation, CJK ideograph samples
  Nerd PUA:   when --check-nerd, present Nerd/PUA icons must be half_unit
              (after font-patcher --single-width-glyphs; NOT --mono)

Exceptions (documented, not checked as hard fails):
  geometric / arrows / misc symbols often mix half and full in CJK mono;
  they are out of scope for this gate unless listed above.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
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

# Box Drawing + Block Elements (terminal grid; Sarasa Mono = half cell)
BOX_AND_BLOCK = _range(0x2500, 0x259F)

# Halfwidth Katakana / punctuation (FF61–FF9F)
HALFWIDTH_KANA = _range(0xFF61, 0xFF9F)

# Fullwidth ASCII-ish forms (FF01–FF5E) + fullwidth yen/won/etc through FF60
FULLWIDTH_FORMS = _range(0xFF01, 0xFF60)

# Common CJK / ideographic punctuation that must be full cell
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
    0x3014,
    0x3015,
    0x3016,
    0x3017,
    0xFF08,  # （
    0xFF09,  # ）
    0xFF0C,  # ，
    0xFF0E,  # ．
    0xFF1A,  # ：
    0xFF1B,  # ；
    0xFF1F,  # ？
    0xFF01,  # ！
]

# Fixed everyday CJK samples (must exist and be full)
CJK_FIXED = [ord(c) for c in "中文测试字体等宽对齐汉字编程注释字符串"]

# Systematic CJK Unified Ideographs samples (BMP block)
CJK_SAMPLE_STARTS = [
    0x4E00,
    0x4E8C,
    0x4E09,
    0x56DB,
    0x4E94,
    0x516D,
    0x4E03,
    0x516B,
    0x4E5D,
    0x5341,
    0x767E,
    0x5343,
    0x4E07,
    0x4EAC,
    0x6D77,
    0x897F,
    0x5317,
    0x4E0A,
    0x4E0B,
    0x5DE6,
    0x53F3,
    0x5927,
    0x5C0F,
    0x4EBA,
    0x5DE5,
    0x7A0B,
    0x5E8F,
    0x6E90,
    0x7801,
    0x53D8,
    0x91CF,
]


# Common Nerd Font Private Use ranges (present glyphs only)
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


def _iter_present(codepoints: Iterable[int], cmap: dict) -> list[int]:
    return [cp for cp in codepoints if cp in cmap]


def collect_half_required() -> list[int]:
    return ASCII_PRINTABLE + BOX_AND_BLOCK + HALFWIDTH_KANA


def collect_full_required() -> list[int]:
    out = list(FULLWIDTH_FORMS) + list(CJK_PUNCT) + list(CJK_FIXED)
    out.extend(CJK_SAMPLE_STARTS)
    # denser sample every 0x80 in CJK Unified Ideographs
    for cp in range(0x4E00, 0x9FFF, 0x80):
        out.append(cp)
    # de-dupe, preserve order
    seen: set[int] = set()
    uniq: list[int] = []
    for cp in out:
        if cp not in seen:
            seen.add(cp)
            uniq.append(cp)
    return uniq


def collect_nerd_codepoints(cmap: dict) -> list[int]:
    found: list[int] = []
    for lo, hi in NERD_RANGES:
        for cp in range(lo, hi + 1):
            if cp in cmap:
                found.append(cp)
    return found


def verify_font(
    path: Path,
    *,
    epsilon: int = 0,
    check_nerd: bool = False,
    require_cjk: bool = True,
) -> tuple[bool, list[str]]:
    """Return (ok, report_lines)."""
    lines: list[str] = []
    failures: list[tuple[str, int, int, int]] = []  # set, cp, expected, actual

    font = TTFont(path)
    try:
        cmap = font.getBestCmap() or {}
        hmtx = font["hmtx"]
        upm = font["head"].unitsPerEm

        half = _advance(cmap, hmtx, ord("A"))
        if half is None:
            return False, [f"{path}: missing reference glyph 'A'"]
        if half <= 0:
            return False, [f"{path}: advance('A')={half} is not a positive half-cell"]

        full = half * 2
        zhong = _advance(cmap, hmtx, ord("中"))

        lines.append(f"==> {path.name}")
        lines.append(f"    path={path}")
        lines.append(f"    UPM={upm}  half_unit(A)={half}  full_unit={full}  中={zhong}")

        if zhong is None and require_cjk:
            failures.append(("ref", ord("中"), full, -1))
        elif zhong is not None and abs(zhong - full) > epsilon:
            failures.append(("ref", ord("中"), full, zhong))

        if full != half * 2:
            # defensive; half*2 is exact int
            lines.append("    CRITICAL: full_unit is not 2× half_unit")

        # half set
        half_cps = _iter_present(collect_half_required(), cmap)
        for cp in half_cps:
            adv = _advance(cmap, hmtx, cp)
            if adv is None:
                continue
            if abs(adv - half) > epsilon:
                failures.append(("half", cp, half, adv))

        # full set
        full_cps = _iter_present(collect_full_required(), cmap)
        missing_cjk_fixed = [cp for cp in CJK_FIXED if cp not in cmap]
        if require_cjk and missing_cjk_fixed:
            for cp in missing_cjk_fixed:
                failures.append(("full-missing", cp, full, -1))

        for cp in full_cps:
            adv = _advance(cmap, hmtx, cp)
            if adv is None:
                continue
            if abs(adv - full) > epsilon:
                failures.append(("full", cp, full, adv))

        nerd_cps: list[int] = []
        if check_nerd:
            nerd_cps = collect_nerd_codepoints(cmap)
            if not nerd_cps:
                lines.append("    nerd: no Nerd/PUA icons found (is the font patched?)")
                failures.append(("nerd-missing", 0, half, -1))
            for cp in nerd_cps:
                adv = _advance(cmap, hmtx, cp)
                if adv is None:
                    continue
                # skip zero-width placeholders
                if adv == 0:
                    continue
                if abs(adv - half) > epsilon:
                    failures.append(("nerd-half", cp, half, adv))

        # summary counts
        lines.append(
            f"    checked: half={len(half_cps)} full={len(full_cps)}"
            + (f" nerd={len(nerd_cps)}" if check_nerd else "")
        )

        if failures:
            # group for readable report
            by_set: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
            for s, cp, exp, act in failures:
                by_set[s].append((cp, exp, act))
            lines.append(f"    FAIL: {len(failures)} codepoint(s)")
            for s, items in by_set.items():
                lines.append(f"    --- {s} ({len(items)}) ---")
                for cp, exp, act in items[:80]:
                    if act < 0:
                        lines.append(f"      {_cp_label(cp)}: missing (expected advance {exp})")
                    else:
                        lines.append(
                            f"      {_cp_label(cp)}: expected {exp}, got {act}"
                        )
                if len(items) > 80:
                    lines.append(f"      … and {len(items) - 80} more")
            return False, lines

        lines.append("    OK")
        return True, lines
    finally:
        font.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Strict 2:1 dual-width mono advance-width verification"
    )
    ap.add_argument("fonts", nargs="+", type=Path, help="TTF/OTF file(s) to check")
    ap.add_argument(
        "--epsilon",
        type=int,
        default=0,
        help="allowed |actual-expected| (default 0 = exact)",
    )
    ap.add_argument(
        "--check-nerd",
        action="store_true",
        help="require present Nerd/PUA icons to be half-cell width",
    )
    ap.add_argument(
        "--allow-missing-cjk",
        action="store_true",
        help="do not fail if fixed CJK samples are absent",
    )
    args = ap.parse_args(argv)

    any_fail = False
    for font_path in args.fonts:
        if not font_path.is_file():
            print(f"error: not a file: {font_path}", file=sys.stderr)
            return 2
        ok, report = verify_font(
            font_path,
            epsilon=args.epsilon,
            check_nerd=args.check_nerd,
            require_cjk=not args.allow_missing_cjk,
        )
        print("\n".join(report))
        if not ok:
            any_fail = True

    if any_fail:
        print("\n2:1 verification FAILED", file=sys.stderr)
        return 1
    print("\n2:1 verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
