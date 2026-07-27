#!/usr/bin/env python3
"""Expand default `calt` so more programming ligatures are on without extra OT features.

Iosevka (and therefore Sarasa MonoSlab Latin) ships a slim default `calt` set and
parks richer ligations under `dlig` (discretionary) and language packs
(`JSPT`, `HSKL`, …). Editors enable `calt` by default when “font ligatures” is
on, but almost never enable `dlig` or the private language tags.

This script unions the lookup indices of selected source features into every
`calt` feature record, so the discretionary set (and optional extras) apply
under the default path. Source features are left intact for apps that still
toggle them explicitly.

Default sources: `dlig` only (safe superset of double chaining ++/--/##/~~,
counter-arrows, logic /\\ \\/, brace/brack bars, markdown checkboxes, …).

Examples:
  python3 expand-default-ligatures.py out/nerd/*.ttf
  python3 expand-default-ligatures.py --include dlig,JSPT font.ttf
  python3 expand-default-ligatures.py --include all --dry-run font.ttf
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from fontTools.ttLib import TTFont
except ImportError:
    print("error: fontTools is required (pip install fonttools)", file=sys.stderr)
    sys.exit(2)

# Iosevka private ligation-set tags (see Iosevka params/ligation-set.toml).
# Excludes non-ligation private tags NWID/WWID and stylistic APLF/MOSC/THND.
LANG_LIG_TAGS = (
    "CLIK",
    "COQX",
    "DFNY",
    "ELMX",
    "ERLA",
    "FSHP",
    "FSTA",
    "HSKL",
    "IDRS",
    "JLIA",
    "JSPT",
    "MLXX",
    "MTLB",
    "PHPX",
    "PURS",
    "RAKU",
    "SWFT",
    "VRLG",
    "WFLM",
)

DEFAULT_SOURCES = ("dlig",)


def _parse_include(raw: str) -> list[str]:
    parts = [p.strip() for p in raw.replace(" ", "").split(",") if p.strip()]
    if not parts:
        return list(DEFAULT_SOURCES)
    out: list[str] = []
    for p in parts:
        low = p.lower()
        if low == "all":
            for t in ("dlig", *LANG_LIG_TAGS):
                if t not in out:
                    out.append(t)
            continue
        tag = "dlig" if low == "dlig" else p.upper()
        if tag not in out:
            out.append(tag)
    return out


def _feature_lookup_lists(gsub, tag: str) -> list[list[int]]:
    """Return LookupListIndex arrays for every feature record with this tag."""
    found: list[list[int]] = []
    if not gsub or not gsub.FeatureList:
        return found
    for fr in gsub.FeatureList.FeatureRecord:
        if fr.FeatureTag != tag:
            continue
        idxs = list(fr.Feature.LookupListIndex or [])
        found.append(idxs)
    return found


def expand_calt(font: TTFont, sources: list[str]) -> dict:
    """Mutate font GSUB: append unique source lookups onto every calt feature.

    Returns a small report dict for logging.
    """
    if "GSUB" not in font:
        return {"ok": False, "reason": "no GSUB"}

    gsub = font["GSUB"].table
    calt_lists = []
    if not gsub.FeatureList:
        return {"ok": False, "reason": "empty FeatureList"}

    calt_records = [
        fr for fr in gsub.FeatureList.FeatureRecord if fr.FeatureTag == "calt"
    ]
    if not calt_records:
        return {"ok": False, "reason": "no calt feature"}

    source_lookups: list[int] = []
    source_report: dict[str, int] = {}
    missing_sources: list[str] = []
    for tag in sources:
        lists = _feature_lookup_lists(gsub, tag)
        if not lists:
            missing_sources.append(tag)
            source_report[tag] = 0
            continue
        # Prefer the richest record if several share the tag.
        best = max(lists, key=len)
        source_report[tag] = len(best)
        for li in best:
            if li not in source_lookups:
                source_lookups.append(li)

    before_counts: list[int] = []
    after_counts: list[int] = []
    added_total = 0
    for fr in calt_records:
        existing = list(fr.Feature.LookupListIndex or [])
        before_counts.append(len(existing))
        seen = set(existing)
        added = 0
        for li in source_lookups:
            if li not in seen:
                existing.append(li)
                seen.add(li)
                added += 1
        fr.Feature.LookupListIndex = existing
        after_counts.append(len(existing))
        added_total += added

    return {
        "ok": True,
        "calt_records": len(calt_records),
        "before": before_counts,
        "after": after_counts,
        "added": added_total,
        "source_report": source_report,
        "missing_sources": missing_sources,
        "union_lookups": len(source_lookups),
    }


def process_path(path: Path, sources: list[str], dry_run: bool) -> int:
    font = TTFont(path)
    report = expand_calt(font, sources)
    if not report.get("ok"):
        print(f"error: {path}: {report.get('reason')}", file=sys.stderr)
        return 1

    src_bits = ", ".join(
        f"{t}={n}" for t, n in report["source_report"].items()
    )
    print(
        f"{path.name}: calt "
        f"{report['before']} → {report['after']} "
        f"(+{report['added']} lookup refs; sources [{src_bits}]; "
        f"union={report['union_lookups']})"
    )
    if report["missing_sources"]:
        print(
            f"  warning: missing source features: "
            f"{', '.join(report['missing_sources'])}",
            file=sys.stderr,
        )

    if dry_run:
        return 0
    if report["added"] == 0:
        print(f"  unchanged (already expanded)")
        return 0
    font.save(path)
    print(f"  saved {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "fonts",
        nargs="+",
        type=Path,
        help="TTF/OTF paths to expand in place",
    )
    ap.add_argument(
        "--include",
        default="dlig",
        help=(
            "Comma-separated source feature tags to union into calt. "
            "Use 'dlig' (default), language tags like JSPT/HSKL, or 'all'."
        ),
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing",
    )
    args = ap.parse_args(argv)

    sources = _parse_include(args.include)
    if not sources:
        print("error: empty --include", file=sys.stderr)
        return 2

    rc = 0
    for path in args.fonts:
        if not path.is_file():
            print(f"error: not a file: {path}", file=sys.stderr)
            rc = 1
            continue
        try:
            rc = process_path(path, sources, args.dry_run) or rc
        except Exception as exc:  # noqa: BLE001 — CLI boundary
            print(f"error: {path}: {exc}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
