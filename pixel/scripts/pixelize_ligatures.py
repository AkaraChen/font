#!/usr/bin/env python3
"""Pixelize programming ligatures from a donor font into a Fusion-style pixel mono.

Takes:
  - base: Fusion Pixel 12px monospaced TTF (no calt)
  - donor: Lilex (or similar) with `.liga` glyphs

Does:
  1. Parse donor `*.liga` glyph names into character sequences
  2. Rasterize each liga outline onto a 12px-tall, N×6px-wide grid
     (N = component count; advance = N × half-cell so columns stay stable)
  3. Convert on-pixels to square contours (1px = px_unit font units)
  4. Inject glyphs + a GSUB `calt` ligature lookup into the base font
  5. Optionally synthesize a few common sequences missing from the donor
     (`=>`, `->`, `<-`, `<=>`) from donor component outlines

Nerd Font glyphs are NOT handled here — patch them afterwards without pixelization.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from fontTools.pens.basePen import BasePen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables as ot
from PIL import Image, ImageDraw

# Adobe glyph name → single character (for parsing foo_bar.liga)
STD_NAME_TO_CHAR: dict[str, str] = {
    "hyphen": "-",
    "equal": "=",
    "greater": ">",
    "less": "<",
    "exclam": "!",
    "question": "?",
    "colon": ":",
    "semicolon": ";",
    "period": ".",
    "comma": ",",
    "plus": "+",
    "asterisk": "*",
    "slash": "/",
    "backslash": "\\",
    "bar": "|",
    "ampersand": "&",
    "percent": "%",
    "numbersign": "#",
    "at": "@",
    "dollar": "$",
    "asciitilde": "~",
    "asciicircum": "^",
    "underscore": "_",
    "parenleft": "(",
    "parenright": ")",
    "bracketleft": "[",
    "bracketright": "]",
    "braceleft": "{",
    "braceright": "}",
}

# Extra sequences not present as a single donor .liga (synthesized).
# Values: list of donor glyph names to draw left-to-right in equal slices,
# or a single donor glyph name to stretch across N cells.
SYNTHETIC: dict[str, list[str]] = {
    "=>": ["equal", "greater"],
    "->": ["hyphen", "greater"],
    "<-": ["less", "hyphen"],
    "<=>": ["less", "equal", "greater"],
    "<!--": ["less", "exclam", "hyphen", "hyphen"],
}


class PolyPen(BasePen):
    """Collect approximate polygons from a glyph outline."""

    def __init__(self, glyph_set):
        super().__init__(glyph_set)
        self.polys: list[list[tuple[float, float]]] = []
        self._cur: list[tuple[float, float]] = []

    def _moveTo(self, p0):
        self._cur = [p0]

    def _lineTo(self, p1):
        self._cur.append(p1)

    def _curveToOne(self, p1, p2, p3):
        # sample cubic for raster fill
        if not self._cur:
            self._cur = [p1]
        p0 = self._cur[-1]
        for i in range(1, 9):
            t = i / 8.0
            u = 1.0 - t
            x = (
                u**3 * p0[0]
                + 3 * u**2 * t * p1[0]
                + 3 * u * t**2 * p2[0]
                + t**3 * p3[0]
            )
            y = (
                u**3 * p0[1]
                + 3 * u**2 * t * p1[1]
                + 3 * u * t**2 * p2[1]
                + t**3 * p3[1]
            )
            self._cur.append((x, y))

    def _qCurveToOne(self, p1, p2):
        if not self._cur:
            self._cur = [p1]
        p0 = self._cur[-1]
        for i in range(1, 7):
            t = i / 6.0
            u = 1.0 - t
            x = u**2 * p0[0] + 2 * u * t * p1[0] + t**2 * p2[0]
            y = u**2 * p0[1] + 2 * u * t * p1[1] + t**2 * p2[1]
            self._cur.append((x, y))

    def _closePath(self):
        if len(self._cur) >= 3:
            self.polys.append(self._cur)
        self._cur = []

    def _endPath(self):
        self._closePath()


def parse_liga_name(gname: str) -> str | None:
    """`equal_equal.liga` → `==`. Returns None if unparseable / variant."""
    if not gname.endswith(".liga"):
        return None
    if any(tag in gname for tag in (".ss", ".cv", ".cn", ".locl")):
        return None
    body = gname[: -len(".liga")]
    parts = body.split("_")
    chars: list[str] = []
    for p in parts:
        if p not in STD_NAME_TO_CHAR:
            return None
        chars.append(STD_NAME_TO_CHAR[p])
    if len(chars) < 2:
        return None
    return "".join(chars)


def rasterize_polys(
    polys: list[list[tuple[float, float]]],
    *,
    w_px: int,
    h_px: int,
    x_scale: float,
    y0_src: float,
    y1_src: float,
    y0_dst: float,
    y1_dst: float,
    px_unit: int,
    threshold: float = 0.38,
    supersample: int = 8,
) -> list[list[int]]:
    """Rasterize source-unit polygons into a binary grid (row 0 = top)."""
    ss = supersample
    W, H = w_px * ss, h_px * ss
    img = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(img)

    def map_pt(x: float, y: float) -> tuple[float, float]:
        xf = x * x_scale
        if y1_src != y0_src:
            t = (y - y0_src) / (y1_src - y0_src)
        else:
            t = 0.0
        yf = y0_dst + t * (y1_dst - y0_dst)
        ix = xf / px_unit * ss
        iy = (y1_dst - yf) / px_unit * ss
        return (ix, iy)

    for poly in polys:
        if len(poly) < 3:
            continue
        pts = [map_pt(x, y) for x, y in poly]
        try:
            draw.polygon(pts, fill=255)
        except Exception:
            continue

    small = img.resize((w_px, h_px), Image.Resampling.BOX)
    return [
        [1 if small.getpixel((x, y)) > 255 * threshold else 0 for x in range(w_px)]
        for y in range(h_px)
    ]


def glyph_polys(font: TTFont, gname: str) -> list[list[tuple[float, float]]]:
    gs = font.getGlyphSet()
    if gname not in gs:
        return []
    pen = PolyPen(gs)
    gs[gname].draw(pen)
    return pen.polys


def bitmap_to_ttglyph(grid: list[list[int]], *, px_unit: int, y_top: int) -> object:
    """Each on-pixel → axis-aligned square contour."""
    pen = TTGlyphPen(None)
    h = len(grid)
    w = len(grid[0]) if h else 0
    for row in range(h):
        for col in range(w):
            if not grid[row][col]:
                continue
            x0 = col * px_unit
            y1 = y_top - row * px_unit
            y0 = y1 - px_unit
            pen.moveTo((x0, y0))
            pen.lineTo((x0, y1))
            pen.lineTo((x0 + px_unit, y1))
            pen.lineTo((x0 + px_unit, y0))
            pen.closePath()
    return pen.glyph()


def set_family_names(font: TTFont, family: str, family_ps: str, style: str = "Regular") -> None:
    full = f"{family} {style}".strip()
    ps = "".join(c for c in (family_ps + style) if c.isalnum())
    name = font["name"]
    mapping = {
        1: family,
        2: style,
        4: full,
        6: ps,
        16: family,
        17: style,
    }
    for nid, value in mapping.items():
        name.setName(value, nid, 3, 1, 0x409)
        try:
            name.setName(value, nid, 1, 0, 0)
        except Exception:
            pass


def collect_donor_ligas(donor: TTFont) -> dict[str, str]:
    """sequence → donor glyph name (prefer plain .liga)."""
    out: dict[str, str] = {}
    for g in donor.getGlyphOrder():
        seq = parse_liga_name(g)
        if seq is None:
            continue
        # first wins; plain names come before .ss/.cv because we filter those out
        out.setdefault(seq, g)
    return out


def synthesize_grid(
    donor: TTFont,
    components: list[str],
    *,
    half: int,
    px_unit: int,
    pixel_h: int,
    ascent: int,
    descent: int,
) -> list[list[int]]:
    """Draw component glyphs side-by-side then pixelize (for missing sequences)."""
    n = len(components)
    w_px = (half // px_unit) * n
    h_px = pixel_h
    # Build a combined polygon list in a synthetic coordinate space:
    # each component drawn in its cell [i*half, (i+1)*half)
    polys: list[list[tuple[float, float]]] = []
    y0 = donor["hhea"].descent
    y1 = donor["hhea"].ascent
    for i, gname in enumerate(components):
        if gname not in donor.getGlyphSet():
            continue
        cell_polys = glyph_polys(donor, gname)
        adv = donor["hmtx"].metrics.get(gname, (half, 0))[0] or half
        # scale component into one half-cell width, then offset
        x_scale = half / adv if adv else 1.0
        x_off = i * half
        for poly in cell_polys:
            polys.append([(x * x_scale + x_off, y) for x, y in poly])
    return rasterize_polys(
        polys,
        w_px=w_px,
        h_px=h_px,
        x_scale=1.0,  # already in target x units (half-cell space ≈ fusion)
        y0_src=y0,
        y1_src=y1,
        y0_dst=descent,
        y1_dst=ascent,
        px_unit=px_unit,
    )


def donor_liga_grid(
    donor: TTFont,
    gname: str,
    n_cells: int,
    *,
    half: int,
    px_unit: int,
    pixel_h: int,
    ascent: int,
    descent: int,
) -> list[list[int]]:
    """Pixelize a donor .liga glyph stretched across n_cells half-cells."""
    donor_adv = donor["hmtx"].metrics.get(gname, (half, 0))[0] or half
    target_adv = half * n_cells
    x_scale = target_adv / donor_adv if donor_adv else float(n_cells)
    y0 = donor["hhea"].descent
    y1 = donor["hhea"].ascent
    w_px = (half // px_unit) * n_cells
    polys = glyph_polys(donor, gname)
    return rasterize_polys(
        polys,
        w_px=w_px,
        h_px=pixel_h,
        x_scale=x_scale,
        y0_src=y0,
        y1_src=y1,
        y0_dst=descent,
        y1_dst=ascent,
        px_unit=px_unit,
    )


def ensure_glyph_order(font: TTFont, names: list[str]) -> None:
    order = font.getGlyphOrder()
    existing = set(order)
    for n in names:
        if n not in existing:
            order.append(n)
            existing.add(n)
    font.setGlyphOrder(order)
    font["maxp"].numGlyphs = len(order)


def add_empty_glyph_tables(font: TTFont, gname: str, advance: int) -> None:
    """Prepare hmtx slot; glyf filled by caller."""
    font["hmtx"].metrics[gname] = (advance, 0)


def build_calt_liga_gsub(
    font: TTFont,
    rules: list[tuple[list[str], str]],
) -> None:
    """Install (or replace) a simple GSUB with one `calt` ligature lookup.

    rules: list of (component_glyph_names, liga_glyph_name)
    Longer sequences first is recommended by caller.
    """
    # Group by first glyph
    by_first: dict[str, list[tuple[list[str], str]]] = defaultdict(list)
    for comps, liga in rules:
        if len(comps) < 2:
            continue
        by_first[comps[0]].append((comps[1:], liga))

    # Build LigatureSubst
    liga_subst = ot.LigatureSubst()
    liga_subst.ligatures = {}
    for first, items in by_first.items():
        # longer component tails first
        items.sort(key=lambda it: len(it[0]), reverse=True)
        ligs = []
        for tail, liga_name in items:
            lig = ot.Ligature()
            lig.Component = list(tail)
            lig.LigGlyph = liga_name
            ligs.append(lig)
        liga_subst.ligatures[first] = ligs

    lookup = ot.Lookup()
    lookup.LookupType = 4
    lookup.LookupFlag = 0
    lookup.SubTable = [liga_subst]
    lookup.SubTableCount = 1

    lookup_list = ot.LookupList()
    lookup_list.Lookup = [lookup]
    lookup_list.LookupCount = 1

    feature = ot.Feature()
    feature.FeatureParams = None
    feature.LookupListIndex = [0]
    feature.LookupCount = 1

    feature_record = ot.FeatureRecord()
    feature_record.FeatureTag = "calt"
    feature_record.Feature = feature

    feature_list = ot.FeatureList()
    feature_list.FeatureRecord = [feature_record]
    feature_list.FeatureCount = 1

    # Default LangSys → calt
    langsys = ot.DefaultLangSys()
    langsys.ReqFeatureIndex = 0xFFFF
    langsys.FeatureIndex = [0]
    langsys.FeatureCount = 1
    langsys.LookupOrder = None

    script = ot.Script()
    script.DefaultLangSys = langsys
    script.LangSysRecord = []
    script.LangSysCount = 0

    script_record = ot.ScriptRecord()
    script_record.ScriptTag = "DFLT"
    script_record.Script = script

    # Also wire latn (editors often look there)
    script_latn = ot.Script()
    script_latn.DefaultLangSys = langsys
    script_latn.LangSysRecord = []
    script_latn.LangSysCount = 0
    script_record_latn = ot.ScriptRecord()
    script_record_latn.ScriptTag = "latn"
    script_record_latn.Script = script_latn

    script_list = ot.ScriptList()
    script_list.ScriptRecord = [script_record, script_record_latn]
    script_list.ScriptCount = 2

    gsub = ot.GSUB()
    gsub.Version = 0x00010000
    gsub.ScriptList = script_list
    gsub.FeatureList = feature_list
    gsub.LookupList = lookup_list

    table = newTable("GSUB")
    table.table = gsub
    font["GSUB"] = table


def process(
    base_path: Path,
    donor_path: Path,
    out_path: Path,
    *,
    family: str,
    family_ps: str,
    half: int,
    px_unit: int,
    pixel_h: int,
    ascent: int,
    descent: int,
) -> dict:
    base = TTFont(base_path)
    donor = TTFont(donor_path)

    cmap = base.getBestCmap() or {}
    # codepoint → base glyph name
    def gname_for_char(ch: str) -> str | None:
        return cmap.get(ord(ch))

    donor_ligas = collect_donor_ligas(donor)
    # Merge synthetic only when not already covered
    sequences: dict[str, tuple[str, str | None]] = {}
    # value: ("donor", gname) | ("synth", None)
    for seq, gname in donor_ligas.items():
        sequences[seq] = ("donor", gname)
    for seq in SYNTHETIC:
        sequences.setdefault(seq, ("synth", None))

    # Sort longer first for GSUB
    ordered_seqs = sorted(sequences.keys(), key=len, reverse=True)

    new_glyph_names: list[str] = []
    rules: list[tuple[list[str], str]] = []
    skipped: list[str] = []
    built = 0

    glyf = base["glyf"]
    hmtx = base["hmtx"]

    for seq in ordered_seqs:
        kind, donor_g = sequences[seq]
        # resolve base component glyph names
        comp_names: list[str] = []
        ok = True
        for ch in seq:
            gn = gname_for_char(ch)
            if not gn:
                ok = False
                break
            comp_names.append(gn)
        if not ok or len(comp_names) < 2:
            skipped.append(seq)
            continue

        n_cells = len(seq)
        advance = half * n_cells
        liga_name = "liga_" + "_".join(f"u{ord(c):04X}" for c in seq)

        if kind == "donor" and donor_g:
            grid = donor_liga_grid(
                donor,
                donor_g,
                n_cells,
                half=half,
                px_unit=px_unit,
                pixel_h=pixel_h,
                ascent=ascent,
                descent=descent,
            )
        else:
            components = SYNTHETIC[seq]
            grid = synthesize_grid(
                donor,
                components,
                half=half,
                px_unit=px_unit,
                pixel_h=pixel_h,
                ascent=ascent,
                descent=descent,
            )

        on = sum(sum(r) for r in grid)
        if on == 0:
            skipped.append(seq + "(empty)")
            continue

        ttg = bitmap_to_ttglyph(grid, px_unit=px_unit, y_top=ascent)
        # install
        if liga_name not in hmtx.metrics:
            new_glyph_names.append(liga_name)
        hmtx.metrics[liga_name] = (advance, 0)
        glyf[liga_name] = ttg
        # bounds
        if hasattr(ttg, "recalcBounds"):
            ttg.recalcBounds(glyf)

        rules.append((comp_names, liga_name))
        built += 1

    ensure_glyph_order(base, new_glyph_names)
    build_calt_liga_gsub(base, rules)
    set_family_names(base, family, family_ps, "Regular")

    # Dual-width 2:1 is still a fixed grid — advertise as mono for host pickers.
    base["post"].isFixedPitch = 1
    try:
        panose = base["OS/2"].panose
        if panose.bFamilyType == 2:
            panose.bProportion = 9
        base["OS/2"].xAvgCharWidth = half
    except Exception:
        pass

    try:
        base["name"].setName(
            f"{family}: Fusion Pixel 12px mono + pixelized programming ligatures",
            10,
            3,
            1,
            0x409,
        )
    except Exception:
        pass

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(out_path)
    base.close()
    donor.close()

    return {
        "built": built,
        "rules": len(rules),
        "skipped": skipped,
        "out": str(out_path),
        "sequences": [
            s for s in ordered_seqs if s not in skipped and not s.endswith("(empty)")
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--donor", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--family", default="FusionPixel12 Mono")
    ap.add_argument("--family-ps", default="FusionPixel12Mono")
    ap.add_argument("--half", type=int, default=600)
    ap.add_argument("--px", type=int, default=100)
    ap.add_argument("--pixel-h", type=int, default=12)
    ap.add_argument("--ascent", type=int, default=1000)
    ap.add_argument("--descent", type=int, default=-200)
    args = ap.parse_args()

    report = process(
        args.base,
        args.donor,
        args.out,
        family=args.family,
        family_ps=args.family_ps,
        half=args.half,
        px_unit=args.px,
        pixel_h=args.pixel_h,
        ascent=args.ascent,
        descent=args.descent,
    )
    print(
        f"pixelize_ligatures: built={report['built']} "
        f"skipped={len(report['skipped'])} → {report['out']}"
    )
    if report["sequences"]:
        sample = " ".join(repr(s) for s in report["sequences"][:12])
        print(f"  sample sequences: {sample} …")
    if report["skipped"]:
        print(f"  skipped ({len(report['skipped'])}): {report['skipped'][:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
