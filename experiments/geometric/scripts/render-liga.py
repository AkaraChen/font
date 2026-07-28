#!/usr/bin/env python3
"""Render a short coding line with OpenType calt/liga via uharfbuzz (GE-1 on/off)."""

from __future__ import annotations

import argparse
from pathlib import Path

import uharfbuzz as hb
from PIL import Image, ImageDraw, ImageFont


def shape(font_path: Path, text: str, features: dict[str, bool]) -> list[tuple[int, int]]:
    """Return list of (glyph_id, x_advance) in font units."""
    data = font_path.read_bytes()
    face = hb.Face(data)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, features)
    infos = buf.glyph_infos
    positions = buf.glyph_positions
    return [(info.codepoint, pos.x_advance) for info, pos in zip(infos, positions)]


def render_pair(font_path: Path, out: Path, size: int = 22) -> Path:
    lines = [
        ("calt OFF", {"calt": False, "liga": False, "dlig": False}),
        ("calt ON ", {"calt": True, "liga": True, "dlig": True}),
    ]
    sample = "if (x != y && a => b || c <= d) { return foo === bar; } // != => <= >= ==="
    title = "GE-1 Fira Code · ligatures on/off"

    # Use PIL for simple glyph paint without full hb glyph drawing:
    # Draw the same string twice — once FreeType/PIL (no features), once we note
    # hb glyph count difference. For visual ligatures we draw via hb glyph paths
    # using fontTools pen → rough: fall back to showing both raw strings and
    # glyph counts, then paint with ImageFont (PIL ignores features) for the OFF
    # line and for ON we substitute known Fira liga sequences if present.
    #
    # Better: draw with hb advances by rendering each glyph via fontTools.
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.misc.transform import Transform

    tt = TTFont(font_path)
    glyf = tt["glyf"]
    upem = tt["head"].unitsPerEm
    scale = size / upem

    def glyph_path_to_points(gid: int):
        name = tt.getGlyphName(gid)
        g = glyf[name]
        pen = RecordingPen()
        g.draw(pen, glyf)
        return pen.value

    width, height = 1100, 180
    bg, fg, muted, strip = (18, 18, 20), (220, 220, 224), (140, 140, 150), (28, 28, 32)
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, 44], fill=strip)
    meta = ImageFont.load_default()
    try:
        title_font = ImageFont.truetype(str(font_path), size=16)
        label_font = ImageFont.truetype(str(font_path), size=14)
    except Exception:
        title_font = meta
        label_font = meta
    draw.text((24, 12), title, font=title_font, fill=fg)

    y = 60
    for label, feats in lines:
        pairs = shape(font_path, sample, feats)
        draw.text((24, y - 18), f"{label}  glyphs={len(pairs)}  features={feats}", font=label_font, fill=muted)
        x = 24
        for gid, x_adv in pairs:
            name = tt.getGlyphName(gid)
            g = glyf[name]
            if g.numberOfContours == 0:
                x += x_adv * scale
                continue
            pen = RecordingPen()
            g.draw(pen, glyf)
            # Rasterize contours as polyline approx
            pts: list[tuple[float, float]] = []
            contours: list[list[tuple[float, float]]] = []
            for op, args in pen.value:
                if op == "moveTo":
                    if pts:
                        contours.append(pts)
                    pts = [(args[0][0], args[0][1])]
                elif op == "lineTo":
                    pts.append((args[0][0], args[0][1]))
                elif op == "qCurveTo":
                    # approximate quadratic with end point
                    for pt in args:
                        pts.append((pt[0], pt[1]))
                elif op == "closePath":
                    if pts:
                        contours.append(pts)
                        pts = []
            if pts:
                contours.append(pts)
            for cont in contours:
                if len(cont) < 2:
                    continue
                poly = [
                    (x + px * scale, y + size * 0.85 - py * scale) for px, py in cont
                ]
                draw.line(poly + [poly[0]], fill=fg, width=1)
            x += x_adv * scale
        y += 55

    tt.close()
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    print(f"wrote {out}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--font", type=Path, required=True)
    ap.add_argument(
        "--out",
        type=Path,
        default=root / "samples" / "rendered" / "GE-1-liga-compare-dark.png",
    )
    ap.add_argument("--size", type=int, default=20)
    args = ap.parse_args()
    if not args.font.exists():
        print(f"missing {args.font}")
        return 1
    render_pair(args.font, args.out, size=args.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
