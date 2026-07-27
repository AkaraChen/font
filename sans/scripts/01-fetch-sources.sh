#!/usr/bin/env bash
# Fetch pinned Lilex + Plex Sans SC release zips and extract TTFs.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
need_cmd unzip

LILEX_ZIP="${DOWNLOADS_DIR}/Lilex.zip"
SC_ZIP="${DOWNLOADS_DIR}/ibm-plex-sans-sc.zip"

download_zip "${LILEX_ZIP_URL}" "${LILEX_ZIP}" "${LILEX_ZIP_SHA256}"
download_zip "${PLEX_SANS_SC_ZIP_URL}" "${SC_ZIP}" "${PLEX_SANS_SC_ZIP_SHA256}"

log "extracting Lilex + SC TTFs"
rm -rf "${EXTRACT_DIR}/lilex" "${EXTRACT_DIR}/sc"
mkdir -p "${EXTRACT_DIR}/lilex" "${EXTRACT_DIR}/sc"
unzip -qo "${LILEX_ZIP}" "${LILEX_TTF_REGULAR}" "${LILEX_TTF_BOLD}" -d "${EXTRACT_DIR}/lilex"
unzip -qo "${SC_ZIP}" "${PLEX_SANS_SC_TTF_REGULAR}" "${PLEX_SANS_SC_TTF_BOLD}" -d "${EXTRACT_DIR}/sc"

# Flatten to predictable paths for the merge step
cp "${EXTRACT_DIR}/lilex/${LILEX_TTF_REGULAR}" "${EXTRACT_DIR}/Lilex-Regular.ttf"
cp "${EXTRACT_DIR}/lilex/${LILEX_TTF_BOLD}" "${EXTRACT_DIR}/Lilex-Bold.ttf"
cp "${EXTRACT_DIR}/sc/${PLEX_SANS_SC_TTF_REGULAR}" "${EXTRACT_DIR}/IBMPlexSansSC-Regular.ttf"
cp "${EXTRACT_DIR}/sc/${PLEX_SANS_SC_TTF_BOLD}" "${EXTRACT_DIR}/IBMPlexSansSC-Bold.ttf"

# Refresh OFL copies when present in the release zips / keep committed pins
if unzip -l "${SC_ZIP}" | grep -q 'LICENSE.txt'; then
  unzip -p "${SC_ZIP}" '*/LICENSE.txt' > "${SANS_ROOT}/licenses/OFL-IBM-Plex.txt" 2>/dev/null \
    || unzip -p "${SC_ZIP}" 'ibm-plex-sans-sc/LICENSE.txt' > "${SANS_ROOT}/licenses/OFL-IBM-Plex.txt"
fi
# Lilex release zip has no OFL file; keep licenses/OFL-Lilex.txt in-tree (from upstream OFL.txt).

log "sources ready under ${EXTRACT_DIR}"
ls -lh "${EXTRACT_DIR}"/Lilex-*.ttf "${EXTRACT_DIR}"/IBMPlexSansSC-*.ttf
