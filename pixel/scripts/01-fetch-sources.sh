#!/usr/bin/env bash
# Fetch pinned Fusion Pixel 12px mono + Lilex (ligature donor).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

need_cmd unzip
ensure_dirs

FUSION_ZIP="${DOWNLOADS_DIR}/fusion-pixel-12px-monospaced-ttf-${FUSION_RELEASE_TAG}.zip"
LILEX_ZIP="${DOWNLOADS_DIR}/Lilex-${LILEX_RELEASE_TAG}.zip"

download_file "${FUSION_ZIP_URL}" "${FUSION_ZIP}" "${FUSION_ZIP_SHA256}"
download_file "${LILEX_ZIP_URL}" "${LILEX_ZIP}" "${LILEX_ZIP_SHA256}"

FUSION_DIR="${EXTRACT_DIR}/fusion"
LILEX_DIR="${EXTRACT_DIR}/lilex"
rm -rf "${FUSION_DIR}" "${LILEX_DIR}"
mkdir -p "${FUSION_DIR}" "${LILEX_DIR}"

log "extract fusion → ${FUSION_DIR}"
unzip -qo "${FUSION_ZIP}" -d "${FUSION_DIR}"
[[ -f "${FUSION_DIR}/${FUSION_TTF}" ]] || die "missing ${FUSION_TTF} in fusion zip"

log "extract lilex → ${LILEX_DIR}"
unzip -qo "${LILEX_ZIP}" -d "${LILEX_DIR}"
[[ -f "${LILEX_DIR}/${LILEX_TTF_REGULAR}" ]] || die "missing ${LILEX_TTF_REGULAR} in lilex zip"

# Stage clean copies under work/src for later steps
mkdir -p "${EXTRACT_DIR}/staged"
cp -f "${FUSION_DIR}/${FUSION_TTF}" "${EXTRACT_DIR}/staged/fusion-base.ttf"
cp -f "${LILEX_DIR}/${LILEX_TTF_REGULAR}" "${EXTRACT_DIR}/staged/lilex-regular.ttf"

log "staged:"
ls -lh "${EXTRACT_DIR}/staged/"
log "done fetch"
