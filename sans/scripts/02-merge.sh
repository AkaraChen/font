#!/usr/bin/env bash
# Embolden SC (optical weight) then merge Lilex + SC → Dual intermediate (pre-Nerd).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

for f in \
  "${EXTRACT_DIR}/Lilex-Regular.ttf" \
  "${EXTRACT_DIR}/Lilex-Bold.ttf" \
  "${EXTRACT_DIR}/IBMPlexSansSC-Regular.ttf" \
  "${EXTRACT_DIR}/IBMPlexSansSC-Bold.ttf"
do
  [[ -f "${f}" ]] || die "missing source ${f}; run 01-fetch-sources.sh first"
done

# Optical weight: pathops embolden full-cell CJK before merge (KIT-259).
# Strengths measured by ./scripts/calibrate-stroke.sh against Lilex at product
# X-scale. 0 = leave the SC master alone.
CJK_EMBOLDEN_REGULAR="${CJK_EMBOLDEN_REGULAR:-0}"
CJK_EMBOLDEN_BOLD="${CJK_EMBOLDEN_BOLD:-0}"
SC_REG_IN="${EXTRACT_DIR}/IBMPlexSansSC-Regular.ttf"
SC_BOLD_IN="${EXTRACT_DIR}/IBMPlexSansSC-Bold.ttf"
SC_REG_PREP="${STAGE_DIR}/IBMPlexSansSC-Regular-weight.ttf"
SC_BOLD_PREP="${STAGE_DIR}/IBMPlexSansSC-Bold-weight.ttf"

embolden_sc() {
  local src="$1" dst="$2" strength="$3" label="$4"
  if awk "BEGIN { exit !(${strength} > 0) }"; then
    log "embolden CJK ${label} s=${strength}"
    "${PY}" -m fontkit.embolden "${src}" "${dst}" --strength "${strength}"
  else
    log "CJK ${label}: no embolden (s=0), use source master"
    cp -f "${src}" "${dst}"
  fi
}

embolden_sc "${SC_REG_IN}" "${SC_REG_PREP}" "${CJK_EMBOLDEN_REGULAR}" "Regular"
embolden_sc "${SC_BOLD_IN}" "${SC_BOLD_PREP}" "${CJK_EMBOLDEN_BOLD}" "Bold"

# Intermediate (pre-Nerd) family keeps Dual so merge output is distinct from NFM.
FAMILY="${BASE_FAMILY_NAME:-${FAMILY_NAME}}"
FAMILY_PS_MERGE="${BASE_FAMILY_PS:-${FAMILY_PS}}"
if [[ -n "${FAMILY_SUFFIX:-}" ]]; then
  FAMILY="${FAMILY} ${FAMILY_SUFFIX}"
fi

log "merging EN=${EN_ADV} CJK=${CJK_ADV} family='${FAMILY}'"
"${PY}" "${SANS_ROOT}/scripts/merge_plex.py" \
  --latin-regular "${EXTRACT_DIR}/Lilex-Regular.ttf" \
  --latin-bold "${EXTRACT_DIR}/Lilex-Bold.ttf" \
  --sc-regular "${SC_REG_PREP}" \
  --sc-bold "${SC_BOLD_PREP}" \
  --out-dir "${OUT_DIR}" \
  --en-adv "${EN_ADV}" \
  --cjk-adv "${CJK_ADV}" \
  --latin-src-adv "${LILEX_SRC_ADV}" \
  --family "${FAMILY}" \
  --family-ps "${FAMILY_PS_MERGE}" \
  --hhea-ascent "${HHEA_ASCENT}" \
  --hhea-descent "${HHEA_DESCENT}" \
  --hhea-line-gap "${HHEA_LINE_GAP}" \
  --os2-typo-ascender "${OS2_TYPO_ASCENDER}" \
  --os2-typo-descender "${OS2_TYPO_DESCENDER}" \
  --os2-typo-line-gap "${OS2_TYPO_LINE_GAP}" \
  --os2-win-ascent "${OS2_WIN_ASCENT}" \
  --os2-win-descent "${OS2_WIN_DESCENT}"

# Bundle OFLs next to intermediate products
for lic in OFL-Lilex.txt OFL-IBM-Plex.txt; do
  if [[ -f "${SANS_ROOT}/licenses/${lic}" ]]; then
    cp "${SANS_ROOT}/licenses/${lic}" "${OUT_DIR}/${lic}"
  fi
done

# EAW-correct Dual intermediate (N/Na/H ↔ half, W/F ↔ full). Nerd step re-runs
# this after patch because icons can dual-map onto CJK outlines.
mapfile -t DUAL_FONTS < <(
  find "${OUT_DIR}" -maxdepth 1 -type f -name 'LilexSansSCDual-*.ttf' | sort
)
if [[ ${#DUAL_FONTS[@]} -gt 0 ]]; then
  log "narrow/widen Dual intermediate to match East_Asian_Width"
  "${PY}" -m fontkit.narrow_symbol_widths --no-donor "${DUAL_FONTS[@]}"
  log "fix Dual terminal metrics"
  "${PY}" -m fontkit.fix_terminal_metrics "${DUAL_FONTS[@]}"
fi

log "intermediate products:"
ls -lh "${OUT_DIR}"/*.ttf
