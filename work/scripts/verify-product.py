#!/usr/bin/env python3
"""Fresh fontTools consumer for the work family products.

Not a second merge engine: opens each built TTF and asserts the contract the
family advertises — mixed Latin+Han from one face, 2:1 advances, Nerd PUA from
the Cascadia zip, RIBBI name split so Light is not stuffed into name ID 2.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

from fontkit import naming

HAN_SAMPLE = "中"
ASCII_SAMPLE = "A"
# Powerline left-hard-divider — present in Nerd Fonts complete / Mono patches.
NERD_SAMPLE = 0xE0A0


def name_of(font: TTFont, name_id: int) -> str | None:
    rec = font["name"].getName(name_id, 3, 1, 0x409)
    if rec is None:
        rec = font["name"].getName(name_id, 1, 0, 0)
    if rec is None:
        return None
    return rec.toUnicode()


def check_one(path: Path, half: int) -> list[str]:
    errors: list[str] = []
    font = TTFont(path)
    try:
        cmap = font.getBestCmap() or {}
        hmtx = font["hmtx"]

        if ord(ASCII_SAMPLE) not in cmap:
            errors.append(f"{path.name}: cmap missing {ASCII_SAMPLE!r}")
        if ord(HAN_SAMPLE) not in cmap:
            errors.append(f"{path.name}: cmap missing {HAN_SAMPLE!r}")
        if NERD_SAMPLE not in cmap:
            errors.append(f"{path.name}: cmap missing Nerd U+{NERD_SAMPLE:04X}")

        if ord(ASCII_SAMPLE) in cmap and ord(HAN_SAMPLE) in cmap:
            latin = hmtx[cmap[ord(ASCII_SAMPLE)]][0]
            cjk = hmtx[cmap[ord(HAN_SAMPLE)]][0]
            if latin != half:
                errors.append(f"{path.name}: {ASCII_SAMPLE} advance {latin} != {half}")
            if cjk != 2 * latin:
                errors.append(
                    f"{path.name}: {HAN_SAMPLE} advance {cjk} != 2 × {latin}"
                )

        id1 = name_of(font, 1) or ""
        id2 = name_of(font, 2) or ""
        id16 = name_of(font, 16) or ""
        id17 = name_of(font, 17) or ""
        stem = path.stem  # AKRWorkSCNFM-Light
        subfamily = stem.rsplit("-", 1)[-1]
        expected_id1 = naming.legacy_family(id16 or "AKR Work SC NFM", subfamily)
        _, expected_id2 = naming.ribbi_split(subfamily)
        if id1 != expected_id1:
            errors.append(f"{path.name}: name ID 1 {id1!r} != {expected_id1!r}")
        if id2 != expected_id2:
            errors.append(f"{path.name}: name ID 2 {id2!r} != {expected_id2!r}")
        if subfamily == "Light" and id2 == "Light":
            errors.append(f"{path.name}: Light stuffed into name ID 2")
        if id17 != subfamily:
            errors.append(f"{path.name}: name ID 17 {id17!r} != {subfamily!r}")
        forbidden = ("cascadia", "caskaydia", "alibaba", "puhuiti", "普惠")
        hay = (id1 + id16).replace(" ", "").lower()
        hit = [w for w in forbidden if w in hay]
        if hit:
            errors.append(f"{path.name}: reserved token {hit} in name ID 1/16")
    finally:
        font.close()
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--expect-half", type=int, default=500)
    ap.add_argument("fonts", nargs="+", type=Path)
    args = ap.parse_args(argv)
    errors: list[str] = []
    for path in args.fonts:
        if not path.is_file():
            errors.append(f"missing {path}")
            print(f"FAIL {path}")
            continue
        found = check_one(path, args.expect_half)
        errors.extend(found)
        print(f"{'FAIL' if found else 'ok'} {path.name}")
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
