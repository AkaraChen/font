#!/usr/bin/env bash
# Merge Courier Prime + Zhuque → out/CourierPrimeZhuqueDual-{Regular,Bold}.ttf
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

for f in \
  "${EXTRACT_DIR}/CourierPrime-Regular.ttf" \
  "${EXTRACT_DIR}/CourierPrime-Bold.ttf" \
  "${EXTRACT_DIR}/ZhuqueFangsong-Regular-prepared.ttf" \
  "${EXTRACT_DIR}/ZhuqueFangsong-Bold-prepared.ttf"
do
  [[ -f "${f}" ]] || die "missing source ${f}; run 01-fetch + 02-prepare-cjk first"
done

FAMILY="${BASE_FAMILY_NAME:-${FAMILY_NAME}}"
FAMILY_PS_MERGE="${BASE_FAMILY_PS:-${FAMILY_PS}}"
if [[ -n "${FAMILY_SUFFIX:-}" ]]; then
  FAMILY="${FAMILY} ${FAMILY_SUFFIX}"
fi

log "merging EN=${EN_ADV} CJK=${CJK_ADV} family='${FAMILY}'"
"${PY}" "${TYPEWRITER_ROOT}/scripts/merge_typewriter.py" \
  --latin-regular "${EXTRACT_DIR}/CourierPrime-Regular.ttf" \
  --latin-bold "${EXTRACT_DIR}/CourierPrime-Bold.ttf" \
  --cjk-regular "${EXTRACT_DIR}/ZhuqueFangsong-Regular-prepared.ttf" \
  --cjk-bold "${EXTRACT_DIR}/ZhuqueFangsong-Bold-prepared.ttf" \
  --out-dir "${OUT_DIR}" \
  --en-adv "${EN_ADV}" \
  --cjk-adv "${CJK_ADV}" \
  --latin-src-adv "${LATIN_SRC_ADV}" \
  --latin-src-upm "${COURIER_PRIME_SRC_UPM}" \
  --latin-target-upm "${LATIN_TARGET_UPM}" \
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

for lic in OFL-CourierPrime.txt OFL-Zhuque.txt; do
  if [[ -f "${TYPEWRITER_ROOT}/licenses/${lic}" ]]; then
    cp "${TYPEWRITER_ROOT}/licenses/${lic}" "${OUT_DIR}/${lic}"
  fi
done

mapfile -t DUAL_FONTS < <(
  find "${OUT_DIR}" -maxdepth 1 -type f -name 'CourierPrimeZhuqueDual-*.ttf' | sort
)
if [[ ${#DUAL_FONTS[@]} -gt 0 ]]; then
  log "narrow/widen Dual intermediate to match East_Asian_Width"
  "${PY}" -m fontkit.narrow_symbol_widths --no-donor "${DUAL_FONTS[@]}"
  log "fix Dual terminal metrics"
  "${PY}" -m fontkit.fix_terminal_metrics "${DUAL_FONTS[@]}"
fi

log "intermediate products:"
ls -lh "${OUT_DIR}"/*.ttf
