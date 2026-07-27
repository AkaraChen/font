#!/usr/bin/env python3
"""Merge Monaspace Radon (Latin) + LXGW WenKai (CJK) into a dual-width coding face.

Default product metrics (UPM 1000): EN 620 / CJK 1240 (strict 2:1).

- Radon is scaled from UPM 2000 → TARGET_UPM (advances 1240 → 620).
- WenKai CJK outlines stay unscaled at UPM 1000; advance expanded & centred.
- Radon GSUB (calt/dlig coding ligatures, etc.) is preserved on Latin glyphs.
- Character policy mirrors sans/merge_plex.py (CJK ranges from WenKai; Latin
  from Radon; WenKai fills any codepoint Radon lacks).
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates


def is_cjk_side(cp: int) -> bool:
    ranges = (
        (0x2E80, 0x2EFF),
        (0x2F00, 0x2FDF),
        (0x3000, 0x303F),
        (0x3040, 0x30FF),
        (0x3100, 0x312F),
        (0x3190, 0x319F),
        (0x31A0, 0x31BF),
        (0x31C0, 0x31EF),
        (0x31F0, 0x31FF),
        (0x3200, 0x32FF),
        (0x3300, 0x33FF),
        (0x3400, 0x4DBF),
        (0x4E00, 0x9FFF),
        (0xF900, 0xFAFF),
        (0xFE30, 0xFE4F),
        (0xFF00, 0xFFEF),
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


def normalize_latin_cell(
    font: TTFont, cell: int, *, src_cell: int | None = None
) -> None:
    """Normalize Latin advances onto a mono cell grid (keep N-cell ligatures).

    Single-cell glyphs → ``cell``. Glyphs whose advance is ≈ k·src_cell keep
    k·cell so multi-character coding ligatures stay aligned. Optional uniform
    X-scale when ``src_cell != cell``.
    """
    glyf = font["glyf"]
    hmtx = font["hmtx"].metrics

    for tag in ("hdmx", "LTSH", "VDMX", "kern"):
        if tag in font:
            del font[tag]

    base = src_cell or cell
    scale = cell / base if base and base != cell else 1.0
    if scale != 1.0:
        print(f"  X-scale Latin * {scale:.6f} ({base} → {cell})")

    for name in font.getGlyphOrder():
        g = glyf[name]
        old_w, old_lsb = hmtx[name]
        if scale != 1.0:
            scale_glyph_x(g, glyf, scale)
            old_w = int(round(old_w * scale))
            old_lsb = int(round(old_lsb * scale))

        if old_w <= 0:
            hmtx[name] = (cell, old_lsb)
            continue

        # Snap to nearest positive integer number of cells
        k = max(1, int(round(old_w / cell)))
        # If it was clearly sub-cell noise, still one cell
        if old_w < cell * 0.6:
            k = 1
        new_w = k * cell
        # Recenter residual width change
        pad = new_w - old_w
        new_lsb = old_lsb + pad // 2
        hmtx[name] = (new_w, new_lsb)

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
    # shift outline if we expanded LSB
    shift = new_lsb - lsb
    if shift:
        g = dst["glyf"][glyph_name]
        if g.numberOfContours != 0 and not g.isComposite():
            coords = g.coordinates
            g.coordinates = GlyphCoordinates(
                [(x + shift, y) for x, y in coords]
            )
            g.recalcBounds(dst["glyf"])
        elif g.isComposite():
            for c in g.components:
                c.x = int(round(c.x + shift))
            g.recalcBounds(dst["glyf"])
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
        f"1.000;KIT;{family} (Monaspace Radon + LXGW WenKai; EN {en_adv} / CJK {cjk_adv})",
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
    # Dual-width 2:1 is still a fixed grid — advertise mono for font pickers
    # (same stance as serif NFM after fix-terminal-metrics).
    font["post"].isFixedPitch = 1
    try:
        os2.panose.bProportion = 9
    except Exception:
        pass
    try:
        os2.xAvgCharWidth = en_adv
    except Exception:
        pass


def load_latin(path: Path, target_upm: int) -> TTFont:
    font = TTFont(path, recalcBBoxes=True, recalcTimestamp=False)
    if font["head"].unitsPerEm != target_upm:
        print(
            f"  scale_upem Latin {font['head'].unitsPerEm} → {target_upm}",
            flush=True,
        )
        scale_upem(font, target_upm)
    return font


def load_cjk(path: Path, target_upm: int) -> TTFont:
    font = TTFont(path, recalcBBoxes=True, recalcTimestamp=False)
    if font["head"].unitsPerEm != target_upm:
        print(
            f"  scale_upem CJK {font['head'].unitsPerEm} → {target_upm}",
            flush=True,
        )
        scale_upem(font, target_upm)
    return font


def merge_pair(
    latin_path: Path,
    cjk_path: Path,
    out_path: Path,
    subfamily: str,
    *,
    en_adv: int,
    cjk_adv: int,
    target_upm: int,
    family: str,
    family_ps: str,
    metrics: dict,
) -> dict[str, int]:
    print(f"Loading {latin_path.name} + {cjk_path.name} ...", flush=True)
    latin = load_latin(latin_path, target_upm)
    cjk = load_cjk(cjk_path, target_upm)

    # After UPM normalize, Radon mono cell is en_adv (620). Keep N-cell
    # ligature advances as k·en_adv so coding ligatures still align.
    sample = latin.getBestCmap().get(ord("A"))
    cur = latin["hmtx"].metrics[sample][0] if sample else en_adv
    normalize_latin_cell(
        latin, en_adv, src_cell=cur if cur != en_adv else en_adv
    )

    latin_cmap = latin.getBestCmap() or {}
    cjk_cmap = cjk.getBestCmap() or {}

    to_import: dict[int, str] = {}
    for cp, gname in cjk_cmap.items():
        if is_cjk_side(cp) or cp not in latin_cmap:
            to_import[cp] = gname

    print(f"  Importing {len(to_import)} codepoints from WenKai ...", flush=True)

    rename: dict[str, str] = {}
    final_map: dict[int, str] = dict(latin_cmap)

    for i, (cp, src_name) in enumerate(sorted(to_import.items())):
        if i and i % 5000 == 0:
            print(f"    ... {i}/{len(to_import)}", flush=True)
        dest_name = copy_glyph_deep(cjk, latin, src_name, rename)
        set_cjk_metrics(latin, dest_name, cjk_adv)
        final_map[cp] = dest_name

    for ch in "中文荷塘月色":
        if ord(ch) not in final_map:
            raise SystemExit(f"missing required CJK sample glyph: {ch}")

    rebuild_cmap(latin, final_map)
    rename_family(latin, family, subfamily, family_ps, en_adv, cjk_adv)
    unify_metrics(latin, en_adv=en_adv, **metrics)

    # Drop CJK-side vertical layout that would confuse horizontal coding hosts
    for tag in ("vhea", "vmtx", "VORG"):
        if tag in latin:
            del latin[tag]

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

    # GSUB/GPOS from Radon remain (coding ligatures). Imported CJK glyphs are
    # not referenced by those lookups (different glyph names).

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
    feats = []
    if "GSUB" in v:
        feats = sorted(
            {
                fr.FeatureTag
                for fr in v["GSUB"].table.FeatureList.FeatureRecord
            }
        )
    v.close()
    print(f"  Saved {out_path}  advances={checks}")
    print(f"  GSUB features retained: {feats}")
    return checks


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--latin-regular", type=Path, required=True)
    p.add_argument("--latin-bold", type=Path, required=True)
    p.add_argument("--cjk-regular", type=Path, required=True)
    p.add_argument("--cjk-bold", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--en-adv", type=int, default=620)
    p.add_argument("--cjk-adv", type=int, default=1240)
    p.add_argument("--target-upm", type=int, default=1000)
    p.add_argument("--family", default="RadonWenKai Dual")
    p.add_argument("--family-ps", default="RadonWenKaiDual")
    p.add_argument("--hhea-ascent", type=int, default=945)
    p.add_argument("--hhea-descent", type=int, default=-200)
    p.add_argument("--hhea-line-gap", type=int, default=100)
    p.add_argument("--os2-typo-ascender", type=int, default=945)
    p.add_argument("--os2-typo-descender", type=int, default=-200)
    p.add_argument("--os2-typo-line-gap", type=int, default=100)
    p.add_argument("--os2-win-ascent", type=int, default=980)
    p.add_argument("--os2-win-descent", type=int, default=250)
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

    stem = args.family_ps
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
            target_upm=args.target_upm,
            family=args.family,
            family_ps=args.family_ps,
            metrics=metrics,
        )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
