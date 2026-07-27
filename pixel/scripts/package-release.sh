#!/usr/bin/env bash
# Package Nerd product for a GitHub Release.
# Usage: ./scripts/package-release.sh [VERSION]
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

VERSION="${1:-0.1.0}"
VERSION="${VERSION#v}"

NERD_OUT="${OUT_DIR}/nerd"
DIST_DIR="${PIXEL_ROOT}/dist"
STAGE="${DIST_DIR}/stage-${PRODUCT_STEM}-${VERSION}"
ZIP_NAME="${PRODUCT_STEM}-${VERSION}.zip"

mapfile -t FONTS < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
[[ ${#FONTS[@]} -gt 0 ]] || die "no Nerd fonts in ${NERD_OUT}; run ./scripts/build.sh first"

PY="$(python_bin)"
"${PY}" "${PIXEL_ROOT}/scripts/verify.py" \
  --half "${EN_ADV}" --full "${CJK_ADV}" \
  --check-nerd --check-ligatures \
  "${FONTS[@]}"

rm -rf "${STAGE}"
mkdir -p "${STAGE}" "${DIST_DIR}"
for f in "${FONTS[@]}"; do
  cp -f "$f" "${STAGE}/"
done
cp -f "${PIXEL_ROOT}/licenses/"* "${STAGE}/" 2>/dev/null || true

cat > "${STAGE}/README.txt" <<EOF
${FAMILY_NAME} ${VERSION}
============================================

Family: ${FAMILY_NAME}
Grid:   Fusion Pixel 12px mono (EN ${EN_ADV} / CJK ${CJK_ADV})
Ligatures: hand-drawn pixel programming ligatures (calt)
Icons:  Nerd Fonts complete set (single-cell), not redrawn
        patcher ${NERD_FONTS_TAG}

Install: copy the .ttf into your OS fonts directory.
In terminals/IDEs pick family "${FAMILY_NAME}" and enable font ligatures.

Sources: https://github.com/AkaraChen/font (pixel/)
Upstream: Fusion Pixel Font (OFL), Nerd Fonts glyph sets
EOF

need_cmd zip
(
  cd "${DIST_DIR}"
  rm -f "${ZIP_NAME}"
  (cd "$(basename "${STAGE}")" && zip -9 "../${ZIP_NAME}" ./*)
)

log "release artifacts:"
ls -lh "${DIST_DIR}/${ZIP_NAME}"
echo "ZIP=${DIST_DIR}/${ZIP_NAME}"
