#!/usr/bin/env bash
# Package Nerd Font products only for a GitHub Release.
# Usage:
#   ./scripts/package-release.sh [VERSION]
#   # → dist/SarasaNZSSlabNFM-<VERSION>.zip  (+ copies of the TTFs)
#
# Requires: out/nerd/*.ttf (run ./scripts/build.sh or 05-nerd-patch.sh first)
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

VERSION="${1:-}"
if [[ -z "${VERSION}" ]]; then
  VERSION="$(git -C "${SERIF_ROOT}/.." describe --tags --abbrev=0 2>/dev/null || true)"
  VERSION="${VERSION:-0.1.0}"
fi
VERSION="${VERSION#v}"

NERD_OUT="${OUT_DIR}/nerd"
DIST_DIR="${SERIF_ROOT}/dist"
STAGE="${DIST_DIR}/stage-SarasaNZSSlabNFM-${VERSION}"
ZIP_NAME="SarasaNZSSlabNFM-${VERSION}.zip"

mapfile -t FONTS < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
if [[ ${#FONTS[@]} -eq 0 ]]; then
  die "no Nerd fonts in ${NERD_OUT}; run ./scripts/build.sh first"
fi

# Gate before packaging
PY=""
if [[ -x "${VENV_DIR}/bin/python" ]]; then
  PY="${VENV_DIR}/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
fi
if [[ -n "${PY}" && -f "${SERIF_ROOT}/scripts/verify-2to1.py" ]]; then
  log "2:1 + Nerd + EAW verify before package"
  "${PY}" "${SERIF_ROOT}/scripts/verify-2to1.py" --check-nerd --check-eaw "${FONTS[@]}"
fi

rm -rf "${STAGE}"
mkdir -p "${STAGE}" "${DIST_DIR}"
for f in "${FONTS[@]}"; do
  cp -f "$f" "${STAGE}/"
done

# short install note inside zip
cat > "${STAGE}/README.txt" <<EOF
SarasaNZSSlab NFM (Nerd Font Mono) ${VERSION}
============================================

Family: SarasaNZSSlab NFM
Styles: Regular, Bold
Grid:   2:1 dual-width mono (Latin half / CJK full)
Icons:  Nerd Fonts complete set (single-cell), patcher ${NERD_FONTS_TAG:-v3.4.0}
Widths: advances match Unicode East_Asian_Width, so terminals that size
        cells with wcwidth() line up (neutral symbols like U+23F5 are
        half-width). Ambiguous-width symbols stay full-width by design.

Install: copy the .ttf files into your OS fonts directory, or use a
font manager. In terminals/IDEs pick family "SarasaNZSSlab NFM".

Sources: https://github.com/AkaraChen/font (serif/)
Licenses: Sarasa / IosevkaN / LXGW Neo ZhiSong / Nerd Fonts glyph sets —
see upstream and repo LICENSE notes.
EOF

need_cmd zip
(
  cd "${DIST_DIR}"
  rm -f "${ZIP_NAME}"
  (cd "$(basename "${STAGE}")" && zip -9 "../${ZIP_NAME}" ./*)
)

log "release artifacts:"
ls -lh "${DIST_DIR}/${ZIP_NAME}"
ls -lh "${STAGE}"/*.ttf
echo
echo "ZIP=${DIST_DIR}/${ZIP_NAME}"
echo "DIR=${STAGE}"
