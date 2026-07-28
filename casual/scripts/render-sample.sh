#!/usr/bin/env bash
# Render dark/light mixed samples of the merged product.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

PY="$(python_bin)"
RENDER="${HANDWRITING_SCRIPTS}/render-sample.py"
[[ -f "${RENDER}" ]] || die "missing ${RENDER}"

stem="${PRODUCT_STEM:-RecursiveYozaiDual}"
font="${OUT_DIR}/${stem}-Regular.ttf"
[[ -f "${font}" ]] || die "missing ${font}; run build first"

OUT="${CASUAL_ROOT}/samples/rendered"
mkdir -p "${OUT}"
BODY="${CASUAL_ROOT}/samples/coding-mixed.txt"

"${PY}" "${RENDER}" \
  --font "${font}" \
  --out-dir "${OUT}" \
  --title "${FAMILY_NAME} · EN ${EN_ADV}/CJK ${CJK_ADV} · stroke-matched" \
  --body-file "${BODY}" \
  --size 16

log "wrote samples under ${OUT}"
ls -lh "${OUT}"
