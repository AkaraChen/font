#!/usr/bin/env bash
# Prepare Zhuque CJK: optional Regular embolden + Bold stem-matched embolden.
# Latin Bold is real Courier Prime Bold; CJK only ships Regular upstream.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

SRC="${EXTRACT_DIR}/ZhuqueFangsong-Regular.ttf"
[[ -f "${SRC}" ]] || die "missing ${SRC}; run 01-fetch-sources.sh first"
[[ -f "${SERIF_TOOLS}/embolden_cjk.py" ]] || die "missing ${SERIF_TOOLS}/embolden_cjk.py"

OUT_REG="${EXTRACT_DIR}/ZhuqueFangsong-Regular-prepared.ttf"
OUT_BOLD="${EXTRACT_DIR}/ZhuqueFangsong-Bold-prepared.ttf"

REG_STR="${CJK_EMBOLDEN_REGULAR:-0}"
BOLD_STR="${CJK_EMBOLDEN_BOLD:-32}"

if awk "BEGIN{exit !(${REG_STR} > 0)}"; then
  log "CJK Regular: embolden strength=${REG_STR}"
  "${PY}" "${SERIF_TOOLS}/embolden_cjk.py" "${SRC}" "${OUT_REG}" --strength "${REG_STR}"
else
  log "CJK Regular: copy upstream (no embolden)"
  cp "${SRC}" "${OUT_REG}"
fi

log "CJK Bold: embolden strength=${BOLD_STR} (match Courier Prime Bold vertical stems)"
"${PY}" "${SERIF_TOOLS}/embolden_cjk.py" "${SRC}" "${OUT_BOLD}" --strength "${BOLD_STR}"

log "prepared CJK:"
ls -lh "${OUT_REG}" "${OUT_BOLD}"
