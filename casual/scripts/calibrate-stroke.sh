#!/usr/bin/env bash
# Survey / sweep CJK embolden strength against prepared Latin stems.
# Usage (after 01-fetch + 02-prepare-latin):
#   ./scripts/calibrate-stroke.sh
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"
CAL="${HANDWRITING_SCRIPTS}/calibrate_cjk_weight.py"
[[ -f "${CAL}" ]] || die "missing ${CAL}"

LAT_R="${STAGE_DIR}/RecursiveLatin-Regular.ttf"
LAT_B="${STAGE_DIR}/RecursiveLatin-Bold.ttf"
[[ -f "${LAT_R}" ]] || die "missing ${LAT_R}; run 02-prepare-latin.sh first"

log "survey: prepared Latin vs raw Yozai"
"${PY}" "${CAL}" --survey \
  --latin "${LAT_R}" --latin "${LAT_B}" \
  --cjk "${EXTRACT_DIR}/Yozai-Regular.ttf" \
  --cjk "${EXTRACT_DIR}/Yozai-Medium.ttf"

log "sweep Regular pair (Yozai Regular → target Latin Regular)"
"${PY}" "${CAL}" \
  --latin "${LAT_R}" \
  --cjk "${EXTRACT_DIR}/Yozai-Regular.ttf" \
  --strengths 0,2,4,6,8,10,12,14,16,18,20

log "sweep Bold pair (Yozai Medium → target Latin Bold)"
"${PY}" "${CAL}" \
  --latin "${LAT_B}" \
  --cjk "${EXTRACT_DIR}/Yozai-Medium.ttf" \
  --strengths 0,4,8,12,16,20,24,28
