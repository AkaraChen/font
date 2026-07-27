#!/usr/bin/env python3
"""Render mixed CJK/EN coding sample for RadonWenKai Dual / NFM."""

from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

DEFAULT_BODY = """这几天心里颇不宁静。今晚在 courtyard 里坐着乘凉，忽然想起 day by day 走过的荷塘，
在这 full moon 的光里，总该另有一番样子吧。叶子出水很高，像亭亭的舞女的 skirt。

// coding sample · Radon × 霞鹜文楷 · 中英 2:1 · calt ligatures
const moon = "荷塘月色"; // full moon over the lotus pond
fn walk(path: String) {
  // => != <= >= == && || //  <- coding ligatures from Monaspace Radon
  println!("path={}, width=620/1240", path);
}
// 两英文字母应严格对齐一汉字：aa中bb文cc混dd排
// |a|b|中|c|d|文|  →  中文 cell=1240, 英文 cell=620
aa中bb文cc混dd排ee齐ff检
|a|b|中|c|d|文|e|f|混|
// nerd / powerline smoke (if NFM):  \ue0b0  \uf015  \ue7a8
"""


def verify_metrics(font_path: Path) -> str:
    f = TTFont(font_path)
    cm = f.getBestCmap()
    hmtx = f["hmtx"]
    lines = []
    for ch in list("aA0中文荷 "):
        g = cm[ord(ch)]
        w, lsb = hmtx[g]
        lines.append(f"  {ch!r} advance={w} lsb={lsb}")
    wa = hmtx[cm[ord("a")]][0]
    wz = hmtx[cm[ord("中")]][0]
    lines.append(f"  2*EN({wa})={2 * wa}  CJK({wz})  equal={2 * wa == wz}")
    f.close()
    return "\n".join(lines)


def render(
    font_path: Path,
    out_dir: Path,
    theme: str,
    bg: tuple[int, int, int],
    fg: tuple[int, int, int],
    muted: tuple[int, int, int],
    grid: tuple[int, int, int],
    title: str,
    body: str,
    size: int,
) -> Path:
    font = ImageFont.truetype(str(font_path), size=size)
    title_font = ImageFont.truetype(str(font_path), size=size + 3)
    meta_font = ImageFont.truetype(str(font_path), size=max(11, size - 3))

    lines = body.splitlines()
    pad_x, pad_y = 36, 28
    line_h = size + 8
    title_h = 48
    width = 960
    height = title_h + pad_y * 2 + line_h * (len(lines) + 3)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    strip = (28, 28, 32) if theme == "dark" else (235, 235, 238)
    draw.rectangle([0, 0, width, title_h], fill=strip)
    draw.text((pad_x, 14), title, font=title_font, fill=fg)
    draw.text((width - 300, 18), f"{font_path.stem}", font=meta_font, fill=muted)

    y = title_h + pad_y
    a_w = font.getlength("a")

    for line in lines:
        if line.startswith("aa中") or line.startswith("|a|b|"):
            for k in range(0, 24):
                x = pad_x + k * a_w
                col = grid if k % 2 == 0 else (
                    (grid[0] // 2 + bg[0] // 2,
                     grid[1] // 2 + bg[1] // 2,
                     grid[2] // 2 + bg[2] // 2)
                )
                draw.line([(x, y - 2), (x, y + line_h - 4)], fill=col, width=1)
            draw.line(
                [(pad_x, y + line_h - 4), (pad_x + 24 * a_w, y + line_h - 4)],
                fill=grid,
                width=1,
            )

        draw.text((pad_x, y), line, font=font, fill=fg)
        y += line_h

    y += 8
    footer = verify_metrics(font_path)
    for fl in footer.splitlines():
        draw.text((pad_x, y), fl, font=meta_font, fill=muted)
        y += max(14, size - 2)

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"sample-{theme}.png"
    img.save(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("samples/rendered"))
    ap.add_argument("--title", default="RadonWenKai Dual · EN 620 / CJK 1240")
    ap.add_argument("--size", type=int, default=16)
    ap.add_argument("--body-file", type=Path, default=None)
    args = ap.parse_args()

    body = DEFAULT_BODY
    if args.body_file and args.body_file.exists():
        body = args.body_file.read_text(encoding="utf-8")

    themes = {
        "dark": ((18, 18, 22), (230, 230, 235), (120, 120, 130), (60, 60, 70)),
        "light": ((250, 250, 252), (20, 20, 24), (100, 100, 110), (200, 200, 210)),
    }
    for name, (bg, fg, muted, grid) in themes.items():
        out = render(
            args.font,
            args.out_dir,
            name,
            bg,
            fg,
            muted,
            grid,
            args.title,
            body,
            args.size,
        )
        print(f"wrote {out}")
    print("metrics:\n" + verify_metrics(args.font))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
