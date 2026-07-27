#!/usr/bin/env bash
# WenKai → weight-matched (measured) + sheared to Radon's lean, full cell kept.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

prepare() {
  local face="$1" wenkai_weight="$2" embolden="$3"
  local src="${EXTRACT_DIR}/LXGWWenKai-${wenkai_weight}.ttf"
  [[ -f "${src}" ]] || die "missing ${src}; run 01-fetch-sources.sh first"
  log "preparing CJK ${face} from WenKai ${wenkai_weight} (embolden=${embolden}, slant=${CJK_SLANT_DEG}°)"
  "${PY}" "${HANDWRITING_ROOT}/scripts/prepare_cjk.py" \
    "${src}" "${STAGE_DIR}/WenKaiSlanted-${face}.ttf" \
    --embolden "${embolden}" \
    --slant-deg "${CJK_SLANT_DEG}" \
    --pivot-y "${CJK_SLANT_PIVOT_Y}"
}

prepare Regular "${WENKAI_FOR_REGULAR}" "${CJK_EMBOLDEN_REGULAR}"
prepare Bold "${WENKAI_FOR_BOLD}" "${CJK_EMBOLDEN_BOLD}"

ls -lh "${STAGE_DIR}"/WenKaiSlanted-*.ttf
