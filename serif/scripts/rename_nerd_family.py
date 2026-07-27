#!/usr/bin/env python3
"""Shorten Nerd-patched family names (Windows name ID 1 ≤ 31 chars).

Default family: SarasaNZSSlab NFM  (Nerd Font Mono)
Override with --family / --family-ps
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from fontTools.ttLib import TTFont


def style_from_name_table(font: TTFont) -> str:
    name = font["name"]
    for nid in (2, 17):
        rec = name.getName(nid, 3, 1, 0x409) or name.getName(nid, 1, 0, 0)
        if rec:
            return rec.toUnicode().strip()
    # fall back from filename later
    return "Regular"


def apply_names(font: TTFont, family: str, family_ps: str, style: str) -> None:
    full = f"{family} {style}".strip()
    ps = re.sub(r"[^A-Za-z0-9]", "", family_ps + style)
    typo_family = family
    typo_style = style

    # name IDs: 1 family, 2 style, 4 full, 6 postscript, 16 typo family, 17 typo style
    mapping = {
        1: family,
        2: style,
        4: full,
        6: ps,
        16: typo_family,
        17: typo_style,
    }
    name = font["name"]
    for nid, value in mapping.items():
        name.setName(value, nid, 3, 1, 0x409)  # Windows Unicode BMP
        name.setName(value, nid, 1, 0, 0)  # Mac Roman best-effort


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument("--family", default="SarasaNZSSlab NFM")
    ap.add_argument("--family-ps", default="SarasaNZSSlabNFM")
    ap.add_argument(
        "--rename-file",
        action="store_true",
        help="also rename file to {family_ps}-{style}.ttf",
    )
    args = ap.parse_args()

    for path in args.fonts:
        font = TTFont(path)
        style = style_from_name_table(font)
        # fix style if name table says Regular but file has Bold
        stem = path.stem.lower()
        if "bold" in stem and "regular" in style.lower():
            style = "Bold"
        apply_names(font, args.family, args.family_ps, style)
        out = path
        if args.rename_file:
            out = path.with_name(f"{args.family_ps}-{style}{path.suffix}")
        font.save(out)
        font.close()
        if out != path and path.exists() and out != path:
            path.unlink()
        print(f"{path.name} → family={args.family!r} style={style!r} file={out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
