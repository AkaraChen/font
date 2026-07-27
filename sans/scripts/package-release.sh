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
stem="${PRODUCT_STEM:-LilexSansSCDual}"
fonts=("${OUT_DIR}/${stem}"-*.ttf)
[[ ${#fonts[@]} -gt 0 ]] || die "no products in ${OUT_DIR}"

DIST_DIR="${SANS_ROOT}/dist"
mkdir -p "${DIST_DIR}"
STAGE="${WORK_DIR}/release-stage"
rm -rf "${STAGE}"
mkdir -p "${STAGE}"

cp "${fonts[@]}" "${STAGE}/"
for lic in OFL-Lilex.txt OFL-IBM-Plex.txt; do
  if [[ -f "${OUT_DIR}/${lic}" ]]; then
    cp "${OUT_DIR}/${lic}" "${STAGE}/"
  elif [[ -f "${SANS_ROOT}/licenses/${lic}" ]]; then
    cp "${SANS_ROOT}/licenses/${lic}" "${STAGE}/"
  fi
done

cat > "${STAGE}/README.txt" <<EOF
${FAMILY_NAME} ${VERSION}
Derived from Lilex + IBM Plex Sans SC under SIL OFL 1.1.
Not an official Lilex or IBM product.

Name recipe (same style as SarasaNZSSlab NFM):
  Lilex  = Lilex Latin / programming (ligatures + OT features preserved)
  SansSC = Plex Sans SC CJK
  Dual   = dual-width 2:1 coding product

Cell metrics: EN ${EN_ADV} / CJK ${CJK_ADV} (strict 2:1)
Upstream pins: see pins.env in the build repository.
EOF

ZIP="${DIST_DIR}/${stem}-${VERSION}.zip"
rm -f "${ZIP}"
(
  cd "${STAGE}"
  zip -q -r "${ZIP}" .
)
log "wrote ${ZIP}"
ls -lh "${ZIP}"
