#!/usr/bin/env bash
# Yozai → measured embolden (stroke match), full cell 1000 kept. No slant.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"
[[ -f "${HANDWRITING_SCRIPTS}/prepare_cjk.py" ]] \
  || die "missing ${HANDWRITING_SCRIPTS}/prepare_cjk.py (handwriting product required)"

prepare() {
  local face="$1" yozai_weight="$2" embolden="$3"
  local src="${EXTRACT_DIR}/Yozai-${yozai_weight}.ttf"
  [[ -f "${src}" ]] || die "missing ${src}; run 01-fetch-sources.sh first"
  log "preparing CJK ${face} from Yozai ${yozai_weight} (embolden=${embolden}, slant=${CJK_SLANT_DEG}°)"
  "${PY}" "${HANDWRITING_SCRIPTS}/prepare_cjk.py" \
    "${src}" "${STAGE_DIR}/YozaiPrepared-${face}.ttf" \
    --embolden "${embolden}" \
    --slant-deg "${CJK_SLANT_DEG}" \
    --pivot-y "${CJK_SLANT_PIVOT_Y}"
}

prepare Regular "${YOZAI_FOR_REGULAR}" "${CJK_EMBOLDEN_REGULAR}"
prepare Bold "${YOZAI_FOR_BOLD}" "${CJK_EMBOLDEN_BOLD}"

ls -lh "${STAGE_DIR}"/YozaiPrepared-*.ttf
