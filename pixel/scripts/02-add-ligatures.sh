#!/usr/bin/env bash
# Install the hand-drawn pixel ligatures into Fusion 12px mono + inject calt GSUB.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

BASE="${EXTRACT_DIR}/staged/fusion-base.ttf"
ART="${PIXEL_ROOT}/ligatures/ligatures.txt"
[[ -f "${BASE}" ]] || die "missing ${BASE}; run 01-fetch-sources.sh"
[[ -f "${ART}" ]] || die "missing ${ART}"

OUT_TTF="${OUT_DIR}/${BASE_FAMILY_PS}-Regular.ttf"
mkdir -p "${OUT_DIR}"

log "hand-drawn ligatures → ${OUT_TTF}"
"${PY}" "${PIXEL_ROOT}/scripts/build_ligatures.py" \
  --base "${BASE}" \
  --art "${ART}" \
  --out "${OUT_TTF}" \
  --family "${BASE_FAMILY_NAME}" \
  --family-ps "${BASE_FAMILY_PS}" \
  --half "${EN_ADV}" \
  --px "${PX_UNIT}" \
  --ascent "${HHEA_ASCENT}"

log "done. intermediate: ${OUT_TTF}"
ls -lh "${OUT_TTF}"
