#!/usr/bin/env python3
"""Wrap a built product in another container format.

The `format` axis of the granularity contract (`packaged`) has only ever had one
value. The text profile is the first product with a reason for a second: a
reading face gets embedded on the web, and shipping a 20 MB TTF where a 6 MB
WOFF2 would do is the whole of the difference.

Container, not conversion. This re-wraps the same `glyf` outlines and the same
tables — no re-rasterising, no re-hinting, no subsetting — so the WOFF2 and the
TTF are the same font and a fingerprint taken through either agrees.

`otf` is deliberately not here. A real OTF is CFF, and these products are
quadratic by construction: the CJK donor is TrueType, and `handwriting/scripts/
prepare_latin.py` converts Monaspace's cubics to quadratics with cu2qu precisely
because one font cannot hold both. Going back would be a second, lossy curve
conversion of 45 000 imported Han glyphs, which is a worse font, not another
format of the same one. `[[build.unsupported]]` in font.toml says so out loud
rather than leaving `otf` an unexplained gap.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

FLAVOURS = {"woff2": "woff2", "woff": "woff"}


def rewrap(src: Path, dst: Path, fmt: str) -> None:
    font = TTFont(src, recalcBBoxes=False, recalcTimestamp=False)
    try:
        font.flavor = FLAVOURS[fmt]
        dst.parent.mkdir(parents=True, exist_ok=True)
        font.save(dst)
    finally:
        font.close()
    print(f"  {src.name} → {dst.name} ({dst.stat().st_size} bytes)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("fonts", nargs="+", type=Path, help="built TTF product(s)")
    ap.add_argument("--format", required=True, choices=sorted(FLAVOURS))
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args(argv)

    for src in args.fonts:
        if not src.is_file():
            print(f"error: not a file: {src}", file=sys.stderr)
            return 2
        rewrap(src, args.out_dir / f"{src.stem}.{args.format}", args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
