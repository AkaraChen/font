#!/usr/bin/env bash
# Zip product TTFs + OFLs for a GitHub Release.
# Usage: ./scripts/package-release.sh 0.1.0
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

VERSION="${1:-}"
[[ -n "${VERSION}" ]] || die "usage: $0 <version>   e.g. 0.1.0"

need_cmd zip
shopt -s nullglob
stem="${PRODUCT_STEM:-RecursiveYozaiDual}"
fonts=("${OUT_DIR}/${stem}"-*.ttf)
[[ ${#fonts[@]} -gt 0 ]] || die "no products in ${OUT_DIR}"

DIST_DIR="${CASUAL_ROOT}/dist"
mkdir -p "${DIST_DIR}"
STAGE="${WORK_DIR}/release-stage"
rm -rf "${STAGE}"
mkdir -p "${STAGE}"

cp "${fonts[@]}" "${STAGE}/"
for lic in OFL-Recursive.txt OFL-Yozai.txt; do
  if [[ -f "${OUT_DIR}/${lic}" ]]; then
    cp "${OUT_DIR}/${lic}" "${STAGE}/"
  elif [[ -f "${CASUAL_ROOT}/licenses/${lic}" ]]; then
    cp "${CASUAL_ROOT}/licenses/${lic}" "${STAGE}/"
  fi
done

cat > "${STAGE}/README.txt" <<EOF
${FAMILY_NAME} ${VERSION}
Derived from Recursive Mono Casual (${RECURSIVE_RELEASE_TAG}) and
Yozai 悠哉 (${YOZAI_RELEASE_TAG}) under SIL OFL 1.1.
Not an official ArrowType Recursive or LXGW product.

Name recipe:
  Recursive = Recursive Mono Casual (Latin)
  Yozai     = 悠哉 (CJK handwriting)
  Dual      = 2:1 dual-width coding face

Cell metrics: EN ${EN_ADV} / CJK ${CJK_ADV} (strict 2:1)
CJK embolden: Regular s=${CJK_EMBOLDEN_REGULAR} (Yozai ${YOZAI_FOR_REGULAR})
              Bold    s=${CJK_EMBOLDEN_BOLD} (Yozai ${YOZAI_FOR_BOLD})
Upstream pins: see casual/pins.env in the build repository.
EOF

ZIP="${DIST_DIR}/${stem}-${VERSION}.zip"
rm -f "${ZIP}"
(
  cd "${STAGE}"
  zip -9 -r "${ZIP}" .
)
log "wrote ${ZIP}"
ls -lh "${ZIP}"
