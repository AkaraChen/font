#!/usr/bin/env python3
"""Render 荷塘月色 mixed CJK/EN sample for AKR Sans SC Dual."""

from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

DEFAULT_BODY = """这几天心里颇不宁静。今晚在 courtyard 里坐着乘凉，忽然想起 day by day 走过的荷塘，
在这 full moon 的光里，总该另有一番样子吧。叶子出水很高，像亭亭的舞女的 skirt。
层层的叶子中间，零星地点缀着些 white flowers，有袅娜地开着的，有羞涩地打着朵儿的；
正如一粒粒的明珠，又如碧天里的 stars，又如刚出浴的美人。

// coding sample · 中英混排对齐检查
const moon = "荷塘月色"; // full moon over the lotus pond
function walk(path: string): void {
  // day by day 走过的 path，观察 leaf 与 flower 的 rhythm
  console.log(`path=${path}, width=550/1100`);
}
// 两英文字母应严格对齐一汉字：aa中bb文cc混dd排
// |a|b|中|c|d|文|  →  中文 cell=1100, 英文 cell=550
aa中bb文cc混dd排ee齐ff检
|a|b|中|c|d|文|e|f|混|"""


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
    width = 920
    height = title_h + pad_y * 2 + line_h * (len(lines) + 3)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    strip = (28, 28, 32) if theme == "dark" else (235, 235, 238)
    draw.rectangle([0, 0, width, title_h], fill=strip)
    draw.text((pad_x, 14), title, font=title_font, fill=fg)
    draw.text((width - 280, 18), f"{font_path.stem}", font=meta_font, fill=muted)

    y = title_h + pad_y
    a_w = font.getlength("a")
    cjk_w = font.getlength("中")

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
    footer = (
        f"metrics check: 2×EN cell = {2 * a_w:.1f}px, CJK cell = {cjk_w:.1f}px  |  "
        f"ratio={cjk_w / a_w:.3f} (expect 2.000)"
    )
    draw.text((pad_x, y), footer, font=meta_font, fill=muted)

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"sample-{theme}.png"
    img.save(out, "PNG")
    print(f"wrote {out}  a_w={a_w:.2f} cjk_w={cjk_w:.2f}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    ap.add_argument(
        "--font",
        type=Path,
        default=root / "out" / "AKRSansSCDual-Regular.ttf",
    )
    ap.add_argument("--out-dir", type=Path, default=root / "samples" / "rendered")
    ap.add_argument("--title", default="Plex merge · EN 550 / CJK 1100")
    ap.add_argument("--body-file", type=Path, default=None)
    ap.add_argument("--size", type=int, default=15)
    args = ap.parse_args()

    if not args.font.exists():
        print(f"missing font: {args.font}")
        return 1

    body = args.body_file.read_text(encoding="utf-8") if args.body_file else DEFAULT_BODY

    print("Verify advances:")
    print(verify_metrics(args.font))
    render(
        args.font,
        args.out_dir,
        "dark",
        bg=(18, 18, 20),
        fg=(220, 220, 224),
        muted=(140, 140, 150),
        grid=(60, 80, 100),
        title=args.title,
        body=body,
        size=args.size,
    )
    render(
        args.font,
        args.out_dir,
        "light",
        bg=(250, 250, 252),
        fg=(24, 24, 28),
        muted=(100, 100, 110),
        grid=(180, 190, 200),
        title=args.title,
        body=body,
        size=args.size,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
