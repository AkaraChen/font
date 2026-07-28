#!/usr/bin/env bash
# Gate: EN/CJK 2:1 + mono flags + EAW + Lilex features + Nerd PUA half-cell.
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
  # intermediate Dual only
  shopt -s nullglob
  stem_base="${BASE_FAMILY_PS:-LilexSansSCDual}"
  FONTS=("${OUT_DIR}/${stem_base}"-*.ttf)
  EXTRA_GATES=(--check-eaw)
  [[ ${#FONTS[@]} -gt 0 ]] || die "no products in ${OUT_DIR}; run 02-merge.sh first"
  log "verify intermediate Dual products (${#FONTS[@]}) with EAW gate"
fi

log "verify 2:1 (expect half=${EN_ADV})"
"${PY}" "${SANS_ROOT}/scripts/verify-2to1.py" \
  --expect-half "${EN_ADV}" \
  "${EXTRA_GATES[@]}" \
  "${FONTS[@]}"

log "verify Lilex coding features (calt / ligatures)"
"${PY}" "${SANS_ROOT}/scripts/verify-features.py" "${FONTS[@]}"

log "verify ok"
