#!/usr/bin/env bash
# Fetch pinned Lilex zip + Plex Sans SC TTFs (individual files, not full zip).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
need_cmd unzip

LILEX_ZIP="${DOWNLOADS_DIR}/Lilex.zip"
SC_REG="${DOWNLOADS_DIR}/IBMPlexSansSC-Regular.ttf"
SC_BOLD="${DOWNLOADS_DIR}/IBMPlexSansSC-Bold.ttf"

download_zip "${LILEX_ZIP_URL}" "${LILEX_ZIP}" "${LILEX_ZIP_SHA256}"

download_file "${PLEX_SANS_SC_TTF_REGULAR_URL}" "${SC_REG}" "${PLEX_SANS_SC_TTF_REGULAR_SHA256}"
download_file "${PLEX_SANS_SC_TTF_BOLD_URL}" "${SC_BOLD}" "${PLEX_SANS_SC_TTF_BOLD_SHA256}"

log "extracting Lilex TTFs"
rm -rf "${EXTRACT_DIR}/lilex"
mkdir -p "${EXTRACT_DIR}/lilex"
unzip -qo "${LILEX_ZIP}" "${LILEX_TTF_REGULAR}" "${LILEX_TTF_BOLD}" -d "${EXTRACT_DIR}/lilex"

# Flatten to predictable paths for the merge step
cp "${EXTRACT_DIR}/lilex/${LILEX_TTF_REGULAR}" "${EXTRACT_DIR}/Lilex-Regular.ttf"
cp "${EXTRACT_DIR}/lilex/${LILEX_TTF_BOLD}" "${EXTRACT_DIR}/Lilex-Bold.ttf"
cp "${SC_REG}" "${EXTRACT_DIR}/IBMPlexSansSC-Regular.ttf"
cp "${SC_BOLD}" "${EXTRACT_DIR}/IBMPlexSansSC-Bold.ttf"

# Lilex release zip has no OFL file; keep licenses/OFL-Lilex.txt in-tree.
# Plex OFL stays committed under licenses/OFL-IBM-Plex.txt.

log "sources ready under ${EXTRACT_DIR}"
ls -lh "${EXTRACT_DIR}"/Lilex-*.ttf "${EXTRACT_DIR}"/IBMPlexSansSC-*.ttf
