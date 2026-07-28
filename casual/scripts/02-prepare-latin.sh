#!/usr/bin/env bash
# Recursive Mono Casual (600 cell) → half-cell 500 @ UPM 1000 (uniform scale).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

for weight in Regular Bold; do
  src="${EXTRACT_DIR}/RecursiveMonoCsl-${weight}.ttf"
  [[ -f "${src}" ]] || die "missing ${src}; run 01-fetch-sources.sh first"
  log "preparing Latin ${weight} (${LATIN_SRC_ADV} → ${EN_ADV})"
  "${PY}" "${CASUAL_ROOT}/scripts/prepare_latin.py" \
    "${src}" "${STAGE_DIR}/RecursiveLatin-${weight}.ttf" \
    --src-adv "${LATIN_SRC_ADV}" \
    --en-adv "${EN_ADV}" \
    --uniform
done

ls -lh "${STAGE_DIR}"/RecursiveLatin-*.ttf
