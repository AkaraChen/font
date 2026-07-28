#!/usr/bin/env python3
"""One merge engine for every Latin × CJK family, driven by ``font.toml``.

Four families used to carry their own 484–614 line `merge_*.py`. They already
shared fifteen same-name same-signature functions (`scale_glyph_x`,
`scale_gpos_x`, `copy_glyph_deep`, `rebuild_cmap`, `rename_family`,
`unify_metrics`, `center_advance`, `ensure_glyph_slot`, `set_cjk_metrics`,
`is_cjk_side`, …); the sans↔rounded diff was almost entirely comments and one
glyph-name prefix. What genuinely differed is small, and is a declared option
here rather than a forked file:

  [merge].latin      what the Latin side needs before it is on the product grid
  [merge].cjk        same question for the CJK side
  [merge].import     which codepoints come from the CJK donor
  [merge].placement  how an imported glyph is put on its cell
  [merge].*          the handful of per-family finishing touches

Three things this engine deliberately keeps apart, because Phase 6 (`text`
profile) and the italic interface both need them separable:

* ``apply_vertical_metrics`` — line box + USE_TYPO_METRICS. Both profiles.
* ``declare_strict_2to1``    — the fixed-grid declaration (`post.isFixedPitch`,
  PANOSE bProportion, `xAvgCharWidth` = the half cell). **coding only**: a
  reading face has no terminal grid to be strict about. Optical stroke matching
  between Latin and CJK is the other half of what used to be one
  `unify_metrics`, and it lives where it belongs — the per-weight
  ``[calibration.<weight>].embolden`` the `cjk-prepared` step consumes, so a
  text profile can share the prepared CJK with the coding profile.
* ``apply_slope``            — `post.italicAngle`, the OS/2 fsSelection ITALIC
  bit and the `head.macStyle` italic bit, all written from one ``slope``
  argument. Upright is a value here, never an assumption: this build produces
  no italic yet, and that must stay a matter of which slope is asked for.

Calibration is read **per weight**. Since Light arrived, embolden strength and
shear are `[calibration.<weight>]` values, never the Regular number reused for
everything, so this engine refuses to run a weight that has no entry of its own.
"""

from __future__ import annotations

import argparse
import copy
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from fontTools.misc.transform import Transform
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.ttLib.tables import ttProgram
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

from fontkit.manifest import Manifest, load_manifest

# TrueType cannot address more glyphs than this, and a Latin base plus a full
# CJK donor gets close enough that it is worth saying so before the merge runs
# for twenty minutes.
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

# scale_upem() rewrites glyf coordinates but leaves TrueType hinting alone: cvt
# values, prep/fpgm and per-glyph bytecode all keep measuring in the OLD UPM.
# Courier Prime ships full hinting at UPM 2048, so after 2048→1000 every
# grid-fit distance is ~2.05× too large and FreeType mangles the outlines at
# coding sizes (i loses its dot, crossbars slide off the stem, parens shear).
HINT_TABLES = ("prep", "fpgm", "cvt ", "gasp", "hdmx", "LTSH", "VDMX")

# Unicode ranges a coding face keeps from a Latin donor that ships tens of
# thousands of stylistic alternates (Iosevka Curly alone is ~46k glyphs, which
# leaves no room under MAX_GLYPHS for a CJK donor).
CODING_LATIN_RANGES = (
    (0x0000, 0x007F),  # Basic Latin
    (0x00A0, 0x024F),  # Latin-1 + Extended-A/B
    (0x0370, 0x03FF),  # Greek
    (0x0400, 0x04FF),  # Cyrillic
    (0x1E00, 0x1EFF),  # Latin Extended Additional
    (0x2000, 0x206F),  # General Punctuation
    (0x2070, 0x209F),  # Super/subscripts
    (0x20A0, 0x20CF),  # Currency
    (0x2100, 0x214F),  # Letterlike
    (0x2190, 0x21FF),  # Arrows
    (0x2200, 0x22FF),  # Math operators
    (0x2300, 0x23FF),  # Misc technical
    (0x2460, 0x24FF),  # Enclosed alphanumerics
    (0x2500, 0x259F),  # Box drawing / blocks
    (0x25A0, 0x25FF),  # Geometric shapes
    (0x2600, 0x27BF),  # Misc symbols + dingbats
    (0x27C0, 0x27EF),  # Misc math
    (0x27F0, 0x27FF),  # Supplemental arrows-A
    (0x2900, 0x297F),  # Supplemental arrows-B
    (0x2980, 0x29FF),  # Misc math symbols-B
    (0x2A00, 0x2AFF),  # Supplemental math operators
    (0x2B00, 0x2BFF),  # Misc symbols and arrows
    (0xFB00, 0xFB06),  # Alphabetic presentation forms (fi fl)
)

# Programming ligatures / composition survive the subset; bulk ss**/cv**
# alternates do not.
CODING_LAYOUT_FEATURES = [
    "calt",
    "liga",
    "dlig",
    "rlig",
    "clig",
    "ccmp",
    "mark",
    "mkmk",
    "kern",
    "locl",
]


def is_cjk_side(cp: int) -> bool:
    return any(lo <= cp <= hi for lo, hi in CJK_RANGES)


def is_wide(cp: int) -> bool:
    """East_Asian_Width W/F — a terminal always gives these two cells."""
    try:
        return unicodedata.east_asian_width(chr(cp)) in ("W", "F")
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- #
# the spec — every per-family difference, resolved from font.toml
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MergeSpec:
    """What `[merge]` in a family's font.toml resolves to."""

    # naming
    family: str
    family_ps: str
    version: str
    sources_note: str

    # grid
    en_adv: int
    cjk_adv: int
    metrics: dict
    profile: str
    slope: str
    slant_deg: float

    # engine options
    latin: str  # none | scale | normalize
    cjk: str  # as-is | normalize | require-same-upm
    import_policy: str  # cjk-side | cjk-side-or-missing | east-asian-width
    placement: str  # center | fit
    glyph_prefix: str
    required_sample: str
    latin_subset: str  # none | coding
    latin_src_adv: int | None
    latin_target_upm: int | None
    drop_hinting_on_upem_change: bool
    set_weight_class: bool
    recalc_bounds: bool
    widen_wide_base_glyphs: bool
    drop_vertical_metrics: bool
    check_glyph_budget: bool


def spec_from_manifest(
    manifest: Manifest,
    weight: str,
    *,
    profile: str = "coding",
    slope: str = "upright",
) -> MergeSpec:
    """Resolve one (weight, profile, slope) cell of the build matrix.

    ``weight`` is the product subfamily ("Regular", "Bold", "Light"); the
    calibration entry it needs is its own, never Regular's.
    """
    merge = manifest.merge
    if merge is None:
        raise SystemExit(f"error: {manifest.family}/font.toml has no [merge] section")

    key = weight.lower()
    if key not in manifest.calibration:
        raise SystemExit(
            f"error: no [calibration.{key}] in {manifest.family}/font.toml — "
            "every weight is calibrated on its own, Regular's numbers are not a default"
        )
    calibration = manifest.calibration[key]

    metrics = manifest.metrics.get(profile)
    if metrics is None:
        raise SystemExit(f"error: {manifest.family}/font.toml has no [metrics.{profile}]")

    naming = manifest.naming
    # The merge writes the intermediate face where a family has one (the "Dual"
    # products that are later Nerd-patched into the shipped family), and the
    # product face where it does not.
    base = naming.base_family or naming.family
    family = base if not naming.suffix else f"{base} {naming.suffix}"

    return MergeSpec(
        family=family,
        family_ps=naming.base_ps or naming.ps,
        version=merge.version,
        sources_note=merge.sources_note.format(slant=f"{calibration.slant_deg:g}"),
        en_adv=manifest.grid.en_adv,
        cjk_adv=manifest.grid.cjk_adv,
        metrics={
            "hhea_ascent": metrics.hhea_ascent,
            "hhea_descent": metrics.hhea_descent,
            "hhea_line_gap": metrics.hhea_line_gap,
            "os2_typo_asc": metrics.os2_typo_ascender,
            "os2_typo_desc": metrics.os2_typo_descender,
            "os2_typo_gap": metrics.os2_typo_line_gap,
            "os2_win_asc": metrics.os2_win_ascent,
            "os2_win_desc": metrics.os2_win_descent,
        },
        profile=profile,
        slope=slope,
        # The shear this weight is calibrated to. handwriting already uses it as
        # a CJK shear; that IS the italic mechanism, so it stays one parameter
        # rather than becoming a handwriting-only special case.
        slant_deg=calibration.slant_deg,
        latin=merge.latin,
        cjk=merge.cjk,
        import_policy=merge.import_policy,
        placement=merge.placement,
        glyph_prefix=merge.glyph_prefix,
        required_sample=merge.required_sample,
        latin_subset=merge.latin_subset,
        latin_src_adv=manifest.grid.latin_src_adv,
        latin_target_upm=manifest.grid.latin_target_upm,
        drop_hinting_on_upem_change=merge.drop_hinting,
        set_weight_class=merge.set_weight_class,
        recalc_bounds=merge.recalc_bounds,
        widen_wide_base_glyphs=merge.widen_wide_base_glyphs,
        drop_vertical_metrics=merge.drop_vertical_metrics,
        check_glyph_budget=merge.check_glyph_budget,
    )


# --------------------------------------------------------------------------- #
# outline / metric primitives
# --------------------------------------------------------------------------- #


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
    glyph.coordinates = GlyphCoordinates([(int(round(x * scale)), y) for x, y in coords])
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
    """Scale horizontal GPOS deltas / anchors after an anisotropic X scale."""
    if "GPOS" not in font or abs(scale - 1.0) < 1e-9:
        return
    gpos = font["GPOS"].table
    if not gpos.LookupList:
        return
    for lookup in gpos.LookupList.Lookup:
        for st in lookup.SubTable:
            # PairPos / SinglePos value records
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
            # MarkToBase / MarkToMark / MarkToLigature anchors
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


def scale_latin_font(
    font: TTFont,
    scale: float,
    target_adv: int,
    src_adv: int,
    *,
    drop_hinting_too: bool = False,
) -> None:
    """X-scale outlines; map mono-cell advances → target_adv; keep 0-width marks."""
    glyf = font["glyf"]
    hmtx = font["hmtx"].metrics

    if drop_hinting_too:
        # Anisotropic X scaling invalidates hinting as thoroughly as a UPM change.
        if "kern" in font:
            del font["kern"]
        drop_hinting(font)
    else:
        # Bitmap / device tables invalid after outline scale
        for tag in ("hdmx", "LTSH", "VDMX", "kern"):
            if tag in font:
                del font[tag]

    for name in font.getGlyphOrder():
        g = glyf[name]
        old_w, old_lsb = hmtx[name]
        scale_glyph_x(g, glyf, scale)
        new_lsb = int(round(old_lsb * scale))
        if old_w == 0:
            # Combining marks / control chars — keep zero advance for OT mark attach
            hmtx[name] = (0, new_lsb)
        elif src_adv and old_w == src_adv:
            hmtx[name] = (target_adv, new_lsb)
        else:
            # Multi-cell or odd advances: scale proportionally
            hmtx[name] = (max(0, int(round(old_w * scale))), new_lsb)

    scale_gpos_x(font, scale)

    if "maxp" in font:
        font["maxp"].recalc(font)


def center_advance(old_adv: int, old_lsb: int, new_adv: int) -> int:
    pad = new_adv - old_adv
    return old_lsb + pad // 2


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
    prefix: str,
    cell: int | None = None,
) -> str:
    """Copy a source glyph (with its components) into dst; return its new name.

    ``cell`` forks the cache: a CJK donor maps several codepoints to one glyph
    even when Unicode disagrees about their width (U+205A '⁚' shares its outline
    with a fullwidth colon), so a glyph wanted at two different advances must
    become two glyphs — otherwise whichever import ran last silently wins the
    advance. Components are cached without a cell, since only the top glyph
    carries one. A family placing every import on the same cell passes None and
    gets a plain by-name cache.
    """
    key = (name, cell)
    if key in rename:
        return rename[key]

    dest_name = name
    if name in dst["glyf"] and name != ".notdef":
        stem = f"{prefix}{name}"
        dest_name = stem
        n = 1
        while dest_name in dst["glyf"]:
            dest_name = f"{stem}.{n}"
            n += 1
    rename[key] = dest_name

    glyph = copy.deepcopy(src["glyf"][name])
    if glyph.isComposite():
        for component in glyph.components:
            component.glyphName = copy_glyph_deep(
                src, dst, component.glyphName, rename, prefix=prefix
            )

    ensure_glyph_slot(dst, dest_name)
    dst["glyf"][dest_name] = glyph
    dst["hmtx"].metrics[dest_name] = src["hmtx"].metrics[name]
    return dest_name


def set_cjk_metrics(font: TTFont, glyph_name: str, new_adv: int) -> None:
    """Place an import on its cell by side bearing alone — the ink is untouched."""
    w, lsb = font["hmtx"].metrics[glyph_name]
    font["hmtx"].metrics[glyph_name] = (new_adv, center_advance(w, lsb, new_adv))


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


def fit_advance(font: TTFont, glyph_set, name: str, target: int) -> bool:
    """Move an imported glyph onto the target cell. Returns True if compressed.

    A glyph already drawn for that cell — a Han glyph on the full cell,
    halfwidth kana on the half cell — is left exactly as designed: no recentring,
    because CJK side bearings are deliberately asymmetric (radicals, punctuation
    that hugs one side) and sheared outlines are *meant* to overhang a little,
    the way an italic does.

    Only glyphs whose native advance differs from the target are touched: the ink
    is x-compressed if it cannot fit the cell (a CJK donor's proportional Latin
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


def widen_wide_base_glyphs(
    font: TTFont,
    mapping: dict[int, str],
    en_adv: int,
    cjk_adv: int,
) -> int:
    """Give the full cell to EAW-wide codepoints only the Latin base covers.

    A Nerd patch draws e.g. ⚡ ⏩ 🕐 at the base font's single cell, but their
    East_Asian_Width is W, so a terminal reserves **two** cells for them no
    matter what the font says. Half-cell ink in a full-cell slot is merely a bit
    airy; a full-cell glyph in a one-cell slot would overlap its neighbour, so
    the advance is what has to move. The outline is centred, not stretched (same
    call `fontkit.narrow_symbol_widths` makes for this case).
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


def rename_family(font: TTFont, subfamily: str, spec: MergeSpec) -> None:
    name = font["name"]
    full = spec.family if subfamily == "Regular" else f"{spec.family} {subfamily}"
    postscript = f"{spec.family_ps}-{subfamily.replace(' ', '')}"

    # Keep copyright / trademark / manufacturer / designer / license URLs
    keep_ids = {0, 7, 8, 9, 10, 11, 13, 14}
    name.names = [r for r in name.names if r.nameID in keep_ids]

    def add(name_id: int, value: str) -> None:
        name.setName(value, name_id, 3, 1, 0x409)
        try:
            name.setName(value, name_id, 1, 0, 0)
        except Exception:
            pass

    add(1, spec.family)
    add(2, subfamily)
    add(3, f"{spec.family}: {subfamily}")
    add(4, full)
    add(6, postscript)
    add(16, spec.family)
    add(17, subfamily)
    add(
        5,
        f"{spec.version};KIT;{spec.family} merge ({spec.sources_note}; "
        f"EN {spec.en_adv} / CJK {spec.cjk_adv})",
    )


# --------------------------------------------------------------------------- #
# metrics — three independently callable steps
# --------------------------------------------------------------------------- #


def apply_vertical_metrics(font: TTFont, metrics: dict) -> None:
    """The line box. Every profile wants this; none of it is coding-specific."""
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


def declare_strict_2to1(font: TTFont, en_adv: int) -> None:
    """Declare the fixed 2:1 grid. **coding profile only.**

    This is the half of the old `unify_metrics` that serves the terminal cell
    rather than the reader: every Latin glyph sits on `en_adv`, every CJK glyph
    on twice that, and hosts are told so — macOS kCTFontTraitMonoSpace,
    Chromium / VS Code font pickers, most terminals' "monospace only" filter.
    A dual-width face is still a fixed grid as far as a terminal is concerned.
    (fontconfig ignores all of it and classifies by advance scan anyway.)

    A `text` face must NOT call this: strict 2:1 is a constraint for code, and
    proportional CJK punctuation is what a reading face wants instead.
    """
    font["OS/2"].xAvgCharWidth = en_adv
    font["post"].isFixedPitch = 1
    try:
        font["OS/2"].panose.bProportion = 9  # Monospaced
    except Exception:
        pass


def apply_slope(font: TTFont, slope: str, *, angle: float = 0.0) -> None:
    """Write every slope-dependent bit from one argument.

    `post.italicAngle`, OS/2 `fsSelection` ITALIC and `head.macStyle` italic all
    have to agree or hosts disagree with each other about whether the face is
    italic. Upright is written, not assumed: this build ships no italic yet, and
    the reason must stay "nobody asked for slope=italic", not "the merge cannot
    express it". Only the italic bits are touched — the bold bits belong to the
    weight, and clearing them here would undo the Latin donor's own flags.
    """
    if slope not in ("upright", "italic"):
        raise SystemExit(f"error: unknown slope {slope!r}")

    os2 = font["OS/2"]
    head = font["head"]
    if slope == "italic":
        # A negative post.italicAngle leans right, which is what a positive
        # shear angle produces.
        font["post"].italicAngle = -abs(angle)
        os2.fsSelection = (os2.fsSelection | 0x01) & ~0x40  # ITALIC, not REGULAR
        head.macStyle |= 0x02
    else:
        font["post"].italicAngle = 0.0
        os2.fsSelection &= ~0x01
        head.macStyle &= ~0x02


def set_weight_class(font: TTFont, subfamily: str) -> None:
    """Some Latin donors leave OS/2 weight flags at the Regular master's values."""
    if "OS/2" not in font:
        return
    os2 = font["OS/2"]
    if subfamily.lower() == "bold":
        os2.usWeightClass = 700
        os2.fsSelection = (os2.fsSelection | 0x20) & ~0x40
    elif subfamily.lower() == "regular":
        os2.usWeightClass = 400
        os2.fsSelection = (os2.fsSelection | 0x40) & ~0x20


# --------------------------------------------------------------------------- #
# source preparation
# --------------------------------------------------------------------------- #


def subset_coding_latin(font: TTFont) -> None:
    """Shrink a huge Latin donor so Latin + CJK fits TrueType's glyph budget."""
    from fontTools.subset import Options, Subsetter

    before = len(font.getGlyphOrder())
    cm = font.getBestCmap() or {}
    unicodes: set[int] = set()
    for a, b in CODING_LATIN_RANGES:
        for cp in range(a, b + 1):
            if cp in cm:
                unicodes.add(cp)

    options = Options()
    options.layout_features = list(CODING_LAYOUT_FEATURES)
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.notdef_outline = True
    options.recalc_bounds = True
    options.recalc_timestamp = False
    options.drop_tables = ["DSIG"]
    subsetter = Subsetter(options=options)
    subsetter.populate(unicodes=unicodes)
    subsetter.subset(font)
    if "maxp" in font:
        font["maxp"].recalc(font)
    after = len(font.getGlyphOrder())
    print(f"  subset Latin coding unicodes={len(unicodes)} glyphs {before} → {after}")


def prepare_latin(path: Path, spec: MergeSpec) -> TTFont:
    """Bring the Latin side onto the product grid.

    Three modes, because three genuinely different situations exist:

    ``none``       the Latin is already on the grid (a `latin-prepared` step ran).
    ``scale``      the donor's mono cell is known from font.toml; scale straight
                   to it. No UPM work, no measuring.
    ``normalize``  the donor needs its UPM normalised first and its cell measured
                   afterwards, because the cell that survives a UPM change is
                   whatever rounding produced.
    """
    font = TTFont(path, recalcBBoxes=True, recalcTimestamp=False)
    if spec.latin == "none":
        return font

    if spec.latin == "scale":
        src_adv = spec.latin_src_adv
        if not src_adv:
            raise SystemExit("error: [grid].latin_src_adv is required for latin = \"scale\"")
        scale = spec.en_adv / src_adv
        print(f"  scaling Latin glyphs X * {scale:.6f} -> advance {spec.en_adv}")
        print("  preserving GSUB/GPOS/GDEF (ligatures / features / marks)")
        scale_latin_font(
            font,
            scale,
            spec.en_adv,
            src_adv,
            drop_hinting_too=spec.drop_hinting_on_upem_change,
        )
        return font

    if spec.latin_subset == "coding":
        # Must happen before the CJK import — a 46k-glyph donor leaves no budget.
        subset_coding_latin(font)

    src_adv = spec.latin_src_adv or 0
    current_upm = font["head"].unitsPerEm
    target_upm = spec.latin_target_upm
    if target_upm and current_upm != target_upm:
        print(f"  scale_upem {current_upm} → {target_upm}")
        scale_upem(font, target_upm)
        if spec.drop_hinting_on_upem_change:
            drop_hinting(font)

    # Whatever the arithmetic said, the cell is what 'A' actually measures.
    cm = font.getBestCmap() or {}
    if ord("A") in cm:
        actual = font["hmtx"].metrics[cm[ord("A")]][0]
        if actual:
            src_adv = actual

    scale = spec.en_adv / src_adv if src_adv else 1.0
    print(f"  scaling Latin glyphs X * {scale:.6f} (src_adv={src_adv} → {spec.en_adv})")
    if abs(scale - 1.0) > 1e-9:
        scale_latin_font(
            font,
            scale,
            spec.en_adv,
            src_adv,
            drop_hinting_too=spec.drop_hinting_on_upem_change,
        )
    else:
        # Still map mono cells to en_adv in case of rounding drift
        hmtx = font["hmtx"].metrics
        for name in font.getGlyphOrder():
            w, lsb = hmtx[name]
            if w == src_adv:
                hmtx[name] = (spec.en_adv, lsb)
        for tag in ("hdmx", "LTSH", "VDMX"):
            if tag in font:
                del font[tag]
    return font


def prepare_cjk(path: Path, spec: MergeSpec, latin: TTFont) -> TTFont:
    font = TTFont(path, recalcBBoxes=True, recalcTimestamp=False)
    if spec.cjk == "require-same-upm":
        if latin["head"].unitsPerEm != font["head"].unitsPerEm:
            raise SystemExit(
                f"error: UPM mismatch {latin['head'].unitsPerEm} vs {font['head'].unitsPerEm}"
            )
        return font
    if spec.cjk == "normalize":
        target = spec.latin_target_upm
        if target and font["head"].unitsPerEm != target:
            print(f"  scale_upem CJK {font['head'].unitsPerEm} → {target}")
            scale_upem(font, target)
            if spec.drop_hinting_on_upem_change:
                drop_hinting(font)
    return font


def codepoints_to_import(
    spec: MergeSpec, latin_cmap: dict[int, str], cjk_cmap: dict[int, str]
) -> dict[int, str]:
    if spec.import_policy == "cjk-side":
        # The donor's own Latin is discarded: it is a different design.
        return {cp: g for cp, g in cjk_cmap.items() if is_cjk_side(cp)}
    if spec.import_policy == "cjk-side-or-missing":
        return {
            cp: g for cp, g in cjk_cmap.items() if is_cjk_side(cp) or cp not in latin_cmap
        }
    # east-asian-width: also take the donor's drawing for any W/F codepoint the
    # base happens to cover (e.g. 〈 〉) — those need a full cell and the donor
    # already draws them for one.
    return {
        cp: g
        for cp, g in cjk_cmap.items()
        if is_cjk_side(cp) or is_wide(cp) or cp not in latin_cmap
    }


# --------------------------------------------------------------------------- #
# the merge
# --------------------------------------------------------------------------- #


def _decompile_now(font: TTFont) -> None:
    for tag in ("glyf", "hmtx"):
        font.get(tag)


def merge_pair(
    latin_path: Path,
    cjk_path: Path,
    out_path: Path,
    subfamily: str,
    spec: MergeSpec,
) -> None:
    print(f"Loading {latin_path.name} + {cjk_path.name}")
    latin = prepare_latin(latin_path, spec)
    cjk = prepare_cjk(cjk_path, spec, latin)

    # Force both metric tables in before the import starts: `ensure_glyph_slot`
    # moves maxp.numGlyphs, and fontTools decompiles hmtx/glyf against whatever
    # numGlyphs says at first access — so a lazy table read after the first
    # import would be read with the wrong glyph count and fail.
    _decompile_now(latin)
    _decompile_now(cjk)

    latin_cmap = latin.getBestCmap() or {}
    cjk_cmap = cjk.getBestCmap() or {}
    to_import = codepoints_to_import(spec, latin_cmap, cjk_cmap)

    if spec.check_glyph_budget:
        projected = len(latin.getGlyphOrder()) + len(to_import)
        if projected > MAX_GLYPHS:
            raise SystemExit(
                f"error: projected {projected} glyphs exceeds the {MAX_GLYPHS} limit"
            )
        print(f"  importing {len(to_import)} codepoints (projected {projected} glyphs)")
    else:
        print(f"  importing {len(to_import)} codepoints from the CJK donor")

    rename: dict[tuple[str, int | None], str] = {}
    final_map = dict(latin_cmap)
    by_cell = spec.placement == "fit"
    glyph_set = latin.getGlyphSet() if by_cell else None
    wide = compressed = 0

    for i, (cp, src_name) in enumerate(sorted(to_import.items())):
        if by_cell:
            target = spec.cjk_adv if is_wide(cp) else spec.en_adv
            dest_name = copy_glyph_deep(
                cjk, latin, src_name, rename, prefix=spec.glyph_prefix, cell=target
            )
            compressed += fit_advance(latin, glyph_set, dest_name, target)
            wide += target == spec.cjk_adv
        else:
            dest_name = copy_glyph_deep(
                cjk, latin, src_name, rename, prefix=spec.glyph_prefix
            )
            set_cjk_metrics(latin, dest_name, spec.cjk_adv)
            wide += 1
        final_map[cp] = dest_name
        if i and i % 5000 == 0:
            print(f"    … {i}/{len(to_import)}")

    if by_cell:
        print(
            f"  advances: {wide} full-cell, {len(to_import) - wide} half-cell "
            f"(by East_Asian_Width); {compressed} outlines x-compressed to fit"
        )

    if spec.widen_wide_base_glyphs:
        widened = widen_wide_base_glyphs(latin, final_map, spec.en_adv, spec.cjk_adv)
        print(f"  {widened} base-only EAW-wide glyphs re-cast into the full cell")

    for ch in spec.required_sample:
        if ord(ch) not in final_map:
            raise SystemExit(f"error: missing required CJK sample glyph {ch}")

    rebuild_cmap(latin, final_map)
    rename_family(latin, subfamily, spec)

    apply_vertical_metrics(latin, spec.metrics)
    if spec.profile == "coding":
        declare_strict_2to1(latin, spec.en_adv)
    if spec.set_weight_class:
        set_weight_class(latin, subfamily)
    apply_slope(latin, spec.slope, angle=spec.slant_deg)

    if spec.recalc_bounds:
        glyf = latin["glyf"]
        for gname in latin.getGlyphOrder():
            g = glyf[gname]
            if g.numberOfContours != 0:
                try:
                    g.recalcBounds(glyf)
                except Exception:
                    pass

    latin["maxp"].recalc(latin)
    latin["hhea"].advanceWidthMax = max(w for w, _ in latin["hmtx"].metrics.values())
    if spec.drop_vertical_metrics:
        for tag in ("vmtx", "vhea"):
            if tag in latin:
                del latin[tag]

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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--manifest", type=Path, required=True, help="the family's font.toml")
    ap.add_argument("--latin-regular", type=Path, required=True)
    ap.add_argument("--latin-bold", type=Path, required=True)
    ap.add_argument("--cjk-regular", type=Path, required=True)
    ap.add_argument("--cjk-bold", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--profile", default="coding", choices=("coding", "text"))
    ap.add_argument("--slope", default="upright", choices=("upright", "italic"))
    args = ap.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
    except Exception as error:  # pydantic's message names the offending field
        print(f"{args.manifest}: {error}", file=sys.stderr)
        return 2

    for latin, cjk, subfamily in (
        (args.latin_regular, args.cjk_regular, "Regular"),
        (args.latin_bold, args.cjk_bold, "Bold"),
    ):
        if not latin.exists() or not cjk.exists():
            print(f"error: missing input {latin} / {cjk}", file=sys.stderr)
            return 1
        spec = spec_from_manifest(
            manifest, subfamily, profile=args.profile, slope=args.slope
        )
        merge_pair(
            latin,
            cjk,
            args.out_dir / f"{spec.family_ps}-{subfamily}.ttf",
            subfamily,
            spec,
        )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
