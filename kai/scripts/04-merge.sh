#!/usr/bin/env bash
# Merge the two intermediates → out/RadonWenKaiNFM-{Regular,Bold}.ttf
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

for f in \
  "${STAGE_DIR}/RadonLatin-Regular.ttf" \
  "${STAGE_DIR}/RadonLatin-Bold.ttf" \
  "${STAGE_DIR}/WenKaiSlanted-Regular.ttf" \
  "${STAGE_DIR}/WenKaiSlanted-Bold.ttf"
do
  [[ -f "${f}" ]] || die "missing intermediate ${f}; run 02-prepare-latin.sh / 03-prepare-cjk.sh"
done

FAMILY="${FAMILY_NAME}"
[[ -n "${FAMILY_SUFFIX:-}" ]] && FAMILY="${FAMILY_NAME} ${FAMILY_SUFFIX}"

log "merging EN=${EN_ADV} CJK=${CJK_ADV} family='${FAMILY}'"
"${PY}" "${KAI_ROOT}/scripts/merge_radon_wenkai.py" \
  --latin-regular "${STAGE_DIR}/RadonLatin-Regular.ttf" \
  --latin-bold "${STAGE_DIR}/RadonLatin-Bold.ttf" \
  --cjk-regular "${STAGE_DIR}/WenKaiSlanted-Regular.ttf" \
  --cjk-bold "${STAGE_DIR}/WenKaiSlanted-Bold.ttf" \
  --out-dir "${OUT_DIR}" \
  --en-adv "${EN_ADV}" \
  --cjk-adv "${CJK_ADV}" \
  --family "${FAMILY}" \
  --family-ps "${FAMILY_PS}" \
  --slant-deg "${CJK_SLANT_DEG}" \
  --hhea-ascent "${HHEA_ASCENT}" \
  --hhea-descent "${HHEA_DESCENT}" \
  --hhea-line-gap "${HHEA_LINE_GAP}" \
  --os2-typo-ascender "${OS2_TYPO_ASCENDER}" \
  --os2-typo-descender "${OS2_TYPO_DESCENDER}" \
  --os2-typo-line-gap "${OS2_TYPO_LINE_GAP}" \
  --os2-win-ascent "${OS2_WIN_ASCENT}" \
  --os2-win-descent "${OS2_WIN_DESCENT}"

for lic in OFL-Monaspace.txt OFL-LXGWWenKai.txt; do
  [[ -f "${KAI_ROOT}/licenses/${lic}" ]] && cp "${KAI_ROOT}/licenses/${lic}" "${OUT_DIR}/${lic}"
done

log "products:"
ls -lh "${OUT_DIR}"/*.ttf
