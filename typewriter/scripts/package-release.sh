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
DIST_DIR="${TYPEWRITER_ROOT}/dist"
STAGE="${WORK_DIR}/release-stage"
stem="${PRODUCT_STEM:-CourierPrimeZhuqueNFM}"

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
for lic in OFL-CourierPrime.txt OFL-Zhuque.txt; do
  if [[ -f "${OUT_DIR}/${lic}" ]]; then
    cp "${OUT_DIR}/${lic}" "${STAGE}/"
  elif [[ -f "${TYPEWRITER_ROOT}/licenses/${lic}" ]]; then
    cp "${TYPEWRITER_ROOT}/licenses/${lic}" "${STAGE}/"
  fi
done

cat > "${STAGE}/README.txt" <<EOF
${FAMILY_NAME} ${VERSION}
Derived from Courier Prime + Zhuque Fangsong (朱雀仿宋) under SIL OFL 1.1.
Nerd Font icons via ${NERD_FONTS_TAG} FontPatcher (--complete --single-width-glyphs).
Not an official Courier Prime, Zhuque, or Nerd Fonts product.

Name recipe (source tokens, same style as LilexSansSC NFM):
  CourierPrime = Courier Prime (Latin slab mono)
  Zhuque       = Zhuque Fangsong (CJK)
  NFM          = Nerd Font Mono

Sources:
  Latin = Courier Prime (slab mono; UPM 2048→1000)
  CJK   = Zhuque Fangsong technical preview (Alegreya Latin dropped)
  CJK weight = stem-measured embolden of Zhuque Regular
               (Regular strength 8 / Bold strength 32 vs Courier Prime)

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
