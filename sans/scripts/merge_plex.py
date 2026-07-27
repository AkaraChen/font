#!/usr/bin/env python3
"""Merge IBM Plex Mono + IBM Plex Sans SC into a dual-width coding face.

Default product metrics: EN 550 / CJK 1100 (strict 2:1).

Character policy
----------------
- Plex Mono (X-scaled to EN_ADV): Latin, digits, programming symbols, half-width
  punctuation, Greek / Cyrillic — anything Mono already maps.
- Plex Sans SC (outline unchanged; advance expanded & centred to CJK_ADV):
  CJK ideographs, CJK punctuation, fullwidth forms, and any codepoint Mono lacks.

Family naming follows the serif recipe (source tokens concatenated + product
suffix), default: "PlexMonoSansSC Dual" = Plex Mono + Plex Sans SC + dual-width.
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates


def is_cjk_side(cp: int) -> bool:
    ranges = (
        (0x2E80, 0x2EFF),  # CJK Radicals Supplement
        (0x2F00, 0x2FDF),  # Kangxi Radicals
        (0x3000, 0x303F),  # CJK Symbols and Punctuation
        (0x3040, 0x30FF),  # Hiragana + Katakana
        (0x3100, 0x312F),  # Bopomofo
        (0x3190, 0x319F),  # Kanbun
        (0x31A0, 0x31BF),  # Bopomofo Extended
        (0x31C0, 0x31EF),  # CJK Strokes
        (0x31F0, 0x31FF),  # Katakana Phonetic Extensions
        (0x3200, 0x32FF),  # Enclosed CJK Letters and Months
        (0x3300, 0x33FF),  # CJK Compatibility
        (0x3400, 0x4DBF),  # CJK Ext A
        (0x4E00, 0x9FFF),  # CJK Unified
        (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
        (0xFE30, 0xFE4F),  # CJK Compatibility Forms
        (0xFF00, 0xFFEF),  # Halfwidth and Fullwidth Forms
        (0x20000, 0x2A6DF),
        (0x2A700, 0x2B73F),
        (0x2B740, 0x2B81F),
        (0x2B820, 0x2CEAF),
        (0x2F800, 0x2FA1F),
    )
    return any(a <= cp <= b for a, b in ranges)


def scale_glyph_x(glyph, glyf_table, scale: float) -> None:
    if glyph.numberOfContours == 0:
        return
    if glyph.isComposite():
        for component in glyph.components:
            component.x = int(round(component.x * scale))
            if hasattr(component, "transform"):
                xx, xy, yx, yy = component.transform
                component.transform = (xx * scale, xy, yx * scale, yy)
        glyph.recalcBounds(glyf_table)
        return

    coords = glyph.coordinates
    if not coords:
        return
    glyph.coordinates = GlyphCoordinates(
        [(int(round(x * scale)), y) for x, y in coords]
    )
    glyph.recalcBounds(glyf_table)


def scale_mono_font(font: TTFont, scale: float, target_adv: int) -> None:
    glyf = font["glyf"]
    hmtx = font["hmtx"].metrics

    for tag in ("hdmx", "LTSH", "VDMX", "kern"):
        if tag in font:
            del font[tag]

    for name in font.getGlyphOrder():
        g = glyf[name]
        old_w, old_lsb = hmtx[name]
        scale_glyph_x(g, glyf, scale)
        new_lsb = int(round(old_lsb * scale))
        hmtx[name] = (target_adv, new_lsb)

    if "maxp" in font:
        font["maxp"].recalc(font)


def center_advance(old_adv: int, old_lsb: int, new_adv: int) -> int:
    pad = new_adv - old_adv
    return old_lsb + pad // 2


def ensure_glyph_slot(dst: TTFont, name: str) -> None:
    order = dst.getGlyphOrder()
    if name not in order:
        order.append(name)
        dst.setGlyphOrder(order)
        dst["maxp"].numGlyphs = len(order)


def copy_glyph_deep(
    src: TTFont, dst: TTFont, name: str, rename: dict[str, str]
) -> str:
    if name in rename:
        return rename[name]

    dest_name = name
    if name in dst["glyf"] and name not in (".notdef",):
        dest_name = f"sc.{name}"
        n = 1
        while dest_name in dst["glyf"]:
            dest_name = f"sc.{name}.{n}"
            n += 1

    rename[name] = dest_name
    src_glyf = src["glyf"]
    dst_glyf = dst["glyf"]
    g = copy.deepcopy(src_glyf[name])

    if g.isComposite():
        for component in g.components:
            comp_dst = copy_glyph_deep(src, dst, component.glyphName, rename)
            component.glyphName = comp_dst

    ensure_glyph_slot(dst, dest_name)
    dst_glyf[dest_name] = g

    w, lsb = src["hmtx"].metrics[name]
    dst["hmtx"].metrics[dest_name] = (w, lsb)
    return dest_name


def set_cjk_metrics(dst: TTFont, glyph_name: str, new_adv: int) -> None:
    w, lsb = dst["hmtx"].metrics[glyph_name]
    new_lsb = center_advance(w, lsb, new_adv)
    dst["hmtx"].metrics[glyph_name] = (new_adv, new_lsb)


def rebuild_cmap(dst: TTFont, mapping: dict[int, str]) -> None:
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

    table = newTable("cmap")
    table.tableVersion = 0
    tables = []

    bmp = {cp: g for cp, g in mapping.items() if cp <= 0xFFFF}
    full = dict(mapping)

    for platformID, platEncID, cmap_dict, fmt in (
        (3, 1, bmp, 4),
        (3, 10, full, 12),
        (0, 3, bmp, 4),
        (0, 4, full, 12),
    ):
        sub = CmapSubtable.newSubtable(fmt)
        sub.platformID = platformID
        sub.platEncID = platEncID
        sub.language = 0
        sub.cmap = cmap_dict
        tables.append(sub)

    table.tables = tables
    dst["cmap"] = table


def rename_family(
    font: TTFont,
    family: str,
    subfamily: str,
    ps_base: str,
    en_adv: int,
    cjk_adv: int,
) -> None:
    name = font["name"]
    full = f"{family} {subfamily}" if subfamily != "Regular" else family
    ps = f"{ps_base}-{subfamily.replace(' ', '')}"

    keep_ids = {0, 5, 7, 8, 9, 10, 11, 13, 14}
    records = [r for r in name.names if r.nameID in keep_ids]
    font["name"].names = records

    def add(nid: int, string: str) -> None:
        name.setName(string, nid, 3, 1, 0x409)
        try:
            name.setName(string, nid, 1, 0, 0)
        except Exception:
            pass

    add(1, family)
    add(2, subfamily)
    add(3, f"{family}: {subfamily}")
    add(4, full)
    add(6, ps)
    add(16, family)
    add(17, subfamily)
    add(
        5,
        f"1.000;KIT;{family} merge (Plex Mono + Plex Sans SC; EN {en_adv} / CJK {cjk_adv})",
    )


def unify_metrics(
    font: TTFont,
    *,
    en_adv: int,
    hhea_ascent: int,
    hhea_descent: int,
    hhea_line_gap: int,
    os2_typo_asc: int,
    os2_typo_desc: int,
    os2_typo_gap: int,
    os2_win_asc: int,
    os2_win_desc: int,
) -> None:
    hhea = font["hhea"]
    os2 = font["OS/2"]
    hhea.ascent = hhea_ascent
    hhea.descent = hhea_descent
    hhea.lineGap = hhea_line_gap
    os2.sTypoAscender = os2_typo_asc
    os2.sTypoDescender = os2_typo_desc
    os2.sTypoLineGap = os2_typo_gap
    os2.usWinAscent = os2_win_asc
    os2.usWinDescent = os2_win_desc
    os2.fsSelection |= 0x80  # USE_TYPO_METRICS
    # Dual-width: not classic single-cell fixed pitch
    font["post"].isFixedPitch = 0
    try:
        os2.panose.bProportion = 9  # monospaced (host hints)
    except Exception:
        pass
    try:
        os2.xAvgCharWidth = en_adv
    except Exception:
        pass


def merge_pair(
    mono_path: Path,
    sc_path: Path,
    out_path: Path,
    subfamily: str,
    *,
    en_adv: int,
    cjk_adv: int,
    mono_src_adv: int,
    family: str,
    family_ps: str,
    metrics: dict,
) -> dict[str, int]:
    print(f"Loading {mono_path.name} + {sc_path.name} ...")
    mono = TTFont(mono_path, recalcBBoxes=True, recalcTimestamp=False)
    sc = TTFont(sc_path, recalcBBoxes=True, recalcTimestamp=False)

    scale = en_adv / mono_src_adv
    print(f"  Scaling Mono glyphs X * {scale:.6f} -> advance {en_adv}")
    scale_mono_font(mono, scale, en_adv)

    mono_cmap = mono.getBestCmap() or {}
    sc_cmap = sc.getBestCmap() or {}

    to_import: dict[int, str] = {}
    for cp, gname in sc_cmap.items():
        if is_cjk_side(cp) or cp not in mono_cmap:
            to_import[cp] = gname

    print(f"  Importing {len(to_import)} codepoints from SC ...")

    rename: dict[str, str] = {}
    final_map: dict[int, str] = dict(mono_cmap)

    for i, (cp, src_name) in enumerate(sorted(to_import.items())):
        if i and i % 5000 == 0:
            print(f"    ... {i}/{len(to_import)}")
        dest_name = copy_glyph_deep(sc, mono, src_name, rename)
        set_cjk_metrics(mono, dest_name, cjk_adv)
        final_map[cp] = dest_name

    for ch in "中文荷塘月色":
        if ord(ch) not in final_map:
            raise SystemExit(f"missing required CJK sample glyph: {ch}")

    rebuild_cmap(mono, final_map)
    rename_family(mono, family, subfamily, family_ps, en_adv, cjk_adv)
    unify_metrics(mono, en_adv=en_adv, **metrics)

    glyf = mono["glyf"]
    for gname in mono.getGlyphOrder():
        g = glyf[gname]
        if g.numberOfContours != 0:
            try:
                g.recalcBounds(glyf)
            except Exception:
                pass
    mono["maxp"].recalc(mono)
    mono["hhea"].advanceWidthMax = max(m[0] for m in mono["hmtx"].metrics.values())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    mono.save(out_path)
    mono.close()
    sc.close()

    v = TTFont(out_path)
    cm = v.getBestCmap()
    hmtx = v["hmtx"]
    checks: dict[str, int] = {}
    for ch in list("aAi0中文荷") + [" "]:
        g = cm[ord(ch)]
        checks[ch] = hmtx[g][0]
    v.close()
    print(f"  Saved {out_path}  advances={checks}")
    return checks


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mono-regular", type=Path, required=True)
    p.add_argument("--mono-bold", type=Path, required=True)
    p.add_argument("--sc-regular", type=Path, required=True)
    p.add_argument("--sc-bold", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--en-adv", type=int, default=550)
    p.add_argument("--cjk-adv", type=int, default=1100)
    p.add_argument("--mono-src-adv", type=int, default=600)
    p.add_argument("--family", default="PlexMonoSansSC Dual")
    p.add_argument("--family-ps", default="PlexMonoSansSCDual")
    p.add_argument("--hhea-ascent", type=int, default=1025)
    p.add_argument("--hhea-descent", type=int, default=-275)
    p.add_argument("--hhea-line-gap", type=int, default=0)
    p.add_argument("--os2-typo-ascender", type=int, default=880)
    p.add_argument("--os2-typo-descender", type=int, default=-220)
    p.add_argument("--os2-typo-line-gap", type=int, default=0)
    p.add_argument("--os2-win-ascent", type=int, default=1060)
    p.add_argument("--os2-win-descent", type=int, default=300)
    args = p.parse_args()

    if args.cjk_adv != 2 * args.en_adv:
        print(
            f"warning: CJK_ADV ({args.cjk_adv}) != 2 * EN_ADV ({args.en_adv})",
            file=sys.stderr,
        )

    metrics = dict(
        hhea_ascent=args.hhea_ascent,
        hhea_descent=args.hhea_descent,
        hhea_line_gap=args.hhea_line_gap,
        os2_typo_asc=args.os2_typo_ascender,
        os2_typo_desc=args.os2_typo_descender,
        os2_typo_gap=args.os2_typo_line_gap,
        os2_win_asc=args.os2_win_ascent,
        os2_win_desc=args.os2_win_descent,
    )

    # File stem keeps metrics so side-by-side experiments don't collide.
    stem = f"{args.family_ps}"
    pairs = [
        (
            args.mono_regular,
            args.sc_regular,
            args.out_dir / f"{stem}-Regular.ttf",
            "Regular",
        ),
        (
            args.mono_bold,
            args.sc_bold,
            args.out_dir / f"{stem}-Bold.ttf",
            "Bold",
        ),
    ]
    for mono_p, sc_p, out_p, sub in pairs:
        if not mono_p.exists() or not sc_p.exists():
            print(f"Missing source fonts: {mono_p} / {sc_p}", file=sys.stderr)
            return 1
        merge_pair(
            mono_p,
            sc_p,
            out_p,
            sub,
            en_adv=args.en_adv,
            cjk_adv=args.cjk_adv,
            mono_src_adv=args.mono_src_adv,
            family=args.family,
            family_ps=args.family_ps,
            metrics=metrics,
        )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
