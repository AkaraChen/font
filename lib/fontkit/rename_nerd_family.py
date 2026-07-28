#!/usr/bin/env python3
"""Shorten Nerd-patched family names (Windows name ID 1 ≤ 31 chars).

Run as: python3 -m fontkit.rename_nerd_family --family 'X NFM' --family-ps XNFM \
            [--rename-file] FONT.ttf [...]

--family / --family-ps are required. The per-family copies of this script each
carried their own product name as a *default*, which is exactly the kind of
drift that made four copies of one file necessary; every build step already
passes both explicitly.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from fontTools.ttLib import TTFont


def style_from_name_table(font: TTFont) -> str:
    name = font["name"]
    for nid in (2, 17):
        rec = name.getName(nid, 3, 1, 0x409) or name.getName(nid, 1, 0, 0)
        if rec:
            return rec.toUnicode().strip()
    return "Regular"


def apply_names(font: TTFont, family: str, family_ps: str, style: str) -> None:
    full = f"{family} {style}".strip()
    ps = re.sub(r"[^A-Za-z0-9]", "", family_ps + style)
    name = font["name"]
    for nid, value in {
        1: family,
        2: style,
        4: full,
        6: ps,
        16: family,
        17: style,
    }.items():
        name.setName(value, nid, 3, 1, 0x409)
        name.setName(value, nid, 1, 0, 0)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument("--family", required=True, help="e.g. 'LilexSansSC NFM'")
    ap.add_argument("--family-ps", required=True, help="e.g. 'LilexSansSCNFM'")
    ap.add_argument(
        "--rename-file",
        action="store_true",
        help="also rename the file to {family_ps}-{style}{suffix}",
    )
    args = ap.parse_args(argv)

    for path in args.fonts:
        font = TTFont(path)
        style = style_from_name_table(font)
        # The name table says "Regular" on some Bold products; trust the filename.
        stem = path.stem.lower()
        if "bold" in stem and "regular" in style.lower():
            style = "Bold"
        apply_names(font, args.family, args.family_ps, style)
        out = path
        if args.rename_file:
            out = path.with_name(f"{args.family_ps}-{style}{path.suffix}")
        font.save(out)
        font.close()
        if out != path and path.exists():
            path.unlink()
        print(f"{path.name} → family={args.family!r} style={style!r} file={out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
