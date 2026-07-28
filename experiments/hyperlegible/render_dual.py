#!/usr/bin/env python3
"""Render Latin mono + CJK pairing without outline merge.

Uses two FreeType faces and a fixed 2:1 cell grid so mixed lines show true
dual-width alignment. Good enough for experimental pairing screenshots.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def is_cjk_side(ch: str) -> bool:
    cp = ord(ch)
    ranges = (
        (0x2E80, 0x2EFF),
        (0x2F00, 0x2FDF),
        (0x3000, 0x303F),
        (0x3040, 0x30FF),
        (0x3100, 0x312F),
        (0x3190, 0x319F),
        (0x31A0, 0x31BF),
        (0x31C0, 0x31EF),
        (0x31F0, 0x31FF),
        (0x3200, 0x32FF),
        (0x3300, 0x33FF),
        (0x3400, 0x4DBF),
        (0x4E00, 0x9FFF),
        (0xF900, 0xFAFF),
        (0xFE30, 0xFE4F),
        (0xFF00, 0xFFEF),
        (0x20000, 0x2A6DF),
    )
    return any(a <= cp <= b for a, b in ranges)


def load_face(path: Path, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    # Pillow index via layout_engine; for TTC use font index in path? ImageFont.truetype index=
    return ImageFont.truetype(str(path), size=size, index=index)


def measure_cell(latin: ImageFont.FreeTypeFont) -> float:
    return float(latin.getlength("a"))


def draw_mixed_line(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    text: str,
    latin: ImageFont.FreeTypeFont,
    cjk: ImageFont.FreeTypeFont,
    en_cell: float,
    fill: tuple[int, int, int],
) -> float:
    """Draw text with dual-width grid; return final x."""
    for ch in text:
        if ch == "\t":
            x += en_cell * 4
            continue
        use_cjk = is_cjk_side(ch)
        face = cjk if use_cjk else latin
        # place glyph; CJK occupies 2 cells, Latin 1 cell
        cells = 2.0 if use_cjk else 1.0
        cell_w = en_cell * cells
        # center glyph within cell
        gw = float(face.getlength(ch))
        ox = x + max(0.0, (cell_w - gw) / 2.0)
        draw.text((ox, y), ch, font=face, fill=fill)
        x += cell_w
    return x


def render_pair(
    *,
    latin_path: Path,
    cjk_path: Path,
    out_path: Path,
    title: str,
    body: str,
    size: int = 16,
    theme: str = "dark",
    latin_index: int = 0,
    cjk_index: int = 0,
    subtitle: str = "",
) -> Path:
    if theme == "dark":
        bg, fg, muted, grid, strip = (
            (18, 18, 20),
            (220, 220, 224),
            (140, 140, 150),
            (55, 75, 95),
            (28, 28, 32),
        )
    else:
        bg, fg, muted, grid, strip = (
            (250, 250, 252),
            (24, 24, 28),
            (100, 100, 110),
            (180, 190, 200),
            (235, 235, 238),
        )

    latin = load_face(latin_path, size, latin_index)
    cjk = load_face(cjk_path, size, cjk_index)
    title_latin = load_face(latin_path, size + 2, latin_index)
    title_cjk = load_face(cjk_path, size + 2, cjk_index)
    meta_latin = load_face(latin_path, max(11, size - 3), latin_index)
    meta_cjk = load_face(cjk_path, max(11, size - 3), cjk_index)

    en_cell = measure_cell(latin)
    title_cell = measure_cell(title_latin)
    meta_cell = measure_cell(meta_latin)
    lines = body.splitlines()
    pad_x, pad_y = 36, 26
    line_h = size + 12
    title_h = 56
    width = 1000
    height = title_h + pad_y * 2 + line_h * (len(lines) + 4)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, title_h], fill=strip)
    draw_mixed_line(draw, pad_x, 10, title, title_latin, title_cjk, title_cell, fg)
    meta_line = subtitle or f"{latin_path.stem} + {cjk_path.stem}"
    draw_mixed_line(draw, pad_x, 34, meta_line[:90], meta_latin, meta_cjk, meta_cell, muted)

    y = title_h + pad_y
    for line in lines:
        if line.startswith("aa中") or line.startswith("|a|b|"):
            for k in range(0, 30):
                x = pad_x + k * en_cell
                col = grid if k % 2 == 0 else (
                    (grid[0] // 2 + bg[0] // 2,
                     grid[1] // 2 + bg[1] // 2,
                     grid[2] // 2 + bg[2] // 2)
                )
                draw.line([(x, y - 2), (x, y + line_h - 4)], fill=col, width=1)
            draw.line(
                [(pad_x, y + line_h - 4), (pad_x + 30 * en_cell, y + line_h - 4)],
                fill=grid,
                width=1,
            )
        draw_mixed_line(draw, pad_x, y, line, latin, cjk, en_cell, fg)
        y += line_h

    y += 10
    cjk_native = float(cjk.getlength("中"))
    footer = (
        f"grid: EN cell={en_cell:.1f}px  CJK cell={2 * en_cell:.1f}px (forced 2:1)  |  "
        f"CJK native width={cjk_native:.1f}px  |  dual-face preview (no outline merge)"
    )
    draw_mixed_line(draw, pad_x, y, footer, meta_latin, meta_cjk, meta_cell, muted)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    print(f"wrote {out_path}")
    return out_path


def render_compare(
    *,
    latin_a: Path,
    cjk_a: Path,
    latin_b: Path,
    cjk_b: Path,
    out_path: Path,
    label_a: str,
    label_b: str,
    body: str,
    size: int = 16,
    cjk_index_a: int = 0,
    cjk_index_b: int = 0,
) -> Path:
    bg, fg, muted, strip = (18, 18, 20), (220, 220, 224), (140, 140, 150), (28, 28, 32)
    accent_a, accent_b = (120, 200, 160), (160, 160, 220)

    la = load_face(latin_a, size)
    ca = load_face(cjk_a, size, cjk_index_a)
    lb = load_face(latin_b, size)
    cb = load_face(cjk_b, size, cjk_index_b)
    title_la = load_face(latin_a, size + 1)
    title_ca = load_face(cjk_a, size + 1, cjk_index_a)
    meta_la = load_face(latin_a, max(11, size - 3))
    meta_ca = load_face(cjk_a, max(11, size - 3), cjk_index_a)

    en_a = measure_cell(la)
    en_b = measure_cell(lb)
    title_cell = measure_cell(title_la)
    meta_cell = measure_cell(meta_la)
    # Keep compare strip to confusables + one coding line so columns stay readable.
    prefer = [
        ln
        for ln in body.splitlines()
        if ln.strip()
        and (
            "0O" in ln
            or "中英" in ln
            or ln.startswith("const ")
            or ln.startswith("function ")
            or "console" in ln
            or ln.startswith("// Hyper")
            or ln.startswith("// coding")
        )
    ]
    lines = prefer[:8] if prefer else [ln for ln in body.splitlines() if ln.strip()][:8]
    pad_x, pad_y = 24, 18
    line_h = size + 12
    col_w = 520
    title_h = 52
    width = col_w * 2 + 16
    height = title_h + pad_y * 2 + line_h * (len(lines) + 5)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, title_h], fill=strip)
    draw_mixed_line(
        draw,
        pad_x,
        14,
        "HL-4 对照条 · Hyperlegible vs 常规可读 mono（同字号 · 同 CJK）",
        title_la,
        title_ca,
        title_cell,
        fg,
    )

    y0 = title_h + 10
    draw_mixed_line(draw, pad_x, y0, label_a, meta_la, meta_ca, meta_cell, accent_a)
    draw_mixed_line(
        draw, col_w + 8 + pad_x, y0, label_b, meta_la, meta_ca, meta_cell, accent_b
    )
    draw.line([(col_w + 4, title_h), (col_w + 4, height)], fill=(50, 50, 55), width=1)

    y = y0 + line_h
    for line in lines:
        draw_mixed_line(draw, pad_x, y, line, la, ca, en_a, fg)
        draw_mixed_line(draw, col_w + 8 + pad_x, y, line, lb, cb, en_b, fg)
        y += line_h

    y += 8
    note = (
        f"左 EN cell={en_a:.1f}px  |  右 EN cell={en_b:.1f}px  ·  "
        "看 0O / l1I / 用户ID 是否 visibly 更可辨"
    )
    draw_mixed_line(draw, pad_x, y, note, meta_la, meta_ca, meta_cell, muted)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    print(f"wrote {out_path}")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("pair", "compare"), default="pair")
    ap.add_argument("--latin", type=Path)
    ap.add_argument("--cjk", type=Path)
    ap.add_argument("--latin-b", type=Path)
    ap.add_argument("--cjk-b", type=Path)
    ap.add_argument("--cjk-index", type=int, default=0)
    ap.add_argument("--cjk-index-b", type=int, default=0)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--title", default="HL experiment")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--label-a", default="HL-1")
    ap.add_argument("--label-b", default="HL-4")
    ap.add_argument("--body-file", type=Path, required=True)
    ap.add_argument("--size", type=int, default=16)
    ap.add_argument("--theme", default="dark")
    args = ap.parse_args()
    body = args.body_file.read_text(encoding="utf-8")

    if args.mode == "compare":
        render_compare(
            latin_a=args.latin,
            cjk_a=args.cjk,
            latin_b=args.latin_b,
            cjk_b=args.cjk_b or args.cjk,
            out_path=args.out,
            label_a=args.label_a,
            label_b=args.label_b,
            body=body,
            size=args.size,
            cjk_index_a=args.cjk_index,
            cjk_index_b=args.cjk_index_b if args.cjk_b else args.cjk_index,
        )
        return 0

    render_pair(
        latin_path=args.latin,
        cjk_path=args.cjk,
        out_path=args.out,
        title=args.title,
        body=body,
        size=args.size,
        theme=args.theme,
        cjk_index=args.cjk_index,
        subtitle=args.subtitle,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
