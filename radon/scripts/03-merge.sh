#!/usr/bin/env bash
# Merge prepared WenKai + Monaspace Radon → out/RadonWenKaiDual-{Regular,Bold}.ttf
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

LAT_R="${EXTRACT_DIR}/MonaspaceRadon-Regular.ttf"
LAT_B="${EXTRACT_DIR}/MonaspaceRadon-Bold.ttf"
CJK_R="${PREP_DIR}/WenKai-Regular-prepared.ttf"
CJK_B="${PREP_DIR}/WenKai-Bold-prepared.ttf"

for f in "${LAT_R}" "${LAT_B}" "${CJK_R}" "${CJK_B}"; do
  [[ -f "${f}" ]] || die "missing ${f}; run 01-fetch-sources.sh and 02-prepare-cjk.sh first"
done

log "merging EN=${EN_ADV} CJK=${CJK_ADV} UPM=${TARGET_UPM} family='${FAMILY_NAME}'"
"${PY}" "${RADON_ROOT}/scripts/merge_radon.py" \
  --latin-regular "${LAT_R}" \
  --latin-bold "${LAT_B}" \
  --cjk-regular "${CJK_R}" \
  --cjk-bold "${CJK_B}" \
  --out-dir "${OUT_DIR}" \
  --en-adv "${EN_ADV}" \
  --cjk-adv "${CJK_ADV}" \
  --target-upm "${TARGET_UPM}" \
  --family "${FAMILY_NAME}" \
  --family-ps "${FAMILY_PS}" \
  --hhea-ascent "${HHEA_ASCENT}" \
  --hhea-descent "${HHEA_DESCENT}" \
  --hhea-line-gap "${HHEA_LINE_GAP}" \
  --os2-typo-ascender "${OS2_TYPO_ASCENDER}" \
  --os2-typo-descender "${OS2_TYPO_DESCENDER}" \
  --os2-typo-line-gap "${OS2_TYPO_LINE_GAP}" \
  --os2-win-ascent "${OS2_WIN_ASCENT}" \
  --os2-win-descent "${OS2_WIN_DESCENT}"

# Bundle licenses next to product
mkdir -p "${OUT_DIR}"
for lic in "${RADON_ROOT}/licenses/"*; do
  [[ -f "${lic}" ]] || continue
  cp -f "${lic}" "${OUT_DIR}/"
done

log "products:"
ls -lh "${OUT_DIR}"/*.ttf
