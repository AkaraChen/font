#!/usr/bin/env python3
"""Experimental dual-width merge: Latin mono + CJK sans → EN 500 / CJK 1000.

ponytail: one-shot preview path for KIT-286 neo-grotesque bake-off.
Not a product pipeline (no Nerd / fingerprint / embolden calibration).
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

from fontTools.misc.transform import Transform
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

CJK_RANGES = (
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
)

DROP = ("CFF ", "CFF2", "VORG", "hdmx", "LTSH", "VDMX", "kern")


def is_cjk_side(cp: int) -> bool:
    return any(a <= cp <= b for a, b in CJK_RANGES)


def cff_to_glyf(font: TTFont, transform: Transform, max_err: float = 0.5) -> None:
    glyph_set = font.getGlyphSet()
    order = font.getGlyphOrder()
    glyf = newTable("glyf")
    glyf.glyphOrder = list(order)
    glyphs = {}
    for i, name in enumerate(order):
        pen = TTGlyphPen(None)
        source = TransformPen(Cu2QuPen(pen, max_err), transform)
        glyph_set[name].draw(source)
        glyphs[name] = pen.glyph()
        if i and i % 5000 == 0:
            print(f"    … cu2qu {i}/{len(order)}")
    glyf.glyphs = glyphs
    post = font["post"]
    post.formatType = 2.0
    post.extraNames = []
    post.mapping = {}
    post.glyphOrder = None
    for tag in DROP:
        if tag in font:
            del font[tag]
    font["glyf"] = glyf
    font["loca"] = newTable("loca")
    font.sfntVersion = "\x00\x01\x00\x00"
    font["maxp"].tableVersion = 0x00010000
    for attr, value in (
        ("maxZones", 1),
        ("maxTwilightPoints", 0),
        ("maxStorage", 0),
        ("maxFunctionDefs", 0),
        ("maxInstructionDefs", 0),
        ("maxStackElements", 0),
        ("maxSizeOfInstructions", 0),
        ("maxComponentElements", 0),
        ("maxComponentDepth", 0),
    ):
        setattr(font["maxp"], attr, value)
    for name in order:
        g = glyf[name]
        if g.numberOfContours != 0:
            g.recalcBounds(glyf)
    font["maxp"].recalc(font)


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


def scale_latin_ttf(font: TTFont, scale: float, target_adv: int, src_adv: int) -> None:
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
        if old_w == 0:
            hmtx[name] = (0, new_lsb)
        elif src_adv and old_w == src_adv:
            hmtx[name] = (target_adv, new_lsb)
        else:
            hmtx[name] = (max(0, int(round(old_w * scale))), new_lsb)
    if "maxp" in font:
        font["maxp"].recalc(font)


def scale_hmtx_after_transform(
    font: TTFont, x_scale: float, en_adv: int, src_adv: int
) -> None:
    hmtx = font["hmtx"].metrics
    glyf = font["glyf"]
    for name in font.getGlyphOrder():
        width, _ = hmtx[name]
        glyph = glyf[name]
        lsb = glyph.xMin if glyph.numberOfContours != 0 else 0
        if width == 0:
            new_w = 0
        elif width == src_adv:
            new_w = en_adv
        else:
            new_w = max(0, round(width * x_scale))
        hmtx[name] = (new_w, lsb)
    font["hhea"].advanceWidthMax = max(w for w, _ in hmtx.values())
    font["OS/2"].xAvgCharWidth = en_adv


def ensure_glyf_latin(
    path: Path,
    *,
    en_adv: int,
    src_adv: int | None,
    monaspace_recipe: bool,
) -> TTFont:
    font = TTFont(path, recalcBBoxes=True, recalcTimestamp=False)
    if monaspace_recipe:
        # Same as handwriting: narrow 1240→1111 @2000, ×0.9, UPM→1000 → cell 500
        src_upm = font["head"].unitsPerEm
        src = src_adv or 1240
        narrow, uniform, upm = 1111, 0.9, 1000
        upm_scale = upm / src_upm
        x_scale = (narrow / src) * uniform * upm_scale
        y_scale = uniform * upm_scale
        print(f"  monaspace recipe x×{x_scale:.6f} y×{y_scale:.6f} → {en_adv}@{upm}")
        if "CFF " in font or "CFF2" in font:
            cff_to_glyf(font, Transform(x_scale, 0, 0, y_scale, 0, 0))
        else:
            # already glyf: apply transform via re-draw
            cff_to_glyf(font, Transform(x_scale, 0, 0, y_scale, 0, 0))
        font["head"].unitsPerEm = upm
        scale_hmtx_after_transform(font, x_scale, en_adv, src)
        return font

    # Plain mono TTF: x-scale cell to en_adv
    if "CFF " in font or "CFF2" in font:
        src = src_adv
        if src is None:
            cm = font.getBestCmap() or {}
            src = font["hmtx"][cm[ord("a")]][0]
        scale = en_adv / src
        print(f"  CFF→glyf + X×{scale:.6f} → {en_adv}")
        cff_to_glyf(font, Transform(scale, 0, 0, 1, 0, 0))
        scale_hmtx_after_transform(font, scale, en_adv, src)
        return font

    cm = font.getBestCmap() or {}
    src = src_adv or font["hmtx"][cm[ord("a")]][0]
    scale = en_adv / src
    print(f"  TTF X×{scale:.6f} ({src}→{en_adv})")
    scale_latin_ttf(font, scale, en_adv, src)
    return font


def subset_cjk(font: TTFont, text: str) -> None:
    """Keep CJK needed for sample + a bit of ASCII fallback from CJK side."""
    cps = {ord(c) for c in text}
    # Always keep these for the footer/grid check
    cps |= {ord(c) for c in "中文荷塘月色编程注释对齐检查易混字符运算符"}
    cps |= set(range(0x20, 0x7F))  # ASCII from SC if Latin misses
    # CJK punctuation common in samples
    cps |= set(range(0x3000, 0x303F))
    cps |= set(range(0xFF00, 0xFFEF))
    opts = Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.name_languages = ["*"]
    opts.notdef_outline = True
    opts.recommended_glyphs = True
    opts.drop_tables += ["GPOS", "GSUB", "GDEF", "BASE", "JSTF", "vmtx", "vhea"]
    sub = Subsetter(options=opts)
    sub.populate(unicodes=sorted(cps))
    sub.subset(font)
    print(f"  subset → {len(font.getGlyphOrder())} glyphs")


def prepare_cjk(path: Path, text: str, cjk_adv: int, upm: int = 1000) -> TTFont:
    """Subset → uniform scale to product UPM → snap full/half cells."""
    font = TTFont(path, recalcBBoxes=True, recalcTimestamp=False)
    src_upm = font["head"].unitsPerEm
    print(f"  CJK load {path.name} UPM={src_upm}")
    # Capture pre-subset advances by glyph name
    src_adv = {n: font["hmtx"].metrics[n] for n in font.getGlyphOrder()}
    subset_cjk(font, text)
    scale = upm / src_upm
    print(f"  CJK outlines scale×{scale:.6f} → UPM {upm}")
    cff_to_glyf(font, Transform(scale, 0, 0, scale, 0, 0))
    font["head"].unitsPerEm = upm
    half = cjk_adv // 2
    glyf = font["glyf"]
    for name in font.getGlyphOrder():
        old_w, old_lsb = src_adv.get(name, (cjk_adv, 0))
        new_w = round(old_w * scale)
        new_lsb = round(old_lsb * scale)
        if old_w == 0:
            font["hmtx"].metrics[name] = (0, new_lsb)
        elif abs(old_w - src_upm) <= 2:
            pad = cjk_adv - new_w
            font["hmtx"].metrics[name] = (cjk_adv, new_lsb + pad // 2)
        elif abs(old_w - src_upm / 2) <= 2:
            pad = half - new_w
            font["hmtx"].metrics[name] = (half, new_lsb + pad // 2)
        else:
            font["hmtx"].metrics[name] = (max(0, new_w), new_lsb)
        g = glyf[name]
        if g.numberOfContours != 0:
            try:
                g.recalcBounds(glyf)
            except Exception:
                pass
    return font


def ensure_glyph_slot(dst: TTFont, name: str) -> None:
    order = dst.getGlyphOrder()
    if name not in order:
        order.append(name)
        dst.setGlyphOrder(order)
        dst["maxp"].numGlyphs = len(order)


def copy_glyph_deep(src: TTFont, dst: TTFont, name: str, rename: dict[str, str]) -> str:
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
    g = copy.deepcopy(src["glyf"][name])
    if g.isComposite():
        for component in g.components:
            component.glyphName = copy_glyph_deep(src, dst, component.glyphName, rename)
    ensure_glyph_slot(dst, dest_name)
    dst["glyf"][dest_name] = g
    w, lsb = src["hmtx"].metrics[name]
    dst["hmtx"].metrics[dest_name] = (w, lsb)
    return dest_name


def center_advance(old_adv: int, old_lsb: int, new_adv: int) -> int:
    return old_lsb + (new_adv - old_adv) // 2


def rebuild_cmap(dst: TTFont, mapping: dict[int, str]) -> None:
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


def rename_family(font: TTFont, family: str, subfamily: str = "Regular") -> None:
    name = font["name"]
    full = f"{family} {subfamily}" if subfamily != "Regular" else family
    ps = family.replace(" ", "") + "-" + subfamily.replace(" ", "")
    keep = {0, 7, 8, 9, 10, 11, 13, 14}
    name.names = [r for r in name.names if r.nameID in keep]

    def add(nid: int, string: str) -> None:
        name.setName(string, nid, 3, 1, 0x409)

    add(1, family)
    add(2, subfamily)
    add(3, f"{family}: {subfamily}")
    add(4, full)
    add(6, ps)
    add(16, family)
    add(17, subfamily)
    add(5, f"0.001;KIT-286;experimental {family}")


def merge(
    latin_path: Path,
    cjk_path: Path,
    out_path: Path,
    *,
    family: str,
    text: str,
    en_adv: int = 500,
    cjk_adv: int = 1000,
    latin_src_adv: int | None = None,
    monaspace_recipe: bool = False,
) -> dict[str, int]:
    print(f"== {family} ==")
    print(f"  Latin: {latin_path}")
    latin = ensure_glyf_latin(
        latin_path,
        en_adv=en_adv,
        src_adv=latin_src_adv,
        monaspace_recipe=monaspace_recipe,
    )
    print(f"  CJK: {cjk_path}")
    cjk = prepare_cjk(cjk_path, text, cjk_adv)

    latin_cmap = latin.getBestCmap() or {}
    cjk_cmap = cjk.getBestCmap() or {}
    to_import: dict[int, str] = {}
    for cp, gname in cjk_cmap.items():
        if is_cjk_side(cp) or cp not in latin_cmap:
            to_import[cp] = gname
    print(f"  importing {len(to_import)} CPs")

    rename: dict[str, str] = {}
    final_map = dict(latin_cmap)
    for cp, src_name in sorted(to_import.items()):
        dest = copy_glyph_deep(cjk, latin, src_name, rename)
        w, lsb = latin["hmtx"].metrics[dest]
        # Ensure wide CJK on full cell
        if is_cjk_side(cp) or w > en_adv * 1.2:
            target = cjk_adv
            if w != target:
                latin["hmtx"].metrics[dest] = (target, center_advance(w, lsb, target))
        elif w != en_adv and w != 0:
            # half-ish
            if abs(w - en_adv) > abs(w - cjk_adv):
                target = cjk_adv
            else:
                target = en_adv
            if w != target:
                latin["hmtx"].metrics[dest] = (target, center_advance(w, lsb, target))
        final_map[cp] = dest

    for ch in "中文荷":
        if ord(ch) not in final_map:
            raise SystemExit(f"missing required CJK: {ch}")

    rebuild_cmap(latin, final_map)
    rename_family(latin, family)

    # Vertical metrics: coding-friendly defaults @ UPM 1000
    hhea, os2 = latin["hhea"], latin["OS/2"]
    hhea.ascent, hhea.descent, hhea.lineGap = 950, -250, 0
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = 880, -220, 0
    os2.usWinAscent, os2.usWinDescent = 1050, 300
    os2.fsSelection |= 0x80
    os2.xAvgCharWidth = en_adv
    latin["post"].isFixedPitch = 1
    try:
        os2.panose.bProportion = 9
    except Exception:
        pass

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
    checks = {}
    for ch in list("aAi0中文荷") + [" "]:
        if ord(ch) in cm:
            checks[ch] = hmtx[cm[ord(ch)]][0]
    print(f"  saved {out_path.name} advances={checks}")
    v.close()
    return checks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--latin", type=Path, required=True)
    ap.add_argument("--cjk", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--family", required=True)
    ap.add_argument("--body-file", type=Path, required=True)
    ap.add_argument("--en-adv", type=int, default=500)
    ap.add_argument("--cjk-adv", type=int, default=1000)
    ap.add_argument("--latin-src-adv", type=int, default=None)
    ap.add_argument("--monaspace-recipe", action="store_true")
    args = ap.parse_args()
    text = args.body_file.read_text(encoding="utf-8")
    merge(
        args.latin,
        args.cjk,
        args.out,
        family=args.family,
        text=text,
        en_adv=args.en_adv,
        cjk_adv=args.cjk_adv,
        latin_src_adv=args.latin_src_adv,
        monaspace_recipe=args.monaspace_recipe,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
