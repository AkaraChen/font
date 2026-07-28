#!/usr/bin/env python3
"""Render dark/light mixed CJK/EN sample for neo-grotesque experiments."""

from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont


def verify_metrics(font_path: Path) -> str:
    f = TTFont(font_path)
    cm = f.getBestCmap()
    hmtx = f["hmtx"]
    lines = []
    for ch in list("aA0中文荷 "):
        if ord(ch) not in cm:
            lines.append(f"  {ch!r} MISSING")
            continue
        g = cm[ord(ch)]
        w, lsb = hmtx[g]
        lines.append(f"  {ch!r} advance={w} lsb={lsb}")
    if ord("a") in cm and ord("中") in cm:
        wa = hmtx[cm[ord("a")]][0]
        wz = hmtx[cm[ord("中")]][0]
        lines.append(f"  2*EN({wa})={2 * wa}  CJK({wz})  equal={2 * wa == wz}")
    f.close()
    return "\n".join(lines)


def render(
    font_path: Path,
    out_path: Path,
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
    draw.text((width - 300, 18), font_path.stem, font=meta_font, fill=muted)

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
        f"metrics: 2×EN={2 * a_w:.1f}px  CJK={cjk_w:.1f}px  "
        f"ratio={cjk_w / a_w:.3f} (expect 2.000)"
    )
    draw.text((pad_x, y), footer, font=meta_font, fill=muted)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    print(f"wrote {out_path}  a_w={a_w:.2f} cjk_w={cjk_w:.2f}")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--font", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--stem", default=None, help="filename stem prefix")
    ap.add_argument("--body-file", type=Path, required=True)
    ap.add_argument("--size", type=int, default=15)
    args = ap.parse_args()

    if not args.font.exists():
        print(f"missing font: {args.font}")
        return 1

    body = args.body_file.read_text(encoding="utf-8")
    stem = args.stem or args.font.stem
    print("Verify advances:")
    print(verify_metrics(args.font))

    render(
        args.font,
        args.out_dir / f"{stem}-dark.png",
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
        args.out_dir / f"{stem}-light.png",
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
