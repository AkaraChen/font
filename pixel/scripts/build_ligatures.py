#!/usr/bin/env python3
"""Install hand-drawn pixel ligatures into Fusion Pixel 12px mono.

Reads `ligatures/ligatures.txt` — ASCII art drawn by hand on the 12-row Fusion
grid — turns each on-pixel into a square contour, and wires the results up as a
GSUB `calt` ligature lookup.

There is no donor font and no rasterization: what is in the art file is exactly
what ships. A ligature that looks wrong is fixed by editing its picture.

Nerd Font glyphs are patched afterwards and are not touched here.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables as ot

PIXEL_ROWS = 12
COLS_PER_CELL = 6


class ArtError(Exception):
    """The art file is malformed. Always fatal — these drawings are hand-authored."""


def parse_art(path: Path) -> list[tuple[str, list[list[int]]]]:
    """Parse the hand-drawn art file into (sequence, grid) pairs, in file order."""
    entries: list[tuple[str, list[list[int]]]] = []
    seen: set[str] = set()

    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("@"):
            i += 1
            continue

        header_lineno = i + 1
        seq = line[1:].strip()
        if len(seq) < 2:
            raise ArtError(
                f"{path}:{header_lineno}: sequence {seq!r} must be at least 2 characters"
            )
        if seq in seen:
            raise ArtError(f"{path}:{header_lineno}: duplicate sequence {seq!r}")
        seen.add(seq)

        width = COLS_PER_CELL * len(seq)
        rows: list[list[int]] = []
        i += 1
        while len(rows) < PIXEL_ROWS:
            if i >= len(lines):
                raise ArtError(
                    f"{path}:{header_lineno}: {seq!r} ended after {len(rows)} rows, "
                    f"need {PIXEL_ROWS}"
                )
            raw = lines[i]
            i += 1
            if not raw.strip():
                raise ArtError(
                    f"{path}:{i}: blank line inside {seq!r} art (row {len(rows)})"
                )
            if len(raw) != width:
                raise ArtError(
                    f"{path}:{i}: {seq!r} row {len(rows)} is {len(raw)} columns, "
                    f"need exactly {width} ({len(seq)} cells x {COLS_PER_CELL})"
                )
            bad = set(raw) - {"#", "."}
            if bad:
                raise ArtError(
                    f"{path}:{i}: {seq!r} row {len(rows)} has illegal characters "
                    f"{sorted(bad)}; only '#' and '.' are allowed"
                )
            rows.append([1 if c == "#" else 0 for c in raw])

        if not any(any(r) for r in rows):
            raise ArtError(f"{path}:{header_lineno}: {seq!r} is blank")
        entries.append((seq, rows))

    if not entries:
        raise ArtError(f"{path}: no ligatures found")
    return entries


def liga_glyph_name(seq: str) -> str:
    return "liga_" + "_".join(f"u{ord(c):04X}" for c in seq)


def bitmap_to_ttglyph(grid: list[list[int]], *, px_unit: int, y_top: int):
    """Each on-pixel becomes one axis-aligned square contour."""
    pen = TTGlyphPen(None)
    for row, cells in enumerate(grid):
        for col, on in enumerate(cells):
            if not on:
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
    mapping = {1: family, 2: style, 4: full, 6: ps, 16: family, 17: style}
    for nid, value in mapping.items():
        name.setName(value, nid, 3, 1, 0x409)
        try:
            name.setName(value, nid, 1, 0, 0)
        except Exception:
            pass


def ensure_glyph_order(font: TTFont, names: list[str]) -> None:
    order = font.getGlyphOrder()
    existing = set(order)
    for n in names:
        if n not in existing:
            order.append(n)
            existing.add(n)
    font.setGlyphOrder(order)
    font["maxp"].numGlyphs = len(order)


def build_calt_liga_gsub(font: TTFont, rules: list[tuple[list[str], str]]) -> None:
    """Install a GSUB with one `calt` type-4 ligature lookup.

    Within each first-glyph bucket, longer component tails are listed first so
    `<!--` wins over `<--` wins over `<-`.
    """
    by_first: dict[str, list[tuple[list[str], str]]] = defaultdict(list)
    for comps, liga in rules:
        by_first[comps[0]].append((comps[1:], liga))

    liga_subst = ot.LigatureSubst()
    liga_subst.ligatures = {}
    for first, items in by_first.items():
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

    langsys = ot.DefaultLangSys()
    langsys.ReqFeatureIndex = 0xFFFF
    langsys.FeatureIndex = [0]
    langsys.FeatureCount = 1
    langsys.LookupOrder = None

    script_records = []
    for tag in ("DFLT", "latn"):
        script = ot.Script()
        script.DefaultLangSys = langsys
        script.LangSysRecord = []
        script.LangSysCount = 0
        rec = ot.ScriptRecord()
        rec.ScriptTag = tag
        rec.Script = script
        script_records.append(rec)

    script_list = ot.ScriptList()
    script_list.ScriptRecord = script_records
    script_list.ScriptCount = len(script_records)

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
    art_path: Path,
    out_path: Path,
    *,
    family: str,
    family_ps: str,
    half: int,
    px_unit: int,
    ascent: int,
) -> dict:
    entries = parse_art(art_path)
    base = TTFont(base_path)
    cmap = base.getBestCmap() or {}
    glyf = base["glyf"]
    hmtx = base["hmtx"]

    new_names: list[str] = []
    rules: list[tuple[list[str], str]] = []

    for seq, grid in entries:
        comps: list[str] = []
        for ch in seq:
            gn = cmap.get(ord(ch))
            if not gn:
                raise ArtError(
                    f"{art_path}: sequence {seq!r} needs {ch!r} (U+{ord(ch):04X}), "
                    f"which the base font does not map"
                )
            comps.append(gn)

        name = liga_glyph_name(seq)
        ttg = bitmap_to_ttglyph(grid, px_unit=px_unit, y_top=ascent)
        if name not in hmtx.metrics:
            new_names.append(name)
        hmtx.metrics[name] = (half * len(seq), 0)
        glyf[name] = ttg
        ttg.recalcBounds(glyf)
        rules.append((comps, name))

    ensure_glyph_order(base, new_names)
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
            f"{family}: Fusion Pixel 12px mono + hand-drawn programming ligatures",
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

    by_width: dict[int, list[str]] = defaultdict(list)
    for seq, _ in entries:
        by_width[len(seq)].append(seq)
    return {"count": len(entries), "by_width": dict(by_width), "out": str(out_path)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--art", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--family", default="AKR Pixel SC Dual")
    ap.add_argument("--family-ps", default="AKRPixelSCDual")
    ap.add_argument("--half", type=int, default=600)
    ap.add_argument("--px", type=int, default=100)
    ap.add_argument("--ascent", type=int, default=1000)
    args = ap.parse_args()

    try:
        report = process(
            args.base,
            args.art,
            args.out,
            family=args.family,
            family_ps=args.family_ps,
            half=args.half,
            px_unit=args.px,
            ascent=args.ascent,
        )
    except ArtError as exc:
        print(f"build_ligatures: {exc}", file=sys.stderr)
        return 1

    print(f"build_ligatures: {report['count']} hand-drawn ligatures → {report['out']}")
    for width in sorted(report["by_width"]):
        seqs = report["by_width"][width]
        print(f"  {width}-cell ({len(seqs)}): {' '.join(seqs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
