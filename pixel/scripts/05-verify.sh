#!/usr/bin/env bash
# Verify ligatures (calt) + dual-width metrics + ambiguous-width punctuation
# + Nerd PUA presence.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

PY="$(python_bin)"
NERD_OUT="${OUT_DIR}/nerd"

mapfile -t FONTS < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) 2>/dev/null | sort)
if [[ ${#FONTS[@]} -eq 0 ]]; then
  # allow verifying intermediate only
  mapfile -t FONTS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.ttf' | sort)
fi
[[ ${#FONTS[@]} -gt 0 ]] || die "no fonts to verify under ${OUT_DIR}"

log "verify ${#FONTS[@]} font(s)"
"${PY}" "${PIXEL_ROOT}/scripts/verify.py" \
  --half "${EN_ADV}" \
  --full "${CJK_ADV}" \
  --check-nerd \
  --check-ligatures \
  --check-eaw \
  "${FONTS[@]}"

log "verify ok"
