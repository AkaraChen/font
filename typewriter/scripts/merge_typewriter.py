#!/usr/bin/env python3
"""Merge Courier Prime + Zhuque Fangsong into a dual-width coding face.

Default product metrics: EN 600 / CJK 1200 (strict 2:1).

Character policy
----------------
- Courier Prime (UPM normalized to 1000; mono cell → EN_ADV): Latin, digits,
  programming symbols, half-width punctuation. Layout tables kept if present.
- Zhuque Fangsong (advance expanded & centred to CJK_ADV): CJK ideographs,
  CJK punctuation, fullwidth forms, kana / bopomofo. **Embedded Alegreya Latin
  is discarded** — only CJK-side ranges are imported.

Family naming: "PrimeZhuque Dual" intermediate / "PrimeZhuque NFM" product.
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.ttLib.tables import ttProgram
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

# scale_upem() rewrites glyf coordinates but leaves TrueType hinting alone:
# cvt values, prep/fpgm and per-glyph bytecode all keep measuring in the OLD
# UPM. Courier Prime ships full hinting at UPM 2048, so after 2048→1000 every
# grid-fit distance is ~2.05× too large and FreeType mangles the outlines at
# coding sizes (i loses its dot, crossbars slide off the stem, parens shear).
# Same table list as handwriting/scripts/prepare_cjk.py.
HINT_TABLES = ("prep", "fpgm", "cvt ", "gasp", "hdmx", "LTSH", "VDMX")


def is_cjk_side(cp: int) -> bool:
    """True for CJK-side codepoints we take from Zhuque (not Alegreya Latin)."""
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


def drop_hinting(font: TTFont) -> None:
    """Strip TrueType hinting that no longer matches the glyf coordinates."""
    for tag in HINT_TABLES:
        if tag in font:
            del font[tag]

    glyf = font["glyf"]
    empty = ttProgram.Program()
    empty.fromBytecode(b"")
    stripped = 0
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        if getattr(glyph, "program", None) is not None:
            glyph.program = empty
            stripped += 1
    print(f"  dropped hinting ({stripped} glyph program(s) + {'/'.join(HINT_TABLES)})")


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


def _scale_value_record_x(vr, scale: float) -> None:
    if vr is None:
        return
    for attr in ("XAdvance", "XPlacement"):
        if hasattr(vr, attr):
            val = getattr(vr, attr)
            if val:
                setattr(vr, attr, int(round(val * scale)))


def _scale_anchor_x(anchor, scale: float) -> None:
    if anchor is None:
        return
    if hasattr(anchor, "XCoordinate") and anchor.XCoordinate is not None:
        anchor.XCoordinate = int(round(anchor.XCoordinate * scale))


def scale_gpos_x(font: TTFont, scale: float) -> None:
    if "GPOS" not in font or abs(scale - 1.0) < 1e-9:
        return
    gpos = font["GPOS"].table
    if not gpos.LookupList:
        return
    for lookup in gpos.LookupList.Lookup:
        for st in lookup.SubTable:
            if hasattr(st, "Value") and st.Value is not None:
                _scale_value_record_x(st.Value, scale)
            if hasattr(st, "Value1"):
                _scale_value_record_x(st.Value1, scale)
            if hasattr(st, "Value2"):
                _scale_value_record_x(st.Value2, scale)
            if hasattr(st, "PairSet"):
                for ps in st.PairSet or []:
                    for pr in ps.PairValueRecord or []:
                        _scale_value_record_x(getattr(pr, "Value1", None), scale)
                        _scale_value_record_x(getattr(pr, "Value2", None), scale)
            if hasattr(st, "Class1Record"):
                for row in st.Class1Record or []:
                    for rec in row.Class2Record or []:
                        _scale_value_record_x(getattr(rec, "Value1", None), scale)
                        _scale_value_record_x(getattr(rec, "Value2", None), scale)
            if hasattr(st, "MarkArray") and st.MarkArray is not None:
                for rec in st.MarkArray.MarkRecord or []:
                    _scale_anchor_x(rec.MarkAnchor, scale)
            if hasattr(st, "BaseArray") and st.BaseArray is not None:
                for rec in st.BaseArray.BaseRecord or []:
                    for anchor in rec.BaseAnchor or []:
                        _scale_anchor_x(anchor, scale)
            if hasattr(st, "Mark2Array") and st.Mark2Array is not None:
                for rec in st.Mark2Array.Mark2Record or []:
                    for anchor in rec.Mark2Anchor or []:
                        _scale_anchor_x(anchor, scale)
            if hasattr(st, "LigatureArray") and st.LigatureArray is not None:
                for lig in st.LigatureArray.LigatureAttach or []:
                    for comp in lig.ComponentRecord or []:
                        for anchor in comp.LigatureAnchor or []:
                            _scale_anchor_x(anchor, scale)


def scale_latin_font(font: TTFont, scale: float, target_adv: int, src_adv: int) -> None:
    glyf = font["glyf"]
    hmtx = font["hmtx"].metrics

    if "kern" in font:
        del font["kern"]
    # Anisotropic X scaling invalidates any surviving hinting too.
    drop_hinting(font)

    for name in font.getGlyphOrder():
        g = glyf[name]
        old_w, old_lsb = hmtx[name]
        scale_glyph_x(g, glyf, scale)
        new_lsb = int(round(old_lsb * scale))
        if old_w == 0:
            hmtx[name] = (0, new_lsb)
        elif src_adv and old_w == src_adv:
            hmtx[name] = (target_adv, new_lsb)
        else:
            hmtx[name] = (max(0, int(round(old_w * scale))), new_lsb)

    scale_gpos_x(font, scale)

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
        dest_name = f"cjk.{name}"
        n = 1
        while dest_name in dst["glyf"]:
            dest_name = f"cjk.{name}.{n}"
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

    keep_ids = {0, 7, 8, 9, 10, 11, 13, 14}
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
        f"1.000;KIT;{family} merge (Courier Prime + Zhuque Fangsong; "
        f"EN {en_adv} / CJK {cjk_adv})",
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
    os2.xAvgCharWidth = en_adv
    font["post"].isFixedPitch = 1
    try:
        os2.panose.bProportion = 9  # Monospaced
    except Exception:
        pass


def prepare_latin(
    latin_path: Path,
    *,
    src_upm: int,
    target_upm: int,
    en_adv: int,
    latin_src_adv: int,
) -> TTFont:
    latin = TTFont(latin_path, recalcBBoxes=True, recalcTimestamp=False)
    current_upm = latin["head"].unitsPerEm
    if target_upm and current_upm != target_upm:
        print(f"  scale_upem {current_upm} → {target_upm}")
        scale_upem(latin, target_upm)
        drop_hinting(latin)
        # After UPM normalize, mono cell becomes latin_src_adv (e.g. 600)
        current_src_adv = latin_src_adv
    else:
        current_src_adv = (
            latin_src_adv
            if current_upm == target_upm
            else int(round(latin_src_adv * current_upm / src_upm))
            if src_upm
            else latin_src_adv
        )

    # Sample actual advance of 'A' for scale basis when close to mono
    cm = latin.getBestCmap() or {}
    if ord("A") in cm:
        actual = latin["hmtx"].metrics[cm[ord("A")]][0]
        if actual:
            current_src_adv = actual

    scale = en_adv / current_src_adv if current_src_adv else 1.0
    print(
        f"  Scaling Latin glyphs X * {scale:.6f} "
        f"(src_adv={current_src_adv} → {en_adv})"
    )
    if abs(scale - 1.0) > 1e-9:
        scale_latin_font(latin, scale, en_adv, current_src_adv)
    else:
        # Still map mono cells to en_adv in case of rounding drift
        hmtx = latin["hmtx"].metrics
        for name in latin.getGlyphOrder():
            w, lsb = hmtx[name]
            if w == current_src_adv:
                hmtx[name] = (en_adv, lsb)
        for tag in ("hdmx", "LTSH", "VDMX"):
            if tag in latin:
                del latin[tag]
    return latin


def merge_pair(
    latin_path: Path,
    cjk_path: Path,
    out_path: Path,
    subfamily: str,
    *,
    en_adv: int,
    cjk_adv: int,
    latin_src_adv: int,
    latin_src_upm: int,
    latin_target_upm: int,
    family: str,
    family_ps: str,
    metrics: dict,
) -> dict[str, int]:
    print(f"Loading {latin_path.name} + {cjk_path.name} ...")
    latin = prepare_latin(
        latin_path,
        src_upm=latin_src_upm,
        target_upm=latin_target_upm,
        en_adv=en_adv,
        latin_src_adv=latin_src_adv,
    )
    cjk = TTFont(cjk_path, recalcBBoxes=True, recalcTimestamp=False)

    # CJK may already be UPM 1000; if not, normalize
    if cjk["head"].unitsPerEm != latin_target_upm:
        print(f"  scale_upem CJK {cjk['head'].unitsPerEm} → {latin_target_upm}")
        scale_upem(cjk, latin_target_upm)
        drop_hinting(cjk)

    print("  Importing CJK-side only (discard Alegreya Latin from Zhuque)")
    latin_cmap = latin.getBestCmap() or {}
    cjk_cmap = cjk.getBestCmap() or {}

    to_import: dict[int, str] = {}
    for cp, gname in cjk_cmap.items():
        if is_cjk_side(cp):
            to_import[cp] = gname

    print(f"  Importing {len(to_import)} CJK-side codepoints ...")

    rename: dict[str, str] = {}
    final_map: dict[int, str] = dict(latin_cmap)

    for i, (cp, src_name) in enumerate(sorted(to_import.items())):
        if i and i % 5000 == 0:
            print(f"    ... {i}/{len(to_import)}")
        dest_name = copy_glyph_deep(cjk, latin, src_name, rename)
        set_cjk_metrics(latin, dest_name, cjk_adv)
        final_map[cp] = dest_name

    for ch in "中文荷塘月色":
        if ord(ch) not in final_map:
            raise SystemExit(f"missing required CJK sample glyph: {ch}")

    rebuild_cmap(latin, final_map)
    rename_family(latin, family, subfamily, family_ps, en_adv, cjk_adv)
    unify_metrics(latin, en_adv=en_adv, **metrics)

    # Bold OS/2 weight class
    if subfamily.lower() == "bold" and "OS/2" in latin:
        latin["OS/2"].usWeightClass = 700
        latin["OS/2"].fsSelection = (latin["OS/2"].fsSelection | 0x20) & ~0x40
    elif subfamily.lower() == "regular" and "OS/2" in latin:
        latin["OS/2"].usWeightClass = 400
        latin["OS/2"].fsSelection = (latin["OS/2"].fsSelection | 0x40) & ~0x20

    glyf = latin["glyf"]
    for gname in latin.getGlyphOrder():
        g = glyf[gname]
        if g.numberOfContours != 0:
            try:
                g.recalcBounds(glyf)
            except Exception:
                pass
    latin["maxp"].recalc(latin)
    latin["hhea"].advanceWidthMax = max(m[0] for m in latin["hmtx"].metrics.values())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    latin.save(out_path)
    latin.close()
    cjk.close()

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
    p.add_argument("--latin-regular", type=Path, required=True)
    p.add_argument("--latin-bold", type=Path, required=True)
    p.add_argument("--cjk-regular", "--sc-regular", dest="cjk_regular", type=Path, required=True)
    p.add_argument("--cjk-bold", "--sc-bold", dest="cjk_bold", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--en-adv", type=int, default=600)
    p.add_argument("--cjk-adv", type=int, default=1200)
    p.add_argument("--latin-src-adv", type=int, default=600)
    p.add_argument("--latin-src-upm", type=int, default=2048)
    p.add_argument("--latin-target-upm", type=int, default=1000)
    p.add_argument("--family", default="PrimeZhuque Dual")
    p.add_argument("--family-ps", default="PrimeZhuqueDual")
    p.add_argument("--hhea-ascent", type=int, default=1050)
    p.add_argument("--hhea-descent", type=int, default=-300)
    p.add_argument("--hhea-line-gap", type=int, default=0)
    p.add_argument("--os2-typo-ascender", type=int, default=880)
    p.add_argument("--os2-typo-descender", type=int, default=-220)
    p.add_argument("--os2-typo-line-gap", type=int, default=0)
    p.add_argument("--os2-win-ascent", type=int, default=1100)
    p.add_argument("--os2-win-descent", type=int, default=320)
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

    stem = f"{args.family_ps}"
    pairs = [
        (
            args.latin_regular,
            args.cjk_regular,
            args.out_dir / f"{stem}-Regular.ttf",
            "Regular",
        ),
        (
            args.latin_bold,
            args.cjk_bold,
            args.out_dir / f"{stem}-Bold.ttf",
            "Bold",
        ),
    ]
    for latin_p, cjk_p, out_p, sub in pairs:
        if not latin_p.exists() or not cjk_p.exists():
            print(f"Missing source fonts: {latin_p} / {cjk_p}", file=sys.stderr)
            return 1
        merge_pair(
            latin_p,
            cjk_p,
            out_p,
            sub,
            en_adv=args.en_adv,
            cjk_adv=args.cjk_adv,
            latin_src_adv=args.latin_src_adv,
            latin_src_upm=args.latin_src_upm,
            latin_target_upm=args.latin_target_upm,
            family=args.family,
            family_ps=args.family_ps,
            metrics=metrics,
        )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
