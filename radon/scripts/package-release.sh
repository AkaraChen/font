#!/usr/bin/env bash
# Package Dual + NFM TTFs + licenses into dist/RadonWenKai-VERSION.zip
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

VERSION="${1:-}"
[[ -n "${VERSION}" ]] || die "usage: package-release.sh <version>"

ensure_dirs
DIST_DIR="${RADON_ROOT}/dist"
STAGE="${WORK_DIR}/release-stage"
rm -rf "${STAGE}"
mkdir -p "${STAGE}" "${DIST_DIR}"

stem="${PRODUCT_STEM:-RadonWenKaiDual}"
nerd_ps="${NERD_FONT_FAMILY_PS:-RadonWenKaiNFM}"

shopt -s nullglob
dual=("${OUT_DIR}/${stem}"-*.ttf)
nerd=("${OUT_DIR}/nerd/${nerd_ps}"-*.ttf)

[[ ${#dual[@]} -gt 0 ]] || die "no Dual fonts in ${OUT_DIR}"
cp -f "${dual[@]}" "${STAGE}/"

if [[ ${#nerd[@]} -gt 0 ]]; then
  mkdir -p "${STAGE}/nerd"
  cp -f "${nerd[@]}" "${STAGE}/nerd/"
else
  log "warning: no Nerd products; packaging Dual only"
fi

for lic in "${RADON_ROOT}/licenses/"* "${OUT_DIR}/"LICENSE* "${OUT_DIR}/"OFL*; do
  [[ -f "${lic}" ]] || continue
  cp -f "${lic}" "${STAGE}/"
done

cat > "${STAGE}/README.txt" <<EOF
RadonWenKai Dual / NFM ${VERSION}
================================

Monaspace Radon (Frozen) Latin + LXGW WenKai Medium CJK
EN cell ${EN_ADV} / CJK cell ${CJK_ADV} (strict 2:1) at UPM ${TARGET_UPM}

Files:
  ${stem}-Regular.ttf / ${stem}-Bold.ttf     — dual-width coding face
  nerd/${nerd_ps}-*.ttf                     — Nerd Font Mono (if present)

Enable coding ligatures in your editor (calt / dlig from Monaspace Radon).

Upstream licenses: SIL OFL 1.1 (Monaspace, LXGW WenKai). Reserved names apply;
this compound name is a project build label, not an official GitHub Next / lxgw face.
EOF

ZIP="${DIST_DIR}/RadonWenKai-${VERSION}.zip"
rm -f "${ZIP}"
need_cmd zip
(
  cd "${STAGE}"
  zip -r "${ZIP}" .
)
log "wrote ${ZIP}"
ls -lh "${ZIP}"
