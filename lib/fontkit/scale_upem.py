#!/usr/bin/env python3
"""Normalise a CJK master to the product's units-per-em.

Run as: fontkit scale-upem SRC DST --upem 1000

Why it is a step of its own: the CJK master a family pins is drawn on whatever
grid its designer used (LXGW Neo ZhiSong is 2048), while the product grid comes
from ``[grid] upm`` in font.toml. Everything downstream — embolden strengths,
the 2:1 advance gate, stem measurements — is expressed in product units, so the
scale has to happen before any of it and exactly once.

This was six lines of heredoc'd Python inside
``serif/scripts/03-prepare-cjk.sh``. It is not serif-specific: every family that
merges a CJK master on a foreign grid needs it, and the ones that do not simply
pin a master already at 1000 (the scale is then a no-op, which is why the check
below is a comparison and not an error).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem


def scale_font(src: Path, dst: Path, upem: int) -> int:
    """Write `src` to `dst` at `upem` units. Returns the source's UPM."""
    font = TTFont(src)
    try:
        source_upem = font["head"].unitsPerEm
        if source_upem != upem:
            scale_upem(font, upem)
        dst.parent.mkdir(parents=True, exist_ok=True)
        font.save(dst)
    finally:
        font.close()
    return source_upem


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--upem", type=int, required=True, help="target units-per-em")
    args = ap.parse_args(argv)

    if not args.src.is_file():
        print(f"error: not a file: {args.src}", file=sys.stderr)
        return 2
    if args.upem <= 0:
        print(f"error: --upem must be positive, got {args.upem}", file=sys.stderr)
        return 2

    source_upem = scale_font(args.src, args.dst, args.upem)
    if source_upem == args.upem:
        print(f"saved {args.dst} UPM={args.upem} (already on grid)")
    else:
        print(f"saved {args.dst} UPM={args.upem} (from {source_upem})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
