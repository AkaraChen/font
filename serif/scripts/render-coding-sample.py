#!/usr/bin/env python3
"""Render coding sample text with a TTF at common editor sizes (px ≈ pt on 96dpi).

Usage:
  python render-coding-sample.py --font out/AKRSlabSCDual-Regular.ttf
  python render-coding-sample.py --font out/nerd/....ttf --sizes 12,14,16

Requires: pillow, fontTools (font path only; Pillow draws the text).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


DEFAULT_TEXT = """\
def greet(name: str) -> str:
    \"\"\"返回问候语 — return a greeting.\"\"\"
    # TODO: 支持多语言 / multi-lang
    return f"Hello, {name}! 你好，{name}！"

# 0123456789012345678901234567890123456789
# |.........|.........|.........|.........|
# 中文中文中文中文中文中文中文中文中文中文
# Hello世界Test测试Code代码Font字体OK

class Config:
    host = "127.0.0.1"
    port = 8080  # 默认端口
    users = ["Alice", "小明", "Bob", "小红"]

# ┌────────┬────────┐
# │ key    │ value  │
# ├────────┼────────┤
# │ 名称   │ 字体   │
# └────────┴────────┘
"""


def render(font_path: Path, text: str, size_px: int, out: Path, pad: int = 16) -> None:
    font = ImageFont.truetype(str(font_path), size=size_px)
    # measure
    dummy = Image.new("RGB", (1, 1), "white")
    draw = ImageDraw.Draw(dummy)
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=4)
    w = bbox[2] - bbox[0] + pad * 2
    h = bbox[3] - bbox[1] + pad * 2
    img = Image.new("RGB", (max(w, 1), max(h, 1)), "#1e1e1e")
    draw = ImageDraw.Draw(img)
    draw.multiline_text(
        (pad - bbox[0], pad - bbox[1]),
        text,
        font=font,
        fill="#d4d4d4",
        spacing=4,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"wrote {out} ({img.size[0]}x{img.size[1]} @ {size_px}px)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Render coding sample PNGs")
    ap.add_argument("--font", type=Path, required=True, help="TTF/OTF path")
    ap.add_argument(
        "--text-file",
        type=Path,
        default=None,
        help="optional sample text (default: built-in coding snippet)",
    )
    ap.add_argument(
        "--sizes",
        default="12,13,14,15,16",
        help="comma-separated pixel sizes",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="output directory (default: serif/samples/rendered)",
    )
    args = ap.parse_args()

    if not args.font.is_file():
        print(f"error: font not found: {args.font}")
        return 2

    text = args.text_file.read_text(encoding="utf-8") if args.text_file else DEFAULT_TEXT
    sizes = [int(s.strip()) for s in args.sizes.split(",") if s.strip()]
    out_dir = args.out_dir or (
        Path(__file__).resolve().parent.parent / "samples" / "rendered"
    )
    stem = args.font.stem
    for sz in sizes:
        out = out_dir / f"{stem}-{sz}px.png"
        render(args.font, text, sz, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
