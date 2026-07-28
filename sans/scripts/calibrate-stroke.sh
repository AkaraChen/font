#!/usr/bin/env bash
# Measure Lilex (Latin, product X-scale) vs Plex Sans SC (CJK) stem widths and
# recommend CJK_EMBOLDEN_* values for pins.env. Does not write pins.env.
#
# Metric: scanline vertical-stem median (shared lib/fontkit/measure.py).
# Latin is X-scaled EN_ADV/LILEX_SRC_ADV so the target matches the merge product.
# Lilex Bold stems are wide relative to glyph bbox — use stem_max_ratio=0.40.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/tools/diagnostic.sh"

log "realising the source steps"
LILEX_R="$(step src-latin-Regular)/Lilex-Regular.ttf"
LILEX_B="$(step src-latin-Bold)/Lilex-Bold.ttf"
PLEX_R="$(step src-cjk-Regular)/IBMPlexSansSC-Regular.ttf"
PLEX_B="$(step src-cjk-Bold)/IBMPlexSansSC-Bold.ttf"

CAL_DIR="${FAMILY_ROOT}/work/stroke-calibrate"
mkdir -p "${CAL_DIR}"

STRENGTHS_REG="${STRENGTHS_REG:-0,1,2,3,4,5,5.5,6,7,8,10}"
STRENGTHS_BOLD="${STRENGTHS_BOLD:-0,1,2,3,4,5,6,8,10,12}"
export CAL_DIR EN_ADV LILEX_SRC_ADV UPM
export STRENGTHS_REG STRENGTHS_BOLD
export LATIN_REG="${LILEX_R}"
export LATIN_BOLD="${LILEX_B}"
export CJK_REG="${PLEX_R}"
export CJK_BOLD="${PLEX_B}"

log "measure + calibrate embolden (subset CJK; Latin at product X-scale)"
python3 - <<'PY'
from __future__ import annotations
import os
import statistics
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter, Options
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

from fontkit.embolden import embolden_font
from fontkit.measure import (
    DEFAULT_CJK,
    DEFAULT_LATIN,
    codepoint_name,
    glyph_to_path,
    measure_stems,
    open_font,
    path_to_polylines,
)

# Lilex Bold verticals exceed the default 0.28×bbox filter; 0.40 covers them
# without swallowing full counters on CJK sample glyphs.
STEM_MAX_RATIO = 0.40


def scale_latin_x(src: Path, dst: Path, scale: float, src_adv: int, en_adv: int) -> None:
    """Match merge_plex.py X-scale so stem targets equal the product face."""
    font = TTFont(str(src))
    glyf = font["glyf"]
    hmtx = font["hmtx"].metrics
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.numberOfContours == 0:
            continue
        if g.isComposite():
            for c in g.components:
                c.x = int(round(c.x * scale))
                if hasattr(c, "transform"):
                    xx, xy, yx, yy = c.transform
                    c.transform = (xx * scale, xy, yx * scale, yy)
            try:
                g.recalcBounds(glyf)
            except Exception:
                pass
            continue
        if g.coordinates:
            g.coordinates = GlyphCoordinates(
                [(int(round(x * scale)), y) for x, y in g.coordinates]
            )
            try:
                g.recalcBounds(glyf)
            except Exception:
                pass
        old_w, old_lsb = hmtx[name]
        new_lsb = int(round(old_lsb * scale))
        if old_w == 0:
            hmtx[name] = (0, new_lsb)
        elif src_adv and old_w == src_adv:
            hmtx[name] = (en_adv, new_lsb)
        else:
            hmtx[name] = (max(0, int(round(old_w * scale))), new_lsb)
    dst.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(dst))
    font.close()


def v_median(font: TTFont, chars: list[str]) -> float:
    gs = font.getGlyphSet()
    vs: list[float] = []
    rows: list[str] = []
    for ch in chars:
        name = codepoint_name(font, ch)
        if not name:
            rows.append(f"  {ch!r:6} missing")
            continue
        try:
            path = glyph_to_path(gs, name)
            if not list(path.contours):
                rows.append(f"  {ch!r:6} empty")
                continue
            m = measure_stems(
                path_to_polylines(path), stem_max_ratio=STEM_MAX_RATIO
            )
            adv = font["hmtx"].metrics.get(name, (0, 0))[0]
            rows.append(
                f"  {ch!r:6} adv={adv:4}  v={_f(m['v_median']):>7}  h={_f(m['h_median']):>7}"
            )
            if m["v_median"] is not None:
                vs.append(m["v_median"])
        except Exception as e:
            rows.append(f"  {ch!r:6} skip ({e})")
    for line in rows:
        print(line)
    if not vs:
        raise SystemExit("no vertical stems measured")
    return float(statistics.median(vs))


def _f(x) -> str:
    return f"{x:.2f}" if x is not None else "   n/a"


cal = Path(os.environ["CAL_DIR"])
upm = int(os.environ.get("UPM", "1000"))
en_adv = int(os.environ["EN_ADV"])
src_adv = int(os.environ["LILEX_SRC_ADV"])
scale = en_adv / src_adv

latin_reg_p = cal / "Lilex-Regular-scaled.ttf"
latin_bold_p = cal / "Lilex-Bold-scaled.ttf"
print(f"X-scale Latin * {scale:.6f} ({src_adv} → {en_adv})")
scale_latin_x(Path(os.environ["LATIN_REG"]), latin_reg_p, scale, src_adv, en_adv)
scale_latin_x(Path(os.environ["LATIN_BOLD"]), latin_bold_p, scale, src_adv, en_adv)

print("\n=== Latin Regular (Lilex @ product scale) ===")
latin_reg = open_font(latin_reg_p, upm)
tr = v_median(latin_reg, DEFAULT_LATIN)
print(f"  >> v_median={tr:.2f}")
latin_reg.close()

print("\n=== Latin Bold (Lilex @ product scale) ===")
latin_bold = open_font(latin_bold_p, upm)
tb = v_median(latin_bold, DEFAULT_LATIN)
print(f"  >> v_median={tb:.2f}")
latin_bold.close()


def subset_cjk(src: Path, dst: Path) -> None:
    opts = Options()
    opts.layout_closure = False
    sub = Subsetter(options=opts)
    sub.populate(unicodes=[ord(c) for c in DEFAULT_CJK])
    font = TTFont(str(src))
    sub.subset(font)
    font.save(str(dst))
    font.close()


def sweep(strengths: list[float], target_v: float, tag: str, cjk_src: Path) -> float:
    sub_path = cal / f"{tag}-cjk-subset.ttf"
    subset_cjk(cjk_src, sub_path)
    print(f"\n=== sweep {tag} (target Latin v_median={target_v:.2f}) ===")
    print(f"{'s':>8} {'v':>8} {'dv':>8}")
    best_s, best_abs = 0.0, None
    for s in strengths:
        out = cal / f"{tag}-s{s:g}.ttf"
        embolden_font(sub_path, out, float(s), only_wide=True)
        f = open_font(out, upm)
        v = v_median(f, DEFAULT_CJK)
        f.close()
        # collapse per-glyph noise in sweep table
        # re-measure quietly: just print summary line (v_median already computed)
        dv = v - target_v
        print(f"{s:8g} {v:8.2f} {dv:+8.2f}")
        if best_abs is None or abs(dv) < best_abs:
            best_abs = abs(dv)
            best_s = s
    assert best_abs is not None
    print(f"→ recommended {tag}: s={best_s:g} (|dv|={best_abs:.2f})")
    return float(best_s)


def parse_s(s: str) -> list[float]:
    return [float(x) for x in s.split(",") if x.strip() != ""]


print("\n=== CJK Regular baseline (s=0) ===")
f = open_font(Path(os.environ["CJK_REG"]), upm)
print(f"  >> v_median={v_median(f, DEFAULT_CJK):.2f}")
f.close()

print("\n=== CJK Bold baseline (s=0) ===")
f = open_font(Path(os.environ["CJK_BOLD"]), upm)
print(f"  >> v_median={v_median(f, DEFAULT_CJK):.2f}")
f.close()

# Quiet redefinition of v_median for sweep (no per-glyph dump)
def v_median(font: TTFont, chars: list[str]) -> float:  # noqa: F811
    gs = font.getGlyphSet()
    vs: list[float] = []
    for ch in chars:
        name = codepoint_name(font, ch)
        if not name:
            continue
        try:
            path = glyph_to_path(gs, name)
            if not list(path.contours):
                continue
            m = measure_stems(
                path_to_polylines(path), stem_max_ratio=STEM_MAX_RATIO
            )
            if m["v_median"] is not None:
                vs.append(m["v_median"])
        except Exception:
            continue
    if not vs:
        return float("nan")
    return float(statistics.median(vs))


rec_r = sweep(
    parse_s(os.environ["STRENGTHS_REG"]),
    tr,
    "regular",
    Path(os.environ["CJK_REG"]),
)
rec_b = sweep(
    parse_s(os.environ["STRENGTHS_BOLD"]),
    tb,
    "bold",
    Path(os.environ["CJK_BOLD"]),
)

print("\n=== pins.env suggestion ===")
print(f"CJK_EMBOLDEN_REGULAR={rec_r:g}")
print(f"CJK_EMBOLDEN_BOLD={rec_b:g}")
print(
    "\nNotes: vertical-stem median is the primary gate (coding mono). "
    "Plex Sans SC runs lighter than Lilex after the 600→EN X-scale; embolden "
    "closes the gap. stem_max_ratio=0.40 is required for Lilex Bold stems."
)
print(
    f"Latin targets (product X-scale {src_adv}→{en_adv}): "
    f"Regular v≈{tr:.1f}  Bold v≈{tb:.1f}"
)
PY

log "done. Compare recommendations with pins.env (CJK_EMBOLDEN_REGULAR / CJK_EMBOLDEN_BOLD)."
