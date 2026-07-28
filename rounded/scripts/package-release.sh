#!/usr/bin/env bash
# Zip Nerd product TTFs + OFLs for a GitHub Release.
# Usage: ./scripts/package-release.sh 0.1.0
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

VERSION="${1:-}"
[[ -n "${VERSION}" ]] || die "usage: $0 <version>   e.g. 0.1.0"
VERSION="${VERSION#v}"

need_cmd zip
NERD_OUT="${OUT_DIR}/nerd"
DIST_DIR="${ROUNDED_ROOT}/dist"
STAGE="${WORK_DIR}/release-stage"
stem="${PRODUCT_STEM:-IosevkaCurlyRHRNFM}"

mapfile -t FONTS < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name "${stem}-*.ttf" -o -name "${stem}-*.otf" \) | sort)
if [[ ${#FONTS[@]} -eq 0 ]]; then
  mapfile -t FONTS < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
fi
[[ ${#FONTS[@]} -gt 0 ]] || die "no Nerd fonts in ${NERD_OUT}; run ./scripts/build.sh first"

PY="$(python_bin)"
"${PY}" -m fontkit.verify2to1 \
  --expect-half "${EN_ADV}" --check-nerd --check-eaw "${FONTS[@]}"

mkdir -p "${DIST_DIR}"
rm -rf "${STAGE}"
mkdir -p "${STAGE}"

cp "${FONTS[@]}" "${STAGE}/"
for lic in OFL-Iosevka.txt OFL-Resource-Han-Rounded.txt; do
  if [[ -f "${OUT_DIR}/${lic}" ]]; then
    cp "${OUT_DIR}/${lic}" "${STAGE}/"
  elif [[ -f "${ROUNDED_ROOT}/licenses/${lic}" ]]; then
    cp "${ROUNDED_ROOT}/licenses/${lic}" "${STAGE}/"
  fi
done

cat > "${STAGE}/README.txt" <<EOF
${FAMILY_NAME} ${VERSION}
Derived from Iosevka Curly (ss20) + Resource Han Rounded SC (资源圆体) under SIL OFL 1.1.
Nerd Font icons via ${NERD_FONTS_TAG} FontPatcher (--complete --single-width-glyphs).
Not an official Iosevka, Resource Han Rounded, or Nerd Fonts product.

Name recipe (inheritance in the family name):
  Iosevka = Latin base
  Curly   = ss20 Curly Style package
  RHR     = Resource Han Rounded SC
  NFM     = Nerd Font Mono
  (docs nickname: 圆体)

Sources:
  Latin = Iosevka Curly (ss20 Curly Style, sans)
  CJK   = Resource Han Rounded SC (资源圆体)
  Bold CJK = RHR Bold master (optional embolden via pins)

Cell metrics: EN ${EN_ADV} / CJK ${CJK_ADV} (strict 2:1)
Mono flags:   post.isFixedPitch=1, PANOSE bProportion=9
Icons:        Nerd complete set at half-cell advance
EAW:          N/Na/H → half, W/F → full (ambiguous left alone by default)

Install: copy the .ttf into your OS fonts directory.
In terminals/IDEs pick family "${FAMILY_NAME}".

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
