#!/usr/bin/env bash
# Pixelize Lilex programming ligatures into Fusion 12px mono + inject calt GSUB.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

BASE="${EXTRACT_DIR}/staged/fusion-base.ttf"
DONOR="${EXTRACT_DIR}/staged/lilex-regular.ttf"
[[ -f "${BASE}" ]] || die "missing ${BASE}; run 01-fetch-sources.sh"
[[ -f "${DONOR}" ]] || die "missing ${DONOR}; run 01-fetch-sources.sh"

OUT_TTF="${OUT_DIR}/${BASE_FAMILY_PS}-Regular.ttf"
mkdir -p "${OUT_DIR}"

log "pixelize ligatures → ${OUT_TTF}"
"${PY}" "${PIXEL_ROOT}/scripts/pixelize_ligatures.py" \
  --base "${BASE}" \
  --donor "${DONOR}" \
  --out "${OUT_TTF}" \
  --family "${BASE_FAMILY_NAME}" \
  --family-ps "${BASE_FAMILY_PS}" \
  --half "${EN_ADV}" \
  --px "${PX_UNIT}" \
  --pixel-h "${PIXEL_H}" \
  --ascent "${HHEA_ASCENT}" \
  --descent "${HHEA_DESCENT}"

log "done. intermediate: ${OUT_TTF}"
ls -lh "${OUT_TTF}"
