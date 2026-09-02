#!/usr/bin/env python3
"""Put CaskaydiaCove Nerd Font Mono on the product 2:1 half-cell.

Cascadia ships UPM 2048, mono cell 1200, fully hinted. scale_upem rewrites glyf
coordinates and leaves cvt / prep / fpgm / per-glyph bytecode measuring in the
old UPM — the same trap typewriter hits with Courier Prime — so hinting is
dropped after the UPM change. The surviving cell is 586 at UPM 1000; an X-scale
lands it on --en-adv (500) so PuHuiTi's native ~1000 Han cell is exactly 2:1.

Nerd icons need no special casing: the Mono members already draw every glyph,
icons included, at the single 1200 cell, so they land on the half cell with
ASCII. That is what makes the product NFM without a second font-patcher pass.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem

from fontkit.merge import drop_hinting, scale_latin_font


def prepare(src: Path, dst: Path, *, upm: int, en_adv: int) -> None:
    font = TTFont(src, recalcBBoxes=True, recalcTimestamp=False)
    current = font["head"].unitsPerEm
    if current != upm:
        print(f"  scale_upem {current} → {upm}")
        scale_upem(font, upm)
        drop_hinting(font)

    cmap = font.getBestCmap() or {}
    if ord("A") not in cmap:
        raise SystemExit(f"error: {src} has no Latin 'A' to measure the cell from")
    src_adv = font["hmtx"].metrics[cmap[ord("A")]][0]
    scale = en_adv / src_adv if src_adv else 1.0
    print(f"  X-scale {scale:.6f}  cell {src_adv} → {en_adv}")
    if abs(scale - 1.0) > 1e-9:
        scale_latin_font(
            font, scale, en_adv, src_adv, drop_hinting_too=True
        )
    else:
        drop_hinting(font)

    dst.parent.mkdir(parents=True, exist_ok=True)
    font.save(dst)
    font.close()

    check = TTFont(dst)
    cm = check.getBestCmap() or {}
    hmtx = check["hmtx"]
    sample = {ch: hmtx[cm[ord(ch)]][0] for ch in "Aa0" if ord(ch) in cm}
    print(f"  saved {dst} UPM={check['head'].unitsPerEm} glyphs={len(check.getGlyphOrder())} {sample}")
    check.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--upm", type=int, default=1000)
    ap.add_argument("--en-adv", type=int, default=500)
    args = ap.parse_args(argv)
    if not args.src.is_file():
        print(f"error: not a file: {args.src}", file=__import__("sys").stderr)
        return 2
    prepare(args.src, args.dst, upm=args.upm, en_adv=args.en_adv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
