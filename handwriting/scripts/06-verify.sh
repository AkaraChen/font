#!/usr/bin/env bash
# Gates: strict 2:1 + EAW + Nerd icon cells (shared fontkit gate), Radon features,
# and the measured CJK/Latin stroke match.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

PY="$(python_bin)"
shopt -s nullglob
stem="${PRODUCT_STEM:-RadonWenKaiNFM}"
fonts=("${OUT_DIR}/${stem}"-*.ttf)
[[ ${#fonts[@]} -gt 0 ]] || die "no products in ${OUT_DIR}; run 04-merge.sh first"

# The dense profile is the gate serif defined; same rules apply to any 2:1
# Nerd mono in this repo.
log "verify 2:1 + EAW + Nerd cells"
"${PY}" -m fontkit.verify2to1 --profile dense --check-nerd --check-eaw "${fonts[@]}"

log "verify Radon coding features (liga / calt / ss / cv)"
"${PY}" "${HANDWRITING_ROOT}/scripts/verify-features.py" --expect-half "${EN_ADV}" "${fonts[@]}"

log "stroke match (CJK vs Latin, in the shipped products)"
for font in "${fonts[@]}"; do
  "${PY}" -m fontkit.measure --font "${font}" | tail -20
done
