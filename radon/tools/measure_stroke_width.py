#!/usr/bin/env python3
"""Measure Latin vs CJK stem widths from TrueType outlines (KIT-239).

Uses horizontal/vertical scanline ray-casts through glyph outlines (fontTools +
pathops). Reports median vertical and horizontal stem thicknesses in font units
so embolden strengths can be calibrated against IosevkaNSlab Latin.

Examples:
  measure_stroke_width.py --latin font.ttf --cjk emboldened.ttf
  measure_stroke_width.py --font product.ttf --chars A,H,n,中,一,十
  measure_stroke_width.py --calibrate-embolden base.ttf --latin-ref latin.ttf
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
import pathops


# Representative coding-face stems. Latin: upright verticals / crossbars.
# CJK: 中 (verticals + horizontals), 一 (horizontal), 十 (both), 国/日 denser.
DEFAULT_LATIN = ["H", "I", "l", "n", "o", "T", "E"]
DEFAULT_CJK = ["中", "一", "十", "日", "国", "木", "工"]


def glyph_to_path(glyph_set, name: str) -> pathops.Path:
    path = pathops.Path()
    rec = DecomposingRecordingPen(glyph_set)
    glyph_set[name].draw(rec)
    rec.replay(path.getPen())
    path.convertConicsToQuads()
    return path


def cmap_best(font: TTFont) -> dict[int, str]:
    cmap = font.getBestCmap() or {}
    return cmap


def codepoint_name(font: TTFont, ch: str) -> str | None:
    if len(ch) != 1:
        # allow "U+4E2D" style
        s = ch.strip()
        if s.upper().startswith("U+"):
            cp = int(s[2:], 16)
        else:
            return None
    else:
        cp = ord(ch)
    return cmap_best(font).get(cp)


def _quad_point(p0, p1, p2, t: float):
    u = 1.0 - t
    return (
        u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
        u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
    )


def path_to_polylines(path: pathops.Path, quad_steps: int = 10) -> list[list[tuple[float, float]]]:
    """Flatten pathops path into closed polylines (line segments only)."""
    polylines: list[list[tuple[float, float]]] = []
    # pathops Path supports iteration via .contours when available; fall back to pen dump
    try:
        contours = list(path.contours)
    except Exception:
        contours = None

    if contours is not None and contours and hasattr(contours[0], "__iter__"):
        # Newer pathops: each contour is iterable of (verb, points)
        for contour in contours:
            pts: list[tuple[float, float]] = []
            # Use pen replay instead — more portable
            break
        else:
            pass

    # Portable: draw into a recording-like structure via pathops getPen reverse is hard.
    # Use path.pen API: convert by stroking nothing — use svg-like segments from bounds sample.
    # Actually pathops.Path has .toSVG() / dump; use RecordingPen via fontTools again on path.draw
    from fontTools.pens.recordingPen import RecordingPen

    rec = RecordingPen()
    path.draw(rec)
    current: list[tuple[float, float]] = []
    start: tuple[float, float] | None = None
    last: tuple[float, float] | None = None

    for op, args in rec.value:
        if op == "moveTo":
            if current and start is not None:
                if current[-1] != start:
                    current.append(start)
                polylines.append(current)
            start = (float(args[0][0]), float(args[0][1]))
            last = start
            current = [start]
        elif op == "lineTo":
            p = (float(args[0][0]), float(args[0][1]))
            current.append(p)
            last = p
        elif op == "qCurveTo":
            # args are control points then end; may be multi
            pts = [(float(a[0]), float(a[1])) for a in args]
            assert last is not None
            # fontTools qCurveTo can have multiple offs; use sequential implied on-curve midpoints
            # Standard: all but last are off, last is on — or all off with implied on.
            if len(pts) == 1:
                # rare
                current.append(pts[0])
                last = pts[0]
                continue
            # Decompose super-bezier style: midpoints between consecutive off-curves
            on_off = pts
            # Treat as sequence of quads from last (on) through controls
            # FontTools: qCurveTo(*off_points, on_point) OR all off
            if len(on_off) >= 2:
                # If last point is treated as on-curve (normal)
                controls = on_off[:-1]
                end = on_off[-1]
                # Walk with implied on-curve points between consecutive offs
                chain = [last] + controls + [end]
                # Convert off-curve chain to quads (TrueType style)
                # Simplified: sample poly from last to end through first control only when single
                if len(controls) == 1:
                    p0, p1, p2 = last, controls[0], end
                    for i in range(1, quad_steps + 1):
                        t = i / quad_steps
                        current.append(_quad_point(p0, p1, p2, t))
                    last = end
                else:
                    # multi off: insert midpoints as on-curve
                    i = 0
                    p_on = last
                    offs = controls
                    while i < len(offs):
                        if i == len(offs) - 1:
                            p0, p1, p2 = p_on, offs[i], end
                            for j in range(1, quad_steps + 1):
                                t = j / quad_steps
                                current.append(_quad_point(p0, p1, p2, t))
                            p_on = end
                            break
                        else:
                            mid = (
                                (offs[i][0] + offs[i + 1][0]) / 2,
                                (offs[i][1] + offs[i + 1][1]) / 2,
                            )
                            p0, p1, p2 = p_on, offs[i], mid
                            for j in range(1, quad_steps + 1):
                                t = j / quad_steps
                                current.append(_quad_point(p0, p1, p2, t))
                            p_on = mid
                            i += 1
                    last = end
        elif op == "curveTo":
            # cubic: sample
            assert last is not None
            p0 = last
            p1 = (float(args[0][0]), float(args[0][1]))
            p2 = (float(args[1][0]), float(args[1][1]))
            p3 = (float(args[2][0]), float(args[2][1]))
            for i in range(1, quad_steps + 1):
                t = i / quad_steps
                u = 1 - t
                x = (
                    u * u * u * p0[0]
                    + 3 * u * u * t * p1[0]
                    + 3 * u * t * t * p2[0]
                    + t * t * t * p3[0]
                )
                y = (
                    u * u * u * p0[1]
                    + 3 * u * u * t * p1[1]
                    + 3 * u * t * t * p2[1]
                    + t * t * t * p3[1]
                )
                current.append((x, y))
            last = p3
        elif op == "closePath":
            if current and start is not None:
                if current[-1] != start:
                    current.append(start)
                polylines.append(current)
            current = []
            start = None
            last = None
        elif op == "endPath":
            if current:
                polylines.append(current)
            current = []
            start = None
            last = None

    if current:
        polylines.append(current)
    return polylines


def _edge_crossings_x(polylines, y: float) -> list[float]:
    xs: list[float] = []
    for poly in polylines:
        for i in range(len(poly) - 1):
            x0, y0 = poly[i]
            x1, y1 = poly[i + 1]
            if y0 == y1:
                continue
            # include lower endpoint, exclude upper → stable fill rule
            ymin, ymax = (y0, y1) if y0 < y1 else (y1, y0)
            if not (ymin <= y < ymax):
                continue
            t = (y - y0) / (y1 - y0)
            xs.append(x0 + t * (x1 - x0))
    xs.sort()
    return xs


def _edge_crossings_y(polylines, x: float) -> list[float]:
    ys: list[float] = []
    for poly in polylines:
        for i in range(len(poly) - 1):
            x0, y0 = poly[i]
            x1, y1 = poly[i + 1]
            if x0 == x1:
                continue
            xmin, xmax = (x0, x1) if x0 < x1 else (x1, x0)
            if not (xmin <= x < xmax):
                continue
            t = (x - x0) / (x1 - x0)
            ys.append(y0 + t * (y1 - y0))
    ys.sort()
    return ys


def _runs_from_crossings(crossings: list[float], min_run: float = 1.0) -> list[float]:
    """Pair sorted edge crossings into interior runs; return run lengths."""
    lengths: list[float] = []
    # even-odd pairing
    i = 0
    while i + 1 < len(crossings):
        a, b = crossings[i], crossings[i + 1]
        w = b - a
        if w >= min_run:
            lengths.append(w)
        i += 2
    return lengths


def bbox_of(polylines) -> tuple[float, float, float, float] | None:
    xs = [p[0] for poly in polylines for p in poly]
    ys = [p[1] for poly in polylines for p in poly]
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def measure_stems(
    polylines,
    *,
    samples: int = 48,
    stem_max_ratio: float = 0.28,
    min_stem: float = 4.0,
) -> dict:
    """Estimate vertical & horizontal stem widths via scanline ink-run clustering.

    Vertical stems: on horizontal scanlines, ink runs that are *narrow* relative
    to glyph width (stem-like, not counters/full body).
    Horizontal stems: same on vertical scanlines.
    """
    bb = bbox_of(polylines)
    if not bb:
        return {"v_stems": [], "h_stems": [], "v_median": None, "h_median": None}
    x0, y0, x1, y1 = bb
    gw, gh = max(x1 - x0, 1.0), max(y1 - y0, 1.0)
    v_max = gw * stem_max_ratio
    h_max = gh * stem_max_ratio

    v_runs: list[float] = []
    # Avoid extreme y (serifs / caps) — use central 60%
    for i in range(samples):
        t = 0.2 + 0.6 * (i + 0.5) / samples
        y = y0 + t * gh
        runs = _runs_from_crossings(_edge_crossings_x(polylines, y), min_run=min_stem)
        for r in runs:
            if min_stem <= r <= v_max:
                v_runs.append(r)

    h_runs: list[float] = []
    for i in range(samples):
        t = 0.2 + 0.6 * (i + 0.5) / samples
        x = x0 + t * gw
        runs = _runs_from_crossings(_edge_crossings_y(polylines, x), min_run=min_stem)
        for r in runs:
            if min_stem <= r <= h_max:
                h_runs.append(r)

    def med(xs: list[float]) -> float | None:
        return float(statistics.median(xs)) if xs else None

    return {
        "v_stems": v_runs,
        "h_stems": h_runs,
        "v_median": med(v_runs),
        "h_median": med(h_runs),
        "v_n": len(v_runs),
        "h_n": len(h_runs),
        "bbox": bb,
    }


def measure_char(font: TTFont, ch: str, glyph_set=None) -> dict | None:
    name = codepoint_name(font, ch)
    if not name:
        return None
    glyph_set = glyph_set or font.getGlyphSet()
    try:
        path = glyph_to_path(glyph_set, name)
    except Exception as e:
        return {"char": ch, "glyph": name, "error": str(e)}
    if not list(path.contours):
        return {"char": ch, "glyph": name, "error": "empty"}
    polys = path_to_polylines(path)
    m = measure_stems(polys)
    width = font["hmtx"].metrics.get(name, (0, 0))[0]
    return {
        "char": ch,
        "glyph": name,
        "advance": width,
        "v_median": m["v_median"],
        "h_median": m["h_median"],
        "v_n": m["v_n"],
        "h_n": m["h_n"],
    }


def measure_set(font: TTFont, chars: list[str]) -> list[dict]:
    gs = font.getGlyphSet()
    out = []
    for ch in chars:
        r = measure_char(font, ch, gs)
        if r is not None:
            out.append(r)
    return out


def summarize(rows: list[dict], label: str) -> dict:
    vs = [r["v_median"] for r in rows if r.get("v_median") is not None]
    hs = [r["h_median"] for r in rows if r.get("h_median") is not None]
    # Combined optical stroke ≈ mean of available v/h medians per glyph
    combined = []
    for r in rows:
        parts = [x for x in (r.get("v_median"), r.get("h_median")) if x is not None]
        if parts:
            combined.append(statistics.mean(parts))
    return {
        "label": label,
        "v_median": statistics.median(vs) if vs else None,
        "h_median": statistics.median(hs) if hs else None,
        "stroke_median": statistics.median(combined) if combined else None,
        "n_glyphs": len(rows),
        "rows": rows,
    }


def fmt_row(r: dict) -> str:
    if r.get("error"):
        return f"  {r.get('char')!r:6} glyph={r.get('glyph')} ERR {r['error']}"
    return (
        f"  {r.get('char')!r:6} adv={r.get('advance'):4}  "
        f"v={_f(r.get('v_median')):>7} (n={r.get('v_n'):3})  "
        f"h={_f(r.get('h_median')):>7} (n={r.get('h_n'):3})"
    )


def _f(x) -> str:
    return f"{x:.2f}" if x is not None else "   n/a"


def print_summary(s: dict) -> None:
    print(f"\n=== {s['label']} ===")
    for r in s["rows"]:
        print(fmt_row(r))
    print(
        f"  >> stroke_median={_f(s['stroke_median'])}  "
        f"v_median={_f(s['v_median'])}  h_median={_f(s['h_median'])}  "
        f"glyphs={s['n_glyphs']}"
    )


def open_font(path: Path, target_upm: int | None = None) -> TTFont:
    font = TTFont(str(path))
    if target_upm and font["head"].unitsPerEm != target_upm:
        scale_upem(font, target_upm)
    return font


def calibrate_embolden(
    base_cjk: Path,
    latin_font: Path,
    *,
    strengths: list[float],
    target_upm: int = 1000,
    latin_chars: list[str],
    cjk_chars: list[str],
    embolden_fn,
    work_dir: Path,
) -> list[dict]:
    """Embolden base CJK at each strength and compare stroke_median to Latin."""
    latin = open_font(latin_font, target_upm)
    latin_sum = summarize(measure_set(latin, latin_chars), f"Latin {latin_font.name}")
    print_summary(latin_sum)
    target = latin_sum["stroke_median"]
    if target is None:
        raise SystemExit("no Latin stroke measurement")

    # Scale base once
    base = open_font(base_cjk, target_upm)
    scaled = work_dir / "cjk-base-scaled.ttf"
    work_dir.mkdir(parents=True, exist_ok=True)
    base.save(str(scaled))
    base.close()

    results = []
    for s in strengths:
        out = work_dir / f"cjk-embolden-s{s:g}.ttf"
        print(f"\n--- embolden strength={s:g} → {out.name} ---", flush=True)
        embolden_fn(scaled, out, s)
        cjk = open_font(out)
        cjk_sum = summarize(measure_set(cjk, cjk_chars), f"CJK s={s:g}")
        print_summary(cjk_sum)
        cjk.close()
        sm = cjk_sum["stroke_median"]
        delta = (sm - target) if sm is not None else None
        ratio = (sm / target) if sm is not None and target else None
        results.append(
            {
                "strength": s,
                "cjk_stroke": sm,
                "latin_stroke": target,
                "delta": delta,
                "ratio": ratio,
            }
        )

    print("\n=== calibration table (CJK stroke − Latin stroke) ===")
    print(f"{'s':>8} {'cjk':>10} {'latin':>10} {'delta':>10} {'ratio':>8}")
    best = None
    for r in results:
        d = r["delta"]
        print(
            f"{r['strength']:8g} {_f(r['cjk_stroke']):>10} {_f(r['latin_stroke']):>10} "
            f"{_f(d):>10} {_f(r['ratio']):>8}"
        )
        if d is not None and (best is None or abs(d) < abs(best["delta"])):
            best = r
    if best:
        print(
            f"\nBEST strength≈{best['strength']:g}  "
            f"delta={best['delta']:+.2f}  ratio={best['ratio']:.4f}"
        )
    return results


def parse_chars(s: str) -> list[str]:
    if not s:
        return []
    # comma-separated; allow literal commas via "\,"
    parts = []
    buf = ""
    esc = False
    for c in s:
        if esc:
            buf += c
            esc = False
        elif c == "\\":
            esc = True
        elif c == ",":
            if buf:
                parts.append(buf)
            buf = ""
        else:
            buf += c
    if buf:
        parts.append(buf)
    return parts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--font", type=Path, help="single font to measure")
    ap.add_argument("--latin", type=Path, help="Latin reference font (IosevkaNSlab / MonoSlab)")
    ap.add_argument("--cjk", type=Path, help="CJK font to measure")
    ap.add_argument("--chars", type=str, default="", help="override chars for --font")
    ap.add_argument("--latin-chars", type=str, default=",".join(DEFAULT_LATIN))
    ap.add_argument("--cjk-chars", type=str, default=",".join(DEFAULT_CJK))
    ap.add_argument("--upm", type=int, default=1000, help="normalize UPM (0=off)")
    ap.add_argument(
        "--calibrate-embolden",
        type=Path,
        metavar="BASE_CJK",
        help="sweep embolden strengths on BASE_CJK vs --latin",
    )
    ap.add_argument(
        "--strengths",
        type=str,
        default="0,4,6,8,10,12,14,16,18,20,22,24",
        help="comma-separated embolden strengths for calibration",
    )
    ap.add_argument(
        "--work-dir",
        type=Path,
        default=Path("work/stroke-calibrate"),
        help="output dir for emboldened trial fonts",
    )
    args = ap.parse_args()
    upm = args.upm if args.upm > 0 else None
    latin_chars = parse_chars(args.latin_chars)
    cjk_chars = parse_chars(args.cjk_chars)

    if args.calibrate_embolden:
        if not args.latin:
            ap.error("--calibrate-embolden requires --latin")
        # import embolden from sibling module
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from embolden_cjk import embolden_font

        def do_emb(src: Path, dst: Path, strength: float) -> None:
            embolden_font(src, dst, strength, only_wide=True)

        strengths = [float(x) for x in args.strengths.split(",") if x.strip() != ""]
        calibrate_embolden(
            args.calibrate_embolden,
            args.latin,
            strengths=strengths,
            target_upm=upm or 1000,
            latin_chars=latin_chars,
            cjk_chars=cjk_chars,
            embolden_fn=do_emb,
            work_dir=args.work_dir,
        )
        return

    if args.font:
        chars = parse_chars(args.chars) if args.chars else latin_chars + cjk_chars
        font = open_font(args.font, upm)
        s = summarize(measure_set(font, chars), str(args.font))
        print_summary(s)
        font.close()
        return

    if args.latin:
        font = open_font(args.latin, upm)
        s = summarize(measure_set(font, latin_chars), f"Latin {args.latin}")
        print_summary(s)
        font.close()

    if args.cjk:
        font = open_font(args.cjk, upm)
        s = summarize(measure_set(font, cjk_chars), f"CJK {args.cjk}")
        print_summary(s)
        font.close()

    if not args.latin and not args.cjk and not args.font:
        ap.error("provide --font and/or --latin/--cjk, or --calibrate-embolden")


if __name__ == "__main__":
    main()
