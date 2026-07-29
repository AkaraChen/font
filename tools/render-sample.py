#!/usr/bin/env python3
"""Render a properly shaped sample of AKR Hand SC NFM.

Pillow only shapes text when it was built with libraqm — without it `!=` draws
as two glyphs and a ligature font looks broken in its own screenshot. So this
script shapes with HarfBuzz (`uharfbuzz`) and rasterises each glyph outline with
FreeType (`freetype-py`): what the PNG shows is what the font actually does,
`liga` + `calt` applied, CJK on the full cell, Latin on the half cell.

  render-sample.py --font out/AKRHandSCNFM-Regular.ttf
  → samples/rendered/sample-{dark,light}.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

try:
    import uharfbuzz as hb
    from fontTools.misc.transform import Transform
    from fontTools.pens.freetypePen import FreeTypePen
    from PIL import Image, ImageDraw
except ImportError as exc:  # pragma: no cover
    print(
        "error: needs Pillow + uharfbuzz + freetype-py + numpy "
        "(pip install Pillow uharfbuzz freetype-py numpy)",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc

DEFAULT_BODY = """// AKR Hand SC NFM · Monaspace Radon × 霞鹜文楷 · 中英 2:1 对齐
fn walk(path: &str) -> Result<(), Error> {
  // day by day 走过的 path，观察 leaf 与 flower 的 rhythm
  if x != y && a <= b || c >= d { log("path=%s ==> ok", path); }
}
// ligatures: != == === -> => <- <= >= ... :: |> /* */ ++ --
// 两个英文字母严格对齐一个汉字：
aa中bb文cc混dd排ee齐ff检gg查
|a|b|中|c|d|文|e|f|混|g|h|排|
这几天心里颇不宁静。今晚在 courtyard 里坐着乘凉，忽然想起 day by day 走过的荷塘，
在这 full moon 的光里，总该另有一番样子吧。叶子出水很高，像亭亭的舞女的 skirt。"""

THEMES = {
    "dark": dict(
        bg=(18, 18, 20), fg=(220, 220, 224), muted=(140, 140, 150),
        grid=(58, 76, 96), strip=(28, 28, 32),
    ),
    "light": dict(
        bg=(250, 250, 252), fg=(24, 24, 28), muted=(100, 100, 110),
        grid=(186, 194, 204), strip=(235, 235, 238),
    ),
}


class Renderer:
    def __init__(self, font_path: Path):
        self.tt = TTFont(font_path)
        self.upm = self.tt["head"].unitsPerEm
        self.glyph_order = self.tt.getGlyphOrder()
        self.glyph_set = self.tt.getGlyphSet()
        self.hb_font = hb.Font(hb.Face(font_path.read_bytes()))
        self.cmap = self.tt.getBestCmap()

    def close(self) -> None:
        self.tt.close()

    def advance(self, char: str) -> int:
        return self.tt["hmtx"][self.cmap[ord(char)]][0]

    def shape(self, text: str):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, {"liga": True, "calt": True})
        x = 0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            yield info.codepoint, x + pos.x_offset, pos.y_offset
            x += pos.x_advance

    def draw_text(
        self,
        image: Image.Image,
        text: str,
        origin: tuple[float, float],
        px: float,
        colour: tuple[int, int, int],
    ) -> None:
        """Draw shaped `text` with its baseline at origin=(x, baseline_y)."""
        scale = px / self.upm
        pad = int(px)
        box_h = int(px * 2.4)
        baseline_in_box = int(px * 1.6)
        x0, baseline = origin

        for gid, x_off, y_off in self.shape(text):
            name = self.glyph_order[gid]
            glyph = self.glyph_set[name]
            if self.tt["glyf"][name].numberOfContours == 0:
                continue
            pen = FreeTypePen(self.glyph_set)
            glyph.draw(pen)
            box_w = int(self.tt["hmtx"][name][0] * scale) + 2 * pad
            transform = Transform(scale, 0, 0, scale, pad, box_h - baseline_in_box)
            try:
                buf, size = pen.buffer(width=box_w, height=box_h, transform=transform)
            except Exception:
                continue
            if not buf:
                continue
            mask = Image.frombytes("L", size, buf)
            left = int(round(x0 + x_off * scale)) - pad
            top = int(round(baseline - y_off * scale)) - baseline_in_box
            image.paste(colour, (left, top), mask)


def render(font_path: Path, out_dir: Path, theme: str, *, body: str, title: str, px: int) -> Path:
    renderer = Renderer(font_path)
    palette = THEMES[theme]
    lines = body.splitlines()

    pad_x, pad_y = 40, 30
    line_h = int(px * 1.65)
    title_h = int(px * 3)
    cell = renderer.advance("A") * px / renderer.upm
    width = 1120
    height = title_h + pad_y * 2 + line_h * (len(lines) + 2)

    image = Image.new("RGB", (width, height), palette["bg"])
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width, title_h], fill=palette["strip"])
    renderer.draw_text(image, title, (pad_x, title_h * 0.65), px + 2, palette["fg"])

    y = title_h + pad_y + px
    for line in lines:
        if line.startswith(("aa中", "|a|b|")):
            for k in range(int((width - 2 * pad_x) / cell)):
                x = pad_x + k * cell
                draw.line([(x, y - px), (x, y + line_h - px - 6)], fill=palette["grid"], width=1)
        renderer.draw_text(image, line, (pad_x, y), px, palette["fg"])
        y += line_h

    footer = (
        f"{font_path.stem} · EN cell {renderer.advance('A')} / CJK cell "
        f"{renderer.advance('中')} · HarfBuzz-shaped (liga + calt)"
    )
    renderer.draw_text(image, footer, (pad_x, y + px * 0.6), int(px * 0.8), palette["muted"])
    renderer.close()

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"sample-{theme}.png"
    image.save(out, "PNG")
    print(f"wrote {out}")
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--font", type=Path, default=root / "out" / "AKRHandSCNFM-Regular.ttf")
    ap.add_argument("--out-dir", type=Path, default=root / "samples" / "rendered")
    ap.add_argument("--title", default="AKR Hand SC NFM · 中英 2:1 · Nerd Font Mono")
    ap.add_argument("--body-file", type=Path, default=None)
    ap.add_argument("--size", type=int, default=19)
    args = ap.parse_args()

    if not args.font.exists():
        print(f"missing font: {args.font}", file=sys.stderr)
        return 1
    body = args.body_file.read_text(encoding="utf-8") if args.body_file else DEFAULT_BODY
    for theme in THEMES:
        render(args.font, args.out_dir, theme, body=body, title=args.title, px=args.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
