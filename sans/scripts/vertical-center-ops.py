#!/usr/bin/env python3
"""Vertically centre coding brackets / operators on a shared visual midline.

Why:
  After Lilex × Plex Sans SC dual-width merge, some programming punctuation
  floats high or low relative to digits and CJK body. Pure optics: advance
  and horizontal placement stay untouched; only Y is shifted.

Target midline:
  Mean of the vertical centres (yMin+yMax)/2 of reference glyphs that exist:
  H, x, 0, 中 (in that priority set — all present ones are averaged).

Whitelist (see README "Vertical centering"):
  ASCII brackets/ops, common math/comparison ops, common arrows, and their
  fullwidth counterparts when present in the cmap.

Usage:
  vertical-center-ops.py FONT.ttf [FONT.ttf ...]
  vertical-center-ops.py --dry-run FONT.ttf
  vertical-center-ops.py --report FONT.ttf   # print dy without saving
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


# ---------------------------------------------------------------------------
# Whitelist — coding punctuation / operators / arrows
# Documented in sans/README.md. Keep in sync when extending.
# ---------------------------------------------------------------------------

# ASCII brackets
_BRACKETS = (
    0x0028,  # (
    0x0029,  # )
    0x005B,  # [
    0x005D,  # ]
    0x007B,  # {
    0x007D,  # }
    0x003C,  # <
    0x003E,  # >
)

# ASCII / common coding operators (intentionally omit . , ; : ' " ` _ which
# sit on the baseline by design)
_OPERATORS = (
    0x003D,  # =
    0x002B,  # +
    0x002D,  # - hyphen-minus (coding minus)
    0x002A,  # *
    0x002F,  # /
    0x005C,  # \
    0x007C,  # |
    0x0026,  # &
    0x0025,  # %
    0x005E,  # ^
    0x007E,  # ~
    0x0021,  # !
    0x003F,  # ?
    0x0040,  # @
    0x0023,  # #
    0x0024,  # $
)

# Math / comparison (often used in code / comments)
_MATH = (
    0x00B1,  # ±
    0x00D7,  # ×
    0x00F7,  # ÷
    0x2260,  # ≠
    0x2264,  # ≤
    0x2265,  # ≥
    0x2248,  # ≈
    0x2261,  # ≡
    0x2212,  # − minus sign
    0x2217,  # ∗
    0x22C5,  # ⋅
    0x2022,  # •
)

# Common arrows (BMP)
_ARROWS = (
    0x2190,  # ←
    0x2191,  # ↑
    0x2192,  # →
    0x2193,  # ↓
    0x2194,  # ↔
    0x2195,  # ↕
    0x21D0,  # ⇐
    0x21D2,  # ⇒
    0x21D4,  # ⇔
    0x27F5,  # ⟵
    0x27F6,  # ⟶
    0x27F7,  # ⟷
)

# Fullwidth counterparts (SC / FW forms when present)
_FULLWIDTH = (
    0xFF08,  # （
    0xFF09,  # ）
    0xFF3B,  # ［
    0xFF3D,  # ］
    0xFF5B,  # ｛
    0xFF5D,  # ｝
    0xFF1C,  # ＜
    0xFF1E,  # ＞
    0xFF1D,  # ＝
    0xFF0B,  # ＋
    0xFF0D,  # －
    0xFF0A,  # ＊
    0xFF0F,  # ／
    0xFF3C,  # ＼
    0xFF5C,  # ｜
    0xFF06,  # ＆
    0xFF05,  # ％
    0xFF3E,  # ＾
    0xFF5E,  # ～
    0xFF01,  # ！
    0xFF1F,  # ？
    0xFF20,  # ＠
    0xFF03,  # ＃
    0xFF04,  # ＄
    # CJK brackets often mixed in code comments
    0x3008,  # 〈
    0x3009,  # 〉
    0x300A,  # 《
    0x300B,  # 》
    0x300C,  # 「
    0x300D,  # 」
    0x300E,  # 『
    0x300F,  # 』
    0x3010,  # 【
    0x3011,  # 】
    0x3014,  # 〔
    0x3015,  # 〕
    0x3016,  # 〖
    0x3017,  # 〗
)

WHITELIST: frozenset[int] = frozenset(
    _BRACKETS + _OPERATORS + _MATH + _ARROWS + _FULLWIDTH
)

# Reference glyphs whose optical vertical centres define the target midline.
REF_CHARS = ("H", "x", "0", "中")


def _y_bounds(glyph) -> tuple[float, float] | None:
    if glyph.numberOfContours == 0:
        return None
    try:
        return float(glyph.yMin), float(glyph.yMax)
    except AttributeError:
        return None


def _y_center(glyph) -> float | None:
    b = _y_bounds(glyph)
    if b is None:
        return None
    return (b[0] + b[1]) / 2.0


def _shift_glyph_y(glyph, glyf, dy: float) -> None:
    """Translate a simple or composite glyf glyph by dy (in place)."""
    if abs(dy) < 0.5:
        return
    if glyph.numberOfContours == 0:
        return
    if glyph.isComposite():
        for component in glyph.components:
            component.y += int(round(dy))
    else:
        coords = glyph.coordinates
        glyph.coordinates = type(coords)([(x, y + dy) for x, y in coords])
    glyph.recalcBounds(glyf)


def _target_midline(font: TTFont, glyf) -> tuple[float, list[str]]:
    cmap = font.getBestCmap() or {}
    centres: list[float] = []
    used: list[str] = []
    for ch in REF_CHARS:
        cp = ord(ch)
        gname = cmap.get(cp)
        if not gname or gname not in glyf:
            continue
        c = _y_center(glyf[gname])
        if c is None:
            continue
        centres.append(c)
        used.append(f"{ch}={c:.1f}")
    if not centres:
        # Fallback: half of OS/2 sCapHeight or typoAscender/2
        os2 = font["OS/2"]
        cap = getattr(os2, "sCapHeight", 0) or 0
        if cap > 0:
            mid = cap / 2.0
            return mid, [f"sCapHeight/2={mid:.1f}"]
        mid = float(os2.sTypoAscender) / 2.0
        return mid, [f"sTypoAscender/2={mid:.1f}"]
    mid = sum(centres) / len(centres)
    return mid, used


def center_font(
    path: Path,
    *,
    dry_run: bool = False,
    min_dy: float = 1.0,
) -> list[str]:
    """Y-centre whitelisted glyphs. Advance / LSB unchanged."""
    lines: list[str] = []
    font = TTFont(path)
    try:
        cmap = font.getBestCmap() or {}
        glyf = font["glyf"]
        hmtx = font["hmtx"].metrics
        # Touch glyph order / load tables before mutation
        _ = font.getGlyphOrder()

        # Drop broken vmtx if present (same hygiene as narrow-symbol-widths)
        if "vmtx" in font:
            try:
                _ = font["vmtx"].metrics
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

        mid, ref_desc = _target_midline(font, glyf)
        lines.append(
            f"{path.name}: target midline={mid:.1f} "
            f"(refs: {', '.join(ref_desc)})"
        )

        # Collect unique glyph names from whitelist codepoints that exist
        targets: dict[str, list[int]] = {}
        for cp in sorted(WHITELIST):
            gname = cmap.get(cp)
            if not gname:
                continue
            targets.setdefault(gname, []).append(cp)

        shifted = 0
        skipped_empty = 0
        skipped_small = 0
        # Snapshot advances so we can assert invariance
        adv_before = {g: hmtx[g][0] for g in targets}

        for gname, cps in sorted(targets.items()):
            glyph = glyf[gname]
            yc = _y_center(glyph)
            if yc is None:
                skipped_empty += 1
                continue
            dy = mid - yc
            if abs(dy) < min_dy:
                skipped_small += 1
                continue
            _shift_glyph_y(glyph, glyf, dy)
            # Keep advance & LSB; y-shift must not change LSB
            adv, lsb = hmtx[gname]
            hmtx[gname] = (adv, lsb)
            shifted += 1
            sample = " ".join(chr(c) if c < 0x10000 else f"U+{c:04X}" for c in cps[:4])
            lines.append(f"  {gname} ({sample}): dy={dy:+.1f}  y-centre {yc:.1f}→{mid:.1f}")

        # Advance invariance check
        bad = [
            g
            for g, a0 in adv_before.items()
            if hmtx[g][0] != a0
        ]
        if bad:
            raise SystemExit(
                f"{path.name}: advance changed for {len(bad)} glyph(s); aborting"
            )

        lines.append(
            f"{path.name}: shifted={shifted} "
            f"skipped_empty={skipped_empty} skipped_|dy|<{min_dy}={skipped_small} "
            f"whitelist_cps_present={sum(len(v) for v in targets.values())}"
        )
        if dry_run:
            lines.append(f"{path.name}: dry-run (not saved)")
        else:
            font.save(path)
            lines.append(f"{path.name}: saved")
        return lines
    finally:
        font.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="report shifts without writing the font",
    )
    ap.add_argument(
        "--min-dy",
        type=float,
        default=1.0,
        help="ignore |dy| below this (font units; default 1)",
    )
    ap.add_argument(
        "--list-whitelist",
        action="store_true",
        help="print whitelist codepoints and exit",
    )
    args = ap.parse_args(argv)

    if args.list_whitelist:
        for cp in sorted(WHITELIST):
            ch = chr(cp) if cp < 0x10000 else ""
            print(f"U+{cp:04X}  {ch}")
        return 0

    any_err = False
    for path in args.fonts:
        if not path.is_file():
            print(f"error: not a file: {path}", file=sys.stderr)
            any_err = True
            continue
        for line in center_font(path, dry_run=args.dry_run, min_dy=args.min_dy):
            print(line)
    return 1 if any_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
