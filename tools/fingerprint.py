#!/usr/bin/env python3
"""Normalised font fingerprints — the Phase 0 regression net.

Why not `sha256 out/**/*.ttf`: fontforge (the Nerd Font patcher) embeds its own
timestamps and is *not* byte-reproducible, so a raw file hash would go red on
every rebuild and teach everyone to ignore it. Instead we dump a normalised,
deterministic view of the things a build refactor can actually break, and
deliberately drop everything that carries a clock:

  excluded   head.created, head.modified, head.checkSumAdjustment, DSIG
  included   name table, per-glyph advances, cmap, GSUB/GPOS/GDEF structure,
             vertical metrics, mono flags, and a digest over glyph outlines

Two levels, because a baseline nobody can review is not a baseline:

  compact  (default, what baselines hold) — small tables in full; cmap,
           outlines and advances as counts plus digests, with per-glyph detail
           kept only for advances *off* the font's two canonical widths. These
           are dual-width fonts, so a full per-glyph advance listing is ~99.5%
           repetition of the histogram.
  full     (--full) — expands all three. Hundreds of thousands of lines per
           font; never commit it. Run it on both sides when a digest goes red
           and you need to know which codepoint or glyph moved.

Localisation does not need to live in the baseline: the build is pinned, so
`git checkout <base> && just build <family>` reproduces the old side in minutes
and `--full` on both then names the glyph.

Usage
  fingerprint.py write  <family> [--repo-root DIR] [--out DIR] [--full]
  fingerprint.py check  <family> [--repo-root DIR] [--baseline DIR] [--full]
  fingerprint.py dump   <font.ttf> [--full]

`write` is idempotent: same inputs in, byte-identical files out.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

FORMAT_VERSION = "akr-fonts fingerprint v1"

FAMILIES = [
    "casual",
    "handwriting",
    "pixel",
    "rounded",
    "sans",
    "serif",
    "typewriter",
]

FONT_SUFFIXES = (".ttf", ".otf", ".ttc")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _digest(chunks) -> str:
    h = hashlib.sha256()
    for chunk in chunks:
        h.update(chunk.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _num(value) -> str:
    """Stable rendering: ints stay ints, floats get a fixed precision."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return f"{value:.6f}"
    return str(value)


def _escape(text) -> str:
    """Keep the dump strictly text: control characters would make git treat the
    baseline as binary and refuse to diff it."""
    if text is None:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", "backslashreplace")
    out = []
    for char in str(text):
        if char == "\\":
            out.append("\\\\")
        elif char in "\t\n\r" or ord(char) < 0x20 or ord(char) == 0x7F:
            out.append(f"\\x{ord(char):02X}")
        else:
            out.append(char)
    return "".join(out)


def _attrs(obj, fields):
    for field in fields:
        if hasattr(obj, field):
            yield field, getattr(obj, field)


# --------------------------------------------------------------------------- #
# per-table dumps
# --------------------------------------------------------------------------- #

HEAD_FIELDS = [
    # created / modified / checkSumAdjustment are intentionally absent: they are
    # the whole reason this tool exists.
    "tableVersion", "fontRevision", "flags", "unitsPerEm", "xMin", "yMin",
    "xMax", "yMax", "macStyle", "lowestRecPPEM", "fontDirectionHint",
    "indexToLocFormat", "glyphDataFormat",
]

HHEA_FIELDS = [
    "ascent", "descent", "lineGap", "advanceWidthMax", "minLeftSideBearing",
    "minRightSideBearing", "xMaxExtent", "caretSlopeRise", "caretSlopeRun",
    "caretOffset", "metricDataFormat", "numberOfHMetrics",
]

OS2_FIELDS = [
    "version", "xAvgCharWidth", "usWeightClass", "usWidthClass", "fsType",
    "ySubscriptXSize", "ySubscriptYSize", "ySubscriptXOffset", "ySubscriptYOffset",
    "ySuperscriptXSize", "ySuperscriptYSize", "ySuperscriptXOffset",
    "ySuperscriptYOffset", "yStrikeoutSize", "yStrikeoutPosition",
    "sFamilyClass", "achVendID", "fsSelection", "usFirstCharIndex",
    "usLastCharIndex", "sTypoAscender", "sTypoDescender", "sTypoLineGap",
    "usWinAscent", "usWinDescent", "ulUnicodeRange1", "ulUnicodeRange2",
    "ulUnicodeRange3", "ulUnicodeRange4", "ulCodePageRange1", "ulCodePageRange2",
    "sxHeight", "sCapHeight", "usDefaultChar", "usBreakChar", "usMaxContext",
    "usLowerOpticalPointSize", "usUpperOpticalPointSize",
]

POST_FIELDS = [
    "formatType", "italicAngle", "underlinePosition", "underlineThickness",
    "isFixedPitch",
]

MAXP_FIELDS = [
    "numGlyphs", "maxPoints", "maxContours", "maxCompositePoints",
    "maxCompositeContours", "maxZones", "maxTwilightPoints", "maxStorage",
    "maxFunctionDefs", "maxInstructionDefs", "maxStackElements",
    "maxSizeOfInstructions", "maxComponentElements", "maxComponentDepth",
]


def _dump_scalar_table(font, tag, fields, lines):
    if tag not in font:
        lines.append(f"[{tag}]")
        lines.append("absent\t1")
        return
    table = font[tag]
    lines.append(f"[{tag}]")
    for field, value in _attrs(table, fields):
        if field == "panose":
            continue
        lines.append(f"{field}\t{_num(value)}")
    panose = getattr(table, "panose", None)
    if panose is not None:
        digits = [
            _num(getattr(panose, name))
            for name in sorted(vars(panose))
        ]
        lines.append("panose\t" + ",".join(digits))


def _dump_name(font, lines):
    lines.append("[name]")
    if "name" not in font:
        lines.append("absent\t1")
        return
    records = sorted(
        font["name"].names,
        key=lambda r: (r.platformID, r.platEncID, r.langID, r.nameID),
    )
    for rec in records:
        try:
            value = rec.toUnicode()
        except UnicodeDecodeError:
            value = repr(rec.string)
        lines.append(
            f"{rec.platformID}/{rec.platEncID}/0x{rec.langID:04X}/{rec.nameID}"
            f"\t{_escape(value)}"
        )


def _dump_cmap(font, lines, detail=False):
    lines.append("[cmap]")
    if "cmap" not in font:
        lines.append("absent\t1")
        return
    for sub in sorted(
        font["cmap"].tables,
        key=lambda s: (s.platformID, s.platEncID, s.format),
    ):
        mapping = sub.cmap or {}
        rows = [f"U+{cp:04X}\t{mapping[cp]}" for cp in sorted(mapping)]
        lines.append(
            f"subtable\t{sub.platformID}/{sub.platEncID}/fmt{sub.format}"
            f"\t{len(mapping)}\t{_digest(rows)}"
        )
        if detail:
            lines.extend("  " + row for row in rows)


def _dump_advances(font, lines, detail=False):
    """Advances, without 800k lines of "this glyph is 500 wide".

    These are dual-width fonts: essentially every glyph sits at one of two
    canonical widths, so a full per-glyph listing is ~99.5% repetition of what
    the histogram two lines up already states. What it costs is a baseline
    nobody can review; what it buys is glyph-name locality, and that is
    recoverable anyway — the build is pinned, so `git checkout <base> &&
    just build <family>` reproduces the old side in minutes.

    So: histogram in full, a digest per width class, the complete stream
    digested, and per-glyph detail only for glyphs *off* the canonical widths —
    which is where dual-width regressions actually show up. --full restores
    everything.
    """
    lines.append("[advances]")
    if "hmtx" not in font:
        lines.append("absent\t1")
        return

    hmtx = font["hmtx"]
    by_width = {}
    rows = []
    for name in sorted(font.getGlyphOrder()):
        width, lsb = hmtx[name]
        by_width.setdefault(width, []).append(name)
        rows.append(f"{name}\t{width}\t{lsb}")

    lines.append("distinct\t" + str(len(by_width)))
    for width in sorted(by_width):
        lines.append(f"histogram\t{width}\t{len(by_width[width])}")

    # Canonical = the two most populated widths. A fixed count rather than a
    # percentage threshold on purpose: a threshold has a cliff a build can
    # oscillate across, which would churn the baseline for no reason.
    canonical = sorted(
        by_width, key=lambda w: (-len(by_width[w]), w)
    )[:2]
    for width in sorted(canonical):
        lines.append(
            f"class\t{width}\t{len(by_width[width])}\t{_digest(by_width[width])}"
        )
    lines.append("digest\t" + _digest(rows))

    if detail:
        lines.extend("  " + row for row in rows)
        return

    # Everything off the canonical widths, named. A dual-width font should have
    # very few of these, and they are exactly the interesting ones.
    off = sorted(
        name for width, names in by_width.items()
        if width not in canonical
        for name in names
    )
    lines.append("offclass\t" + str(len(off)))
    for name in off:
        width, lsb = hmtx[name]
        lines.append(f"  {name}\t{width}\t{lsb}")


def _glyph_outline_key(font, glyf, name) -> str:
    glyph = glyf[name]
    parts = [name]
    if getattr(glyph, "isComposite", lambda: False)():
        glyph.expand(glyf)
        for comp in glyph.components:
            parts.append(
                "C:" + comp.glyphName + ":" +
                ",".join(_num(v) for v in comp.getComponentInfo()[1])
            )
    else:
        glyph.expand(glyf)
        coords, end_pts, flags = glyph.getCoordinates(glyf)
        parts.append("E:" + ",".join(str(e) for e in end_pts))
        parts.append("F:" + ",".join(str(int(f) & 0x01) for f in flags))
        parts.append("P:" + ",".join(f"{x},{y}" for x, y in coords))
    return "|".join(parts)


def _dump_outlines(font, lines, detail=False):
    lines.append("[outlines]")
    if "glyf" in font:
        glyf = font["glyf"]
        keys = []
        for name in sorted(font.getGlyphOrder()):
            try:
                keys.append((name, _glyph_outline_key(font, glyf, name)))
            except Exception as exc:  # noqa: BLE001 - a broken glyph is a finding
                keys.append((name, f"ERROR:{type(exc).__name__}"))
        lines.append("source\tglyf")
    elif "CFF " in font:
        charstrings = font["CFF "].cff[font["CFF "].cff.fontNames[0]].CharStrings
        keys = []
        for name in sorted(font.getGlyphOrder()):
            try:
                cs = charstrings[name]
                cs.decompile()
                keys.append((name, ",".join(str(t) for t in cs.program)))
            except Exception as exc:  # noqa: BLE001
                keys.append((name, f"ERROR:{type(exc).__name__}"))
        lines.append("source\tCFF ")
    else:
        lines.append("absent\t1")
        return

    per_glyph = [
        f"{name}\t{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"
        for name, key in keys
    ]
    lines.append("glyphs\t" + str(len(per_glyph)))
    lines.append("digest\t" + _digest(per_glyph))
    if detail:
        lines.extend("  " + row for row in per_glyph)


def _dump_layout(font, tag, lines):
    lines.append(f"[{tag}]")
    if tag not in font:
        lines.append("absent\t1")
        return
    table = font[tag].table
    if table is None:
        lines.append("absent\t1")
        return

    script_list = getattr(table, "ScriptList", None)
    feature_list = getattr(table, "FeatureList", None)
    features = feature_list.FeatureRecord if feature_list else []

    if script_list:
        for script in sorted(script_list.ScriptRecord, key=lambda s: s.ScriptTag):
            langs = [("dflt", script.Script.DefaultLangSys)] if script.Script.DefaultLangSys else []
            langs += [
                (r.LangSysTag, r.LangSys)
                for r in getattr(script.Script, "LangSysRecord", [])
            ]
            for lang_tag, lang_sys in sorted(langs, key=lambda p: p[0]):
                tags = sorted(
                    features[i].FeatureTag
                    for i in lang_sys.FeatureIndex
                    if i < len(features)
                )
                lines.append(
                    f"script\t{script.ScriptTag}\t{lang_tag}\t" + ",".join(tags)
                )

    lookups = getattr(table, "LookupList", None)
    lookup_types = (
        [lk.LookupType for lk in lookups.Lookup] if lookups else []
    )
    for record in sorted(features, key=lambda r: r.FeatureTag):
        indices = list(record.Feature.LookupListIndex)
        types = ",".join(
            str(lookup_types[i]) for i in indices if i < len(lookup_types)
        )
        lines.append(
            f"feature\t{record.FeatureTag}\t{len(indices)}\t{types}"
        )
    if lookups:
        lines.append(f"lookups\t{len(lookups.Lookup)}")
        counts = {}
        for lk in lookups.Lookup:
            counts[lk.LookupType] = counts.get(lk.LookupType, 0) + 1
        for lookup_type in sorted(counts):
            lines.append(f"lookuptype\t{lookup_type}\t{counts[lookup_type]}")


def _dump_gdef(font, lines):
    lines.append("[GDEF]")
    if "GDEF" not in font or font["GDEF"].table is None:
        lines.append("absent\t1")
        return
    gdef = font["GDEF"].table
    classes = getattr(gdef, "GlyphClassDef", None)
    if classes is not None and classes.classDefs:
        counts = {}
        for value in classes.classDefs.values():
            counts[value] = counts.get(value, 0) + 1
        for value in sorted(counts):
            lines.append(f"glyphclass\t{value}\t{counts[value]}")
    for attr in ("AttachList", "LigCaretList", "MarkAttachClassDef", "MarkGlyphSetsDef"):
        lines.append(f"{attr}\t{1 if getattr(gdef, attr, None) else 0}")


# --------------------------------------------------------------------------- #
# whole-font dump
# --------------------------------------------------------------------------- #

def fingerprint_font(path: Path, rel_name: str, full: bool = False) -> str:
    from fontTools.ttLib import TTFont

    font = TTFont(str(path), lazy=False, fontNumber=0)
    lines = [f"# {FORMAT_VERSION}", f"# level: {'full' if full else 'compact'}", ""]

    lines.append("[meta]")
    lines.append(f"path\t{rel_name}")
    lines.append("sfntVersion\t" + font.sfntVersion.encode("latin-1", "replace").hex())
    lines.append("tables\t" + ",".join(sorted(font.keys())))
    lines.append(f"numGlyphs\t{len(font.getGlyphOrder())}")
    # Glyph order is meaningful but a reorder would explode the diff, so it is
    # collapsed to one line. Advances and outlines below are keyed by name.
    lines.append("glyphorder\t" + _digest(font.getGlyphOrder()))

    _dump_scalar_table(font, "head", HEAD_FIELDS, lines)
    _dump_scalar_table(font, "hhea", HHEA_FIELDS, lines)
    _dump_scalar_table(font, "OS/2", OS2_FIELDS, lines)
    _dump_scalar_table(font, "post", POST_FIELDS, lines)
    _dump_scalar_table(font, "maxp", MAXP_FIELDS, lines)
    _dump_name(font, lines)
    _dump_cmap(font, lines, detail=full)
    _dump_advances(font, lines, detail=full)
    _dump_outlines(font, lines, detail=full)
    _dump_layout(font, "GSUB", lines)
    _dump_layout(font, "GPOS", lines)
    _dump_gdef(font, lines)

    font.close()
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# family level
# --------------------------------------------------------------------------- #

def find_products(repo_root: Path, family: str) -> list[Path]:
    out_dir = repo_root / family / "out"
    if not out_dir.is_dir():
        return []
    return sorted(
        p for p in out_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in FONT_SUFFIXES
    )


def slug(rel: Path) -> str:
    return str(rel).replace(os.sep, "__") + ".fp"


def _write_provenance(repo_root: Path, out_dir: Path) -> None:
    """Record where a baseline came from.

    Deliberately clock-free so it does not itself churn: a baseline regenerated
    on the same machine from the same pin produces an identical file, which is
    what keeps `write` idempotent. Whether darwin and linux agree on the
    products is an open question the first CI run answers.
    """
    import platform

    lock = repo_root / "flake.lock"
    nixpkgs_rev = "unknown"
    if lock.exists():
        import json
        try:
            nodes = json.loads(lock.read_text())["nodes"]
            nixpkgs_rev = nodes["nixpkgs"]["locked"]["rev"]
        except (KeyError, ValueError):
            pass

    (out_dir / "PROVENANCE").write_text(
        "\n".join([
            f"format\t{FORMAT_VERSION}",
            f"system\t{platform.machine()}-{platform.system().lower()}",
            f"nixpkgs\t{nixpkgs_rev}",
            "",
        ]),
        encoding="utf-8",
    )


def write_family(repo_root: Path, family: str, out_dir: Path,
                 full: bool = False) -> list[str]:
    products = find_products(repo_root, family)
    if not products:
        raise SystemExit(
            f"error: no build products under {family}/out — "
            f"run `just build {family}` first"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    # Clear stale entries so a removed product cannot linger in the baseline.
    for stale in out_dir.glob("*.fp"):
        stale.unlink()
    (out_dir / "INDEX").unlink(missing_ok=True)
    _write_provenance(repo_root, out_dir)

    index = []
    written = []
    base = repo_root / family / "out"
    for product in products:
        rel = product.relative_to(base)
        text = fingerprint_font(product, str(rel), full=full)
        target = out_dir / slug(rel)
        target.write_text(text, encoding="utf-8")
        index.append(f"{hashlib.sha256(text.encode('utf-8')).hexdigest()}  {slug(rel)}")
        written.append(str(rel))

    (out_dir / "INDEX").write_text("\n".join(index) + "\n", encoding="utf-8")
    return written


def check_family(repo_root: Path, family: str, baseline_dir: Path,
                 full: bool = False) -> int:
    if not (baseline_dir / "INDEX").exists():
        print(
            f"notice: no fingerprint baseline at {baseline_dir}. "
            f"Run `just fingerprint {family}` on a known-good build and commit it.",
            file=sys.stderr,
        )
        return 3

    tmp = Path(tempfile.mkdtemp(prefix=f"fp-{family}-"))
    try:
        write_family(repo_root, family, tmp, full=full)
        baseline_files = {p.name for p in baseline_dir.glob("*.fp")}
        current_files = {p.name for p in tmp.glob("*.fp")}

        failed = False
        for name in sorted(baseline_files - current_files):
            print(f"MISSING  {name} — product disappeared from this build")
            failed = True
        for name in sorted(current_files - baseline_files):
            print(f"NEW      {name} — product not in the baseline")
            failed = True

        for name in sorted(baseline_files & current_files):
            old = (baseline_dir / name).read_text(encoding="utf-8").splitlines()
            new = (tmp / name).read_text(encoding="utf-8").splitlines()
            if old == new:
                print(f"OK       {name}")
                continue
            failed = True
            print(f"CHANGED  {name}")
            diff = list(difflib.unified_diff(
                old, new, fromfile=f"baseline/{name}", tofile=f"current/{name}",
                lineterm="", n=1,
            ))
            for line in diff[:200]:
                print("    " + line)
            if len(diff) > 200:
                print(f"    … {len(diff) - 200} more diff lines suppressed")

        return 1 if failed else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo-root",
        default=os.environ.get("FONTKIT_REPO_ROOT", str(Path(__file__).resolve().parent.parent)),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    full_help = (
        "expand the per-codepoint cmap and per-glyph outline sections. "
        "Not for committed baselines (megabytes per font) — use it on both "
        "sides when a digest goes red and you need to localise the change."
    )

    p_write = sub.add_parser("write", help="write/update a family's baseline")
    p_write.add_argument("family", choices=FAMILIES)
    p_write.add_argument("--out")
    p_write.add_argument("--full", action="store_true", help=full_help)

    p_check = sub.add_parser("check", help="compare a family against its baseline")
    p_check.add_argument("family", choices=FAMILIES)
    p_check.add_argument("--baseline")
    p_check.add_argument("--full", action="store_true", help=full_help)

    p_dump = sub.add_parser("dump", help="print one font's fingerprint to stdout")
    p_dump.add_argument("font")
    p_dump.add_argument("--full", action="store_true", help=full_help)

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    if args.command == "dump":
        path = Path(args.font)
        sys.stdout.write(fingerprint_font(path, path.name, full=args.full))
        return 0

    default_dir = repo_root / "fingerprints" / args.family

    if args.command == "write":
        out_dir = Path(args.out) if args.out else default_dir
        written = write_family(repo_root, args.family, out_dir, full=args.full)
        print(f"wrote {len(written)} fingerprint(s) to {out_dir}")
        for name in written:
            print(f"  {name}")
        return 0

    baseline = Path(args.baseline) if args.baseline else default_dir
    return check_family(repo_root, args.family, baseline, full=args.full)


if __name__ == "__main__":
    sys.exit(main())
