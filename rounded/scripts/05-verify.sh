#!/usr/bin/env bash
# Gate: EN/CJK 2:1 + mono flags + EAW + Nerd PUA half-cell.
# Iosevka Curly ships coding ligatures; feature gate is optional for now.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

PY="$(python_bin)"
NERD_OUT="${OUT_DIR}/nerd"

mapfile -t NERD_FONTS < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) 2>/dev/null | sort)
if [[ ${#NERD_FONTS[@]} -gt 0 ]]; then
  FONTS=("${NERD_FONTS[@]}")
  EXTRA_GATES=(--check-nerd --check-eaw)
  log "verify Nerd products (${#FONTS[@]}) with nerd + EAW gates"
else
  shopt -s nullglob
  stem_base="${BASE_FAMILY_PS:-YuanTiDual}"
  FONTS=("${OUT_DIR}/${stem_base}"-*.ttf)
  EXTRA_GATES=(--check-eaw)
  [[ ${#FONTS[@]} -gt 0 ]] || die "no products in ${OUT_DIR}; run 03-merge.sh first"
  log "verify intermediate Dual products (${#FONTS[@]}) with EAW gate"
fi

log "verify 2:1 (expect half=${EN_ADV})"
"${PY}" "${ROUNDED_ROOT}/scripts/verify-2to1.py" \
  --expect-half "${EN_ADV}" \
  "${EXTRA_GATES[@]}" \
  "${FONTS[@]}"

log "verify ok"
