#!/usr/bin/env bash
# Measure Latin vs CJK stem widths and optionally sweep embolden strengths.
# Updates suggested CJK_EMBOLDEN_* values for pins.env (does not write pins).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"
# skia-pathops already required by ensure_python

LAT_R="${EXTRACT_DIR}/MonaspaceRadon-Regular.ttf"
LAT_B="${EXTRACT_DIR}/MonaspaceRadon-Bold.ttf"
CJK="${EXTRACT_DIR}/LXGWWenKai-Medium.ttf"
[[ -f "${LAT_R}" && -f "${CJK}" ]] || die "run 01-fetch-sources.sh first"

MEASURE="${RADON_ROOT}/tools/measure_stroke_width.py"
WORK="${WORK_DIR}/stroke-calibrate"
mkdir -p "${WORK}"

# Normalize Radon to TARGET_UPM for fair comparison
"${PY}" - <<PY
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
from pathlib import Path
upm = ${TARGET_UPM}
for src, dst in [
    ("${LAT_R}", "${WORK}/radon-regular-${TARGET_UPM}.ttf"),
    ("${LAT_B}", "${WORK}/radon-bold-${TARGET_UPM}.ttf"),
]:
    f = TTFont(src)
    if f["head"].unitsPerEm != upm:
        scale_upem(f, upm)
    f.save(dst)
    f.close()
    print("wrote", dst)
PY

log "baseline measure (Radon Regular/Bold vs WenKai Medium)"
"${PY}" "${MEASURE}" \
  --latin "${WORK}/radon-regular-${TARGET_UPM}.ttf" \
  --cjk "${CJK}" \
  --upm "${TARGET_UPM}"

log "embolden calibration sweep (Regular target = Radon Regular stroke)"
"${PY}" "${MEASURE}" \
  --calibrate-embolden "${CJK}" \
  --latin "${WORK}/radon-regular-${TARGET_UPM}.ttf" \
  --strengths "0,4,8,10,12,14,16,18,20" \
  --work-dir "${WORK}/reg" \
  --upm "${TARGET_UPM}"

log "embolden calibration sweep (Bold target = Radon Bold stroke)"
"${PY}" "${MEASURE}" \
  --calibrate-embolden "${CJK}" \
  --latin "${WORK}/radon-bold-${TARGET_UPM}.ttf" \
  --strengths "24,32,40,44,48,52,56,60" \
  --work-dir "${WORK}/bld" \
  --upm "${TARGET_UPM}"

log "done. Copy BEST strengths into pins.env CJK_EMBOLDEN_REGULAR / CJK_EMBOLDEN_BOLD"
