#!/usr/bin/env bash
# Fetch the pinned Fusion Pixel 12px mono base.
# Ligatures are hand-drawn in ligatures/ligatures.txt — there is no donor font.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

need_cmd unzip
ensure_dirs

FUSION_ZIP="${DOWNLOADS_DIR}/fusion-pixel-12px-monospaced-ttf-${FUSION_RELEASE_TAG}.zip"

download_file "${FUSION_ZIP_URL}" "${FUSION_ZIP}" "${FUSION_ZIP_SHA256}"

FUSION_DIR="${EXTRACT_DIR}/fusion"
rm -rf "${FUSION_DIR}"
mkdir -p "${FUSION_DIR}"

log "extract fusion → ${FUSION_DIR}"
unzip -qo "${FUSION_ZIP}" -d "${FUSION_DIR}"
[[ -f "${FUSION_DIR}/${FUSION_TTF}" ]] || die "missing ${FUSION_TTF} in fusion zip"

# Stage a clean copy under work/src for later steps
mkdir -p "${EXTRACT_DIR}/staged"
cp -f "${FUSION_DIR}/${FUSION_TTF}" "${EXTRACT_DIR}/staged/fusion-base.ttf"

log "staged:"
ls -lh "${EXTRACT_DIR}/staged/"
log "done fetch"
