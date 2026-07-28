#!/usr/bin/env bash
# Render dark/light mixed samples of the merged product.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/tools/diagnostic.sh"

# The renderer used to live under ../handwriting/scripts/ and be reached by a
# hardcoded relative path — one of the cross-family references this phase
# removed. It is a repo tool now; nothing under casual/ points at another
# family.
RENDER="${REPO_ROOT}/tools/render-sample.py"

font="$(step merged-Regular)/${PRODUCT_STEM}-Regular.ttf"
OUT="${FAMILY_ROOT}/samples/rendered"
mkdir -p "${OUT}"

python3 "${RENDER}" \
  --font "${font}" \
  --out-dir "${OUT}" \
  --title "${FAMILY_NAME} · EN ${EN_ADV}/CJK ${CJK_ADV} · stroke-matched" \
  --body-file "${FAMILY_ROOT}/samples/coding-mixed.txt" \
  --size 16

log "wrote samples under ${OUT}"
ls -lh "${OUT}"
