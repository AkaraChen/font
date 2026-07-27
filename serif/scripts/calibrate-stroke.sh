#!/usr/bin/env bash
# Measure IosevkaNSlab (Latin) vs Neo ZhiSong (CJK) stem widths and recommend
# CJK_EMBOLDEN_* values for pins.env. Does not write pins.env automatically.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

need_cmd curl
need_cmd python3
ensure_dirs

# venv
if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  log "creating venv ${VENV_DIR}"
  if command -v uv >/dev/null 2>&1; then
    uv venv "${VENV_DIR}"
    uv pip install --python "${VENV_DIR}/bin/python" fonttools skia-pathops py7zr
  else
    python3 -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/pip" install -U pip
    "${VENV_DIR}/bin/pip" install fonttools skia-pathops py7zr
  fi
fi
PY="${VENV_DIR}/bin/python"

# Ensure py7zr for archive extract (optional if latin already present)
"${PY}" -c "import py7zr" 2>/dev/null || {
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "${PY}" py7zr
  else
    "${VENV_DIR}/bin/pip" install py7zr
  fi
}

LATIN_DIR="${DOWNLOADS_DIR}/sarasa_mono_slab"
LATIN_REG="${LATIN_DIR}/SarasaMonoSlabSC-Regular.ttf"
LATIN_BOLD="${LATIN_DIR}/SarasaMonoSlabSC-Bold.ttf"
CJK_SRC="${DOWNLOADS_DIR}/${LXGW_ASSET}"
CJK_SCALED="${DOWNLOADS_DIR}/LXGWNeoZhiSong-UPM${CJK_TARGET_UPM}.ttf"
CAL_DIR="${WORK_DIR}/stroke-calibrate"
mkdir -p "${CAL_DIR}" "${LATIN_DIR}"

if [[ ! -f "${CJK_SRC}" ]]; then
  log "downloading ${LXGW_URL}"
  curl -fL --retry 3 -o "${CJK_SRC}.partial" "${LXGW_URL}"
  mv "${CJK_SRC}.partial" "${CJK_SRC}"
fi

if [[ ! -f "${LATIN_REG}" || ! -f "${LATIN_BOLD}" ]]; then
  ARC="${DOWNLOADS_DIR}/SarasaMonoSlabSC-TTF-Unhinted-${SARASA_REF#v}.7z"
  URL="https://github.com/be5invis/Sarasa-Gothic/releases/download/${SARASA_REF}/SarasaMonoSlabSC-TTF-Unhinted-${SARASA_REF#v}.7z"
  if [[ ! -f "${ARC}" ]]; then
    log "downloading Latin reference ${URL}"
    curl -fL --retry 3 -o "${ARC}.partial" "${URL}"
    mv "${ARC}.partial" "${ARC}"
  fi
  log "extracting MonoSlab SC (Latin = IosevkaNSlab)"
  "${PY}" - <<PY
from py7zr import SevenZipFile
from pathlib import Path
arc = Path(${ARC@Q})
out = Path(${LATIN_DIR@Q})
out.mkdir(parents=True, exist_ok=True)
with SevenZipFile(arc, "r") as z:
    z.extractall(path=out)
print("extracted to", out)
PY
fi

log "scale CJK UPM → ${CJK_TARGET_UPM}"
"${PY}" - <<PY
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
from pathlib import Path
src = Path(${CJK_SRC@Q})
dst = Path(${CJK_SCALED@Q})
font = TTFont(src)
upm = font["head"].unitsPerEm
target = int(${CJK_TARGET_UPM@Q})
if upm != target:
    scale_upem(font, target)
font.save(dst)
print(f"saved {dst} UPM={TTFont(dst)['head'].unitsPerEm} (from {upm})")
PY

log "measure + calibrate embolden (subset glyphs; fast)"
STRENGTHS_REG="${STRENGTHS_REG:-0,4,6,7,7.5,8,9,10,12,14}"
STRENGTHS_BOLD="${STRENGTHS_BOLD:-16,20,22,24,26,28,32}"
export SERIF_ROOT PY LATIN_REG LATIN_BOLD CJK_SCALED CAL_DIR CJK_TARGET_UPM
export STRENGTHS_REG STRENGTHS_BOLD
export MEASURE_PY="${SERIF_ROOT}/tools/measure_stroke_width.py"
export EMBOLDEN_PY="${SERIF_ROOT}/tools/embolden_cjk.py"

"${PY}" - <<'PY'
from __future__ import annotations
import os
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter, Options

sys.path.insert(0, str(Path(os.environ["SERIF_ROOT"]) / "tools"))
from embolden_cjk import embolden_font
from measure_stroke_width import (
    DEFAULT_CJK,
    DEFAULT_LATIN,
    measure_set,
    open_font,
    print_summary,
    summarize,
)

cal = Path(os.environ["CAL_DIR"])
upm = int(os.environ["CJK_TARGET_UPM"])
latin_reg = open_font(Path(os.environ["LATIN_REG"]), upm)
latin_bold = open_font(Path(os.environ["LATIN_BOLD"]), upm)
cjk_scaled = Path(os.environ["CJK_SCALED"])

sr = summarize(measure_set(latin_reg, DEFAULT_LATIN), "Latin Regular (IosevkaNSlab)")
sb = summarize(measure_set(latin_bold, DEFAULT_LATIN), "Latin Bold (IosevkaNSlab)")
print_summary(sr)
print_summary(sb)

# subset CJK for speed
opts = Options()
opts.layout_closure = False
sub = Subsetter(options=opts)
sub.populate(unicodes=[ord(c) for c in DEFAULT_CJK])
cjk = TTFont(str(cjk_scaled))
sub.subset(cjk)
sub_path = cal / "cjk-subset-base.ttf"
cjk.save(str(sub_path))
cjk.close()

def sweep(strengths: list[float], target_v: float, tag: str) -> float | None:
    print(f"\n=== sweep {tag} (target Latin v_median={target_v:.2f}) ===")
    print(f"{'s':>8} {'v':>8} {'dv':>8} {'中.v':>8} {'h':>8}")
    best_s, best_abs = None, None
    for s in strengths:
        out = cal / f"{tag}-s{s:g}.ttf"
        embolden_font(sub_path, out, float(s), only_wide=True)
        sm = summarize(measure_set(open_font(out), DEFAULT_CJK), f"{tag} s={s:g}")
        z = next(r for r in sm["rows"] if r["char"] == "中")
        dv = sm["v_median"] - target_v
        print(
            f"{s:8g} {sm['v_median']:8.2f} {dv:+8.2f} "
            f"{z['v_median']:8.2f} {sm['h_median']:8.2f}"
        )
        if best_abs is None or abs(dv) < best_abs:
            best_abs = abs(dv)
            best_s = s
    print(f"→ recommended {tag}: s={best_s:g} (|dv|={best_abs:.2f})")
    return best_s

def parse_s(s: str) -> list[float]:
    return [float(x) for x in s.split(",") if x.strip() != ""]

rec_r = sweep(parse_s(os.environ["STRENGTHS_REG"]), sr["v_median"], "regular")
rec_b = sweep(parse_s(os.environ["STRENGTHS_BOLD"]), sb["v_median"], "bold")

print("\n=== pins.env suggestion ===")
print(f"CJK_EMBOLDEN_REGULAR={rec_r:g}")
print(f"CJK_EMBOLDEN_BOLD={rec_b:g}")
print(
    "\nNotes: vertical-stem median is the primary gate (coding mono). "
    "Song-style CJK horizontals stay thinner by design; matching v-stems "
    "removes the 'CJK slightly heavier than Latin' look without over-emboldening."
)
PY

log "done. Compare recommendations with pins.env (CJK_EMBOLDEN_REGULAR / CJK_EMBOLDEN_BOLD)."
