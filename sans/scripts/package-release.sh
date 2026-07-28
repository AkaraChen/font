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
DIST_DIR="${SANS_ROOT}/dist"
STAGE="${WORK_DIR}/release-stage"
stem="${PRODUCT_STEM:-LilexSansSCNFM}"

mapfile -t FONTS < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name "${stem}-*.ttf" -o -name "${stem}-*.otf" \) | sort)
if [[ ${#FONTS[@]} -eq 0 ]]; then
  mapfile -t FONTS < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
fi
[[ ${#FONTS[@]} -gt 0 ]] || die "no Nerd fonts in ${NERD_OUT}; run ./scripts/build.sh first"

# Gate before packaging (2:1 + nerd + EAW + features)
PY="$(python_bin)"
"${PY}" "${SANS_ROOT}/scripts/verify-2to1.py" \
  --expect-half "${EN_ADV}" --check-nerd --check-eaw "${FONTS[@]}"
"${PY}" "${SANS_ROOT}/scripts/verify-features.py" "${FONTS[@]}"

mkdir -p "${DIST_DIR}"
rm -rf "${STAGE}"
mkdir -p "${STAGE}"

cp "${FONTS[@]}" "${STAGE}/"
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
Nerd Font icons via ${NERD_FONTS_TAG} FontPatcher (--complete --single-width-glyphs).
Not an official Lilex, IBM, or Nerd Fonts product.

Name recipe (same style as SarasaNZSSlab NFM):
  Lilex  = Lilex Latin / programming (ligatures + OT features preserved)
  SansSC = Plex Sans SC CJK
  NFM    = Nerd Font Mono

Cell metrics: EN ${EN_ADV} / CJK ${CJK_ADV} (strict 2:1)
Mono flags:   post.isFixedPitch=1, PANOSE bProportion=9
Icons:        Nerd complete set at half-cell advance
EAW:          N/Na/H → half, W/F → full (ambiguous left alone by default)

Install: copy the .ttf into your OS fonts directory.
In terminals/IDEs pick family "${FAMILY_NAME}" and enable font ligatures.

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
