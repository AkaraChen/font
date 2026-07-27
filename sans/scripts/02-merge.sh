#!/usr/bin/env bash
# Merge pinned Lilex + SC into out/LilexSansSCDual-{Regular,Bold}.ttf
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

FAMILY="${FAMILY_NAME}"
if [[ -n "${FAMILY_SUFFIX:-}" ]]; then
  FAMILY="${FAMILY_NAME} ${FAMILY_SUFFIX}"
fi

log "merging EN=${EN_ADV} CJK=${CJK_ADV} family='${FAMILY}'"
"${PY}" "${SANS_ROOT}/scripts/merge_plex.py" \
  --latin-regular "${EXTRACT_DIR}/Lilex-Regular.ttf" \
  --latin-bold "${EXTRACT_DIR}/Lilex-Bold.ttf" \
  --sc-regular "${EXTRACT_DIR}/IBMPlexSansSC-Regular.ttf" \
  --sc-bold "${EXTRACT_DIR}/IBMPlexSansSC-Bold.ttf" \
  --out-dir "${OUT_DIR}" \
  --en-adv "${EN_ADV}" \
  --cjk-adv "${CJK_ADV}" \
  --latin-src-adv "${LILEX_SRC_ADV}" \
  --family "${FAMILY}" \
  --family-ps "${FAMILY_PS}" \
  --hhea-ascent "${HHEA_ASCENT}" \
  --hhea-descent "${HHEA_DESCENT}" \
  --hhea-line-gap "${HHEA_LINE_GAP}" \
  --os2-typo-ascender "${OS2_TYPO_ASCENDER}" \
  --os2-typo-descender "${OS2_TYPO_DESCENDER}" \
  --os2-typo-line-gap "${OS2_TYPO_LINE_GAP}" \
  --os2-win-ascent "${OS2_WIN_ASCENT}" \
  --os2-win-descent "${OS2_WIN_DESCENT}"

# Bundle OFLs next to product
for lic in OFL-Lilex.txt OFL-IBM-Plex.txt; do
  if [[ -f "${SANS_ROOT}/licenses/${lic}" ]]; then
    cp "${SANS_ROOT}/licenses/${lic}" "${OUT_DIR}/${lic}"
  fi
done

log "products:"
ls -lh "${OUT_DIR}"/*.ttf
