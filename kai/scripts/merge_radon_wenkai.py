#!/usr/bin/env python3
"""Merge prepared Radon Latin + slanted WenKai CJK into RadonWenKai NFM.

Inputs are the two intermediates, already on the product grid:
  * Latin — `prepare_latin.py` output: glyf, UPM 1000, every cell 500,
    Nerd icons included, Radon GSUB/GDEF (`liga`, `calt`, `ss01`–`ss10`, `cv**`) intact.
  * CJK — `prepare_cjk.py` output: WenKai, weight-matched and sheared, native
    1000 advance = the full cell.

Character policy
----------------
| Source | Role |
| Radon (base font, kept whole) | ASCII, Latin, Greek/Cyrillic, programming symbols, box drawing, **Nerd icons**, **ligatures + OT features** |
| WenKai (imported) | Han, CJK punctuation, fullwidth forms, kana, bopomofo, and any codepoint Radon lacks |

Imported advances follow Unicode East_Asian_Width, because that is what a
terminal uses to size cells (it never asks the font): `W`/`F` → full cell,
everything else → half cell. An imported glyph too wide for the half cell is
x-compressed to fit rather than left overhanging its neighbour.

Radon stays the base font so its layout tables need no merging — the reason
ligatures survive at all. WenKai's own GSUB/GPOS is **not** merged (see README
limits).
"""

from __future__ import annotations

import argparse
import copy
import sys
import unicodedata
from pathlib import Path

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.misc.transform import Transform

MAX_GLYPHS = 0xFFFF

CJK_RANGES = (
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
REQUIRED_CJK_SAMPLE = "中文荷塘月色霞鹜楷编程注释"


def is_cjk_side(cp: int) -> bool:
    return any(lo <= cp <= hi for lo, hi in CJK_RANGES)


def is_wide(cp: int) -> bool:
    """East_Asian_Width W/F — a terminal always gives these two cells."""
    try:
        return unicodedata.east_asian_width(chr(cp)) in ("W", "F")
    except (ValueError, TypeError):
        return False


def ensure_glyph_slot(font: TTFont, name: str) -> None:
    order = font.getGlyphOrder()
    if name not in order:
        order.append(name)
        font.setGlyphOrder(order)
        font["maxp"].numGlyphs = len(order)


def copy_glyph_deep(
    src: TTFont,
    dst: TTFont,
    name: str,
    rename: dict[tuple[str, int | None], str],
    *,
    cell: int | None = None,
) -> str:
    """Copy a source glyph (with its components) into dst; return its new name.

    `cell` forks the cache: WenKai maps several codepoints to one glyph even when
    Unicode disagrees about their width (U+205A '⁚' shares its outline with a
    fullwidth colon), so a glyph wanted at two different advances must become two
    glyphs — otherwise whichever import ran last silently wins the advance.
    Components are cached without a cell, since only the top glyph carries one.
    """
    key = (name, cell)
    if key in rename:
        return rename[key]

    dest_name = name
    if name in dst["glyf"] and name != ".notdef":
        stem = f"wk.{name}"
        dest_name = stem
        n = 1
        while dest_name in dst["glyf"]:
            dest_name = f"{stem}.{n}"
            n += 1
    rename[key] = dest_name

    glyph = copy.deepcopy(src["glyf"][name])
    if glyph.isComposite():
        for component in glyph.components:
            component.glyphName = copy_glyph_deep(src, dst, component.glyphName, rename)

    ensure_glyph_slot(dst, dest_name)
    dst["glyf"][dest_name] = glyph
    dst["hmtx"].metrics[dest_name] = src["hmtx"].metrics[name]
    return dest_name


def fit_advance(font: TTFont, glyph_set, name: str, target: int) -> bool:
    """Move an imported glyph onto the target cell. Returns True if compressed.

    A glyph already drawn for that cell — every WenKai Han glyph on the full
    cell, halfwidth kana on the half cell — is left exactly as designed: no
    recentring, because CJK side bearings are deliberately asymmetric (radicals,
    punctuation that hugs one side) and the sheared outlines are *meant* to
    overhang a little, the way an italic does.

    Only glyphs whose native advance differs from the target are touched: the
    ink is x-compressed if it cannot fit the cell (WenKai's proportional Latin
    fallbacks), then the glyph is placed in the middle of its new cell.
    """
    glyf = font["glyf"]
    glyph = glyf[name]
    width, lsb = font["hmtx"].metrics[name]

    if glyph.numberOfContours == 0:
        font["hmtx"].metrics[name] = (target, lsb)
        return False
    if width == target:
        return False

    glyph.recalcBounds(glyf)
    ink = glyph.xMax - glyph.xMin
    compressed = ink > target > 0
    if compressed:
        pen = TTGlyphPen(None)
        recording = DecomposingRecordingPen(glyph_set)
        glyph_set[name].draw(recording)
        recording.replay(TransformPen(pen, Transform(target / ink, 0, 0, 1, 0, 0)))
        glyph = pen.glyph()
        glyf[name] = glyph
        glyph.recalcBounds(glyf)
        shift = (target - (glyph.xMax - glyph.xMin)) // 2 - glyph.xMin
    else:
        shift = (target - width) // 2

    shift_glyph(glyph, glyf, shift)
    font["hmtx"].metrics[name] = (target, glyph.xMin)
    return compressed


def shift_glyph(glyph, glyf, dx: int) -> None:
    if not dx or glyph.numberOfContours == 0:
        return
    if glyph.isComposite():
        for component in glyph.components:
            component.x += dx
    else:
        coords = glyph.coordinates
        for i in range(len(coords)):
            x, y = coords[i]
            coords[i] = (x + dx, y)
        glyph.coordinates = coords
    glyph.recalcBounds(glyf)


def widen_radon_wide_glyphs(
    font: TTFont,
    mapping: dict[int, str],
    en_adv: int,
    cjk_adv: int,
) -> int:
    """Give the full cell to EAW-wide codepoints only Radon covers.

    The Nerd patch draws e.g. ⚡ ⏩ 🕐 at Monaspace's single cell, but their
    East_Asian_Width is W, so a terminal reserves **two** cells for them no
    matter what the font says. Half-cell ink in a full-cell slot is merely a bit
    airy; a full-cell glyph in a one-cell slot would overlap its neighbour, so
    the advance is what has to move. The outline is centred, not stretched (same
    call as `serif/scripts/narrow-symbol-widths.py` makes for this case).
    """
    glyf = font["glyf"]
    hmtx = font["hmtx"].metrics
    users: dict[str, list[int]] = {}
    for cp, gname in mapping.items():
        users.setdefault(gname, []).append(cp)

    forks: dict[str, str] = {}
    widened = 0
    for cp in sorted(mapping):
        gname = mapping[cp]
        if not is_wide(cp) or hmtx[gname][0] != en_adv:
            continue
        if any(not is_wide(other) for other in users[gname]):
            # Shared with a narrow codepoint — fork so the narrow one keeps its cell
            if gname not in forks:
                fork = f"wide.{gname}"
                n = 1
                while fork in glyf:
                    fork = f"wide.{gname}.{n}"
                    n += 1
                ensure_glyph_slot(font, fork)
                glyf[fork] = copy.deepcopy(glyf[gname])
                hmtx[fork] = hmtx[gname]
                forks[gname] = fork
            gname = forks[gname]
            mapping[cp] = gname
            if hmtx[gname][0] == cjk_adv:
                continue
        glyph = glyf[gname]
        shift_glyph(glyph, glyf, (cjk_adv - en_adv) // 2)
        lsb = glyph.xMin if glyph.numberOfContours != 0 else hmtx[gname][1]
        hmtx[gname] = (cjk_adv, lsb)
        widened += 1
    return widened


def rebuild_cmap(font: TTFont, mapping: dict[int, str]) -> None:
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

    table = newTable("cmap")
    table.tableVersion = 0
    bmp = {cp: g for cp, g in mapping.items() if cp <= 0xFFFF}
    tables = []
    for platform_id, plat_enc_id, cmap_dict, fmt in (
        (3, 1, bmp, 4),
        (3, 10, mapping, 12),
        (0, 3, bmp, 4),
        (0, 4, mapping, 12),
    ):
        sub = CmapSubtable.newSubtable(fmt)
        sub.platformID = platform_id
        sub.platEncID = plat_enc_id
        sub.language = 0
        sub.cmap = dict(cmap_dict)
        tables.append(sub)
    table.tables = tables
    font["cmap"] = table


def rename_family(
    font: TTFont,
    family: str,
    subfamily: str,
    ps_base: str,
    *,
    version: str,
    en_adv: int,
    cjk_adv: int,
    slant_deg: float,
) -> None:
    name = font["name"]
    full = family if subfamily == "Regular" else f"{family} {subfamily}"
    postscript = f"{ps_base}-{subfamily.replace(' ', '')}"

    keep_ids = {0, 7, 8, 9, 10, 11, 13, 14}  # copyright / trademark / licence
    name.names = [r for r in name.names if r.nameID in keep_ids]

    def add(name_id: int, value: str) -> None:
        name.setName(value, name_id, 3, 1, 0x409)
        try:
            name.setName(value, name_id, 1, 0, 0)
        except Exception:
            pass

    add(1, family)
    add(2, subfamily)
    add(3, f"{family}: {subfamily}")
    add(4, full)
    add(6, postscript)
    add(16, family)
    add(17, subfamily)
    add(
        5,
        f"{version};KIT;{family} merge (Monaspace Radon NF + LXGW WenKai "
        f"{slant_deg:g}° slant; EN {en_adv} / CJK {cjk_adv})",
    )


def unify_metrics(font: TTFont, *, en_adv: int, metrics: dict) -> None:
    hhea = font["hhea"]
    os2 = font["OS/2"]
    hhea.ascent = metrics["hhea_ascent"]
    hhea.descent = metrics["hhea_descent"]
    hhea.lineGap = metrics["hhea_line_gap"]
    os2.sTypoAscender = metrics["os2_typo_asc"]
    os2.sTypoDescender = metrics["os2_typo_desc"]
    os2.sTypoLineGap = metrics["os2_typo_gap"]
    os2.usWinAscent = metrics["os2_win_asc"]
    os2.usWinDescent = metrics["os2_win_desc"]
    os2.fsSelection |= 0x80  # USE_TYPO_METRICS
    os2.xAvgCharWidth = en_adv
    # Coding product: keep the mono flags hosts read to answer "is this mono?"
    # (macOS kCTFontTraitMonoSpace, editor font pickers). A 2:1 dual-width face
    # is still a fixed-pitch grid as far as a terminal is concerned.
    font["post"].isFixedPitch = 1
    try:
        os2.panose.bProportion = 9
    except Exception:
        pass


def merge_pair(
    latin_path: Path,
    cjk_path: Path,
    out_path: Path,
    subfamily: str,
    *,
    en_adv: int,
    cjk_adv: int,
    family: str,
    family_ps: str,
    version: str,
    slant_deg: float,
    metrics: dict,
) -> None:
    print(f"Loading {latin_path.name} + {cjk_path.name}")
    latin = TTFont(latin_path, recalcBBoxes=True, recalcTimestamp=False)
    cjk = TTFont(cjk_path, recalcBBoxes=True, recalcTimestamp=False)

    if latin["head"].unitsPerEm != cjk["head"].unitsPerEm:
        raise SystemExit(
            f"error: UPM mismatch {latin['head'].unitsPerEm} vs {cjk['head'].unitsPerEm}"
        )

    latin_cmap = latin.getBestCmap() or {}
    cjk_cmap = cjk.getBestCmap() or {}
    # Also take WenKai's drawing for any East_Asian_Width W/F codepoint Radon
    # happens to cover (e.g. 〈 〉): those need a full cell, and WenKai already
    # draws them for one.
    to_import = {
        cp: g
        for cp, g in cjk_cmap.items()
        if is_cjk_side(cp) or is_wide(cp) or cp not in latin_cmap
    }
    projected = len(latin.getGlyphOrder()) + len(to_import)
    if projected > MAX_GLYPHS:
        raise SystemExit(f"error: projected {projected} glyphs exceeds the {MAX_GLYPHS} limit")
    print(f"  importing {len(to_import)} codepoints (projected {projected} glyphs)")

    rename: dict[tuple[str, int | None], str] = {}
    final_map = dict(latin_cmap)
    glyph_set = latin.getGlyphSet()
    wide = compressed = 0
    for i, (cp, src_name) in enumerate(sorted(to_import.items())):
        target = cjk_adv if is_wide(cp) else en_adv
        dest_name = copy_glyph_deep(cjk, latin, src_name, rename, cell=target)
        compressed += fit_advance(latin, glyph_set, dest_name, target)
        wide += target == cjk_adv
        final_map[cp] = dest_name
        if i and i % 8000 == 0:
            print(f"    … {i}/{len(to_import)}")
    print(
        f"  advances: {wide} full-cell, {len(to_import) - wide} half-cell "
        f"(by East_Asian_Width); {compressed} outlines x-compressed to fit"
    )

    widened = widen_radon_wide_glyphs(latin, final_map, en_adv, cjk_adv)
    print(f"  {widened} Radon-only EAW-wide glyphs re-cast into the full cell")

    for ch in REQUIRED_CJK_SAMPLE:
        if ord(ch) not in final_map:
            raise SystemExit(f"error: missing required CJK sample glyph {ch}")

    rebuild_cmap(latin, final_map)
    rename_family(
        latin,
        family,
        subfamily,
        family_ps,
        version=version,
        en_adv=en_adv,
        cjk_adv=cjk_adv,
        slant_deg=slant_deg,
    )
    unify_metrics(latin, en_adv=en_adv, metrics=metrics)

    latin["maxp"].recalc(latin)
    latin["hhea"].advanceWidthMax = max(w for w, _ in latin["hmtx"].metrics.values())
    if "vmtx" in latin:
        del latin["vmtx"]
    if "vhea" in latin:
        del latin["vhea"]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    latin.save(out_path)
    latin.close()
    cjk.close()

    check = TTFont(out_path)
    cmap = check.getBestCmap()
    hmtx = check["hmtx"]
    sample = {ch: hmtx[cmap[ord(ch)]][0] for ch in "Aa0中文，" if ord(ch) in cmap}
    gsub = (
        sorted({r.FeatureTag for r in check["GSUB"].table.FeatureList.FeatureRecord})
        if "GSUB" in check
        else []
    )
    print(f"  saved {out_path}  glyphs={len(check.getGlyphOrder())} advances={sample}")
    print(f"  GSUB: {gsub}")
    check.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--latin-regular", type=Path, required=True)
    ap.add_argument("--latin-bold", type=Path, required=True)
    ap.add_argument("--cjk-regular", type=Path, required=True)
    ap.add_argument("--cjk-bold", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--en-adv", type=int, default=500)
    ap.add_argument("--cjk-adv", type=int, default=1000)
    ap.add_argument("--family", default="RadonWenKai NFM")
    ap.add_argument("--family-ps", default="RadonWenKaiNFM")
    ap.add_argument("--version", default="1.000")
    ap.add_argument("--slant-deg", type=float, default=7.5)
    ap.add_argument("--hhea-ascent", type=int, default=950)
    ap.add_argument("--hhea-descent", type=int, default=-250)
    ap.add_argument("--hhea-line-gap", type=int, default=0)
    ap.add_argument("--os2-typo-ascender", type=int, default=880)
    ap.add_argument("--os2-typo-descender", type=int, default=-220)
    ap.add_argument("--os2-typo-line-gap", type=int, default=0)
    ap.add_argument("--os2-win-ascent", type=int, default=1032)
    ap.add_argument("--os2-win-descent", type=int, default=290)
    args = ap.parse_args()

    if args.cjk_adv != 2 * args.en_adv:
        print(
            f"warning: CJK_ADV ({args.cjk_adv}) != 2 × EN_ADV ({args.en_adv})",
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

    for latin, cjk, subfamily in (
        (args.latin_regular, args.cjk_regular, "Regular"),
        (args.latin_bold, args.cjk_bold, "Bold"),
    ):
        if not latin.exists() or not cjk.exists():
            print(f"error: missing intermediate {latin} / {cjk}", file=sys.stderr)
            return 1
        merge_pair(
            latin,
            cjk,
            args.out_dir / f"{args.family_ps}-{subfamily}.ttf",
            subfamily,
            en_adv=args.en_adv,
            cjk_adv=args.cjk_adv,
            family=args.family,
            family_ps=args.family_ps,
            version=args.version,
            slant_deg=args.slant_deg,
            metrics=metrics,
        )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
