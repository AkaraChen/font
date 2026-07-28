#!/usr/bin/env python3
"""Strict 2:1 dual-width metric verification for LilexSansSC Dual / NFM.

half_unit = advance('A')   # default product: 550
full_unit = 2 * half_unit  # default product: 1100

Exit: 0 pass · 1 metric fail · 2 usage / I/O
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


def _range(lo: int, hi: int) -> list[int]:
    return list(range(lo, hi + 1))


ASCII_PRINTABLE = _range(0x20, 0x7E)
BOX_AND_BLOCK = _range(0x2500, 0x259F)
HALFWIDTH_KANA = _range(0xFF61, 0xFF9F)
FULLWIDTH_FORMS = _range(0xFF01, 0xFF60)
CJK_PUNCT = [
    0x3000,
    0x3001,
    0x3002,
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
    0xFF08,
    0xFF09,
    0xFF0C,
    0xFF0E,
    0xFF1A,
    0xFF1B,
    0xFF1F,
    0xFF01,
]
CJK_FIXED = [ord(c) for c in "中文测试字体等宽对齐汉字编程注释字符串荷塘月色"]

# BMP PUA + SPUA-A (Material Design Icons etc.) — Nerd complete set
PUA_RANGES = (
    (0xE000, 0xF8FF),
    (0xF0000, 0xFFFFD),
    (0x100000, 0x10FFFD),
)


def advance(font: TTFont, cp: int) -> int | None:
    cm = font.getBestCmap() or {}
    g = cm.get(cp)
    if g is None:
        return None
    return font["hmtx"].metrics[g][0]


def check_set(
    font: TTFont,
    cps: list[int],
    expected: int,
    label: str,
    *,
    require_present: bool,
    epsilon: int,
    missing: list[str],
    bad: list[str],
) -> None:
    for cp in cps:
        w = advance(font, cp)
        if w is None:
            if require_present:
                missing.append(f"U+{cp:04X} ({label})")
            continue
        if abs(w - expected) > epsilon:
            ch = chr(cp) if cp < 0x110000 else "?"
            bad.append(f"U+{cp:04X} '{ch}' {label}: advance={w} expected={expected}")


def check_nerd(font: TTFont, half: int, epsilon: int, bad: list[str]) -> int:
    """Require present Nerd/PUA icons at half-cell. Returns count scanned."""
    cmap = font.getBestCmap() or {}
    nerd_cps = [
        cp
        for cp in cmap
        if any(a <= cp <= b for a, b in PUA_RANGES)
    ]
    if not nerd_cps:
        bad.append("nerd: no Nerd/PUA icons found (is the font patched?)")
        return 0
    for cp in nerd_cps:
        w = advance(font, cp)
        if w is None or w == 0:
            continue
        if abs(w - half) > epsilon:
            bad.append(
                f"U+{cp:04X} nerd/PUA: advance={w} expected {half} (half-cell icon)"
            )
    return len(nerd_cps)


def verify_one(
    path: Path,
    epsilon: int,
    expect_half: int | None,
    *,
    check_nerd_flag: bool,
) -> int:
    font = TTFont(path)
    half = advance(font, ord("A"))
    if half is None:
        print(f"{path}: missing 'A'", file=sys.stderr)
        return 2
    if expect_half is not None and half != expect_half:
        print(
            f"{path}: half_unit advance('A')={half}, expected {expect_half}",
            file=sys.stderr,
        )
        return 1
    full = 2 * half
    print(f"{path.name}: half={half} full={full}")

    missing: list[str] = []
    bad: list[str] = []

    check_set(
        font,
        ASCII_PRINTABLE,
        half,
        "ascii",
        require_present=True,
        epsilon=epsilon,
        missing=missing,
        bad=bad,
    )
    check_set(
        font,
        BOX_AND_BLOCK,
        half,
        "box/block",
        require_present=False,
        epsilon=epsilon,
        missing=missing,
        bad=bad,
    )
    check_set(
        font,
        HALFWIDTH_KANA,
        half,
        "hw-kana",
        require_present=False,
        epsilon=epsilon,
        missing=missing,
        bad=bad,
    )
    check_set(
        font,
        FULLWIDTH_FORMS,
        full,
        "fullwidth",
        require_present=False,
        epsilon=epsilon,
        missing=missing,
        bad=bad,
    )
    check_set(
        font,
        CJK_PUNCT,
        full,
        "cjk-punct",
        require_present=False,
        epsilon=epsilon,
        missing=missing,
        bad=bad,
    )
    check_set(
        font,
        CJK_FIXED,
        full,
        "cjk-sample",
        require_present=True,
        epsilon=epsilon,
        missing=missing,
        bad=bad,
    )

    # Hosts answer "is this mono?" from post.isFixedPitch + PANOSE proportion.
    # Dual-width 2:1 still advertises fixed pitch (matches serif/pixel/handwriting).
    # FontForge/Nerd patcher often clears isFixedPitch — fix-terminal-metrics restores it.
    is_fp = font["post"].isFixedPitch
    print(f"  post.isFixedPitch={is_fp} (expected 1)")
    if is_fp != 1:
        bad.append(f"post.isFixedPitch={is_fp} expected 1 (font will not list as mono)")
    panose = font["OS/2"].panose
    if panose.bFamilyType == 2 and panose.bProportion != 9:
        bad.append(
            f"PANOSE bProportion={panose.bProportion} expected 9 (Monospaced)"
        )
    else:
        print(f"  PANOSE bProportion={panose.bProportion} (Monospaced)")
    avg = font["OS/2"].xAvgCharWidth
    print(f"  OS/2.xAvgCharWidth={avg} (expected {half})")
    if avg != half:
        bad.append(f"OS/2.xAvgCharWidth={avg} expected {half} (half-cell)")

    if check_nerd_flag:
        n = check_nerd(font, half, epsilon, bad)
        print(f"  nerd/PUA icons scanned={n}")

    font.close()

    ok = True
    if missing:
        ok = False
        print(f"  MISSING ({len(missing)}):", file=sys.stderr)
        for m in missing[:40]:
            print(f"    {m}", file=sys.stderr)
    if bad:
        ok = False
        print(f"  BAD ADVANCES / FLAGS ({len(bad)}):", file=sys.stderr)
        for b in bad[:60]:
            print(f"    {b}", file=sys.stderr)
        if len(bad) > 60:
            print(f"    ... +{len(bad) - 60} more", file=sys.stderr)
    if ok:
        print("  OK")
        return 0
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument("--epsilon", type=int, default=0)
    ap.add_argument(
        "--expect-half",
        type=int,
        default=None,
        help="Optional hard pin for EN cell (e.g. 550)",
    )
    ap.add_argument(
        "--check-nerd",
        action="store_true",
        help="Require Nerd/PUA icons present at half-cell advance",
    )
    args = ap.parse_args()

    worst = 0
    for f in args.fonts:
        if not f.exists():
            print(f"missing file: {f}", file=sys.stderr)
            return 2
        rc = verify_one(
            f, args.epsilon, args.expect_half, check_nerd_flag=args.check_nerd
        )
        worst = max(worst, rc)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
