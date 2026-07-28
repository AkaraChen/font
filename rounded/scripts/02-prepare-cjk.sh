#!/usr/bin/env bash
# Optional pathops embolden on RHR masters (pins CJK_EMBOLDEN_*).
# RHR ships real Regular + Bold — default pins are 0 (use masters as-is).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

SRC_REG="${EXTRACT_DIR}/RHR-Regular.ttf"
SRC_BOLD="${EXTRACT_DIR}/RHR-Bold.ttf"
[[ -f "${SRC_REG}" ]] || die "missing ${SRC_REG}; run 01-fetch-sources.sh first"
[[ -f "${SRC_BOLD}" ]] || die "missing ${SRC_BOLD}; run 01-fetch-sources.sh first"
[[ -f "${SERIF_TOOLS}/embolden_cjk.py" ]] || die "missing ${SERIF_TOOLS}/embolden_cjk.py"

OUT_REG="${EXTRACT_DIR}/RHR-Regular-prepared.ttf"
OUT_BOLD="${EXTRACT_DIR}/RHR-Bold-prepared.ttf"

REG_STR="${CJK_EMBOLDEN_REGULAR:-0}"
BOLD_STR="${CJK_EMBOLDEN_BOLD:-0}"

embolden_or_copy() {
  local src="$1" dst="$2" strength="$3" label="$4"
  if awk "BEGIN{exit !(${strength} > 0)}"; then
    log "CJK ${label}: embolden strength=${strength}"
    "${PY}" "${SERIF_TOOLS}/embolden_cjk.py" "${src}" "${dst}" --strength "${strength}"
  else
    log "CJK ${label}: copy master (no embolden)"
    cp "${src}" "${dst}"
  fi
}

embolden_or_copy "${SRC_REG}" "${OUT_REG}" "${REG_STR}" "Regular"
embolden_or_copy "${SRC_BOLD}" "${OUT_BOLD}" "${BOLD_STR}" "Bold"

log "prepared CJK:"
ls -lh "${OUT_REG}" "${OUT_BOLD}"
