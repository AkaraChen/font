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
stem="${PRODUCT_STEM:-RadonWenKaiNFM}"
fonts=("${OUT_DIR}/${stem}"-*.ttf)
[[ ${#fonts[@]} -gt 0 ]] || die "no products in ${OUT_DIR}"

DIST_DIR="${KAI_ROOT}/dist"
mkdir -p "${DIST_DIR}"
STAGE="${WORK_DIR}/release-stage"
rm -rf "${STAGE}"
mkdir -p "${STAGE}"

cp "${fonts[@]}" "${STAGE}/"
for lic in OFL-Monaspace.txt OFL-LXGWWenKai.txt; do
  if [[ -f "${OUT_DIR}/${lic}" ]]; then
    cp "${OUT_DIR}/${lic}" "${STAGE}/"
  elif [[ -f "${KAI_ROOT}/licenses/${lic}" ]]; then
    cp "${KAI_ROOT}/licenses/${lic}" "${STAGE}/"
  fi
done

cat > "${STAGE}/README.txt" <<EOF
${FAMILY_NAME} ${VERSION}
Derived from Monaspace Radon NF (${MONASPACE_RELEASE_TAG}) and
LXGW WenKai 霞鹜文楷 (${WENKAI_RELEASE_TAG}) under SIL OFL 1.1.
Not an official Monaspace / GitHub Next or LXGW product.

Name recipe (same style as SarasaNZSSlab NFM):
  Radon    = Monaspace Radon (Latin, ligatures + OpenType features)
  WenKai   = 霞鹜文楷 (CJK, sheared ${CJK_SLANT_DEG}° to Radon's lean)
  NFM      = Nerd Font Mono product (icons at one cell)

Cell metrics: EN ${EN_ADV} / CJK ${CJK_ADV} (strict 2:1)
Nerd icons:   from the upstream Monaspace Radon NF build, one cell each
Ligatures:    Radon liga + calt (on by default), plus ss01–ss10 / cv** opt-in
Upstream pins: see kai/pins.env in the build repository.
EOF

ZIP="${DIST_DIR}/${stem}-${VERSION}.zip"
rm -f "${ZIP}"
(
  cd "${STAGE}"
  zip -q -r "${ZIP}" .
)
log "wrote ${ZIP}"
ls -lh "${ZIP}"
