#!/usr/bin/env bash
# Fetch pinned IBM Plex Mono + Plex Sans SC release zips and extract TTFs.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
need_cmd unzip

MONO_ZIP="${DOWNLOADS_DIR}/ibm-plex-mono.zip"
SC_ZIP="${DOWNLOADS_DIR}/ibm-plex-sans-sc.zip"

download_zip "${PLEX_MONO_ZIP_URL}" "${MONO_ZIP}" "${PLEX_MONO_ZIP_SHA256}"
download_zip "${PLEX_SANS_SC_ZIP_URL}" "${SC_ZIP}" "${PLEX_SANS_SC_ZIP_SHA256}"

log "extracting Mono TTFs"
rm -rf "${EXTRACT_DIR}/mono" "${EXTRACT_DIR}/sc"
mkdir -p "${EXTRACT_DIR}/mono" "${EXTRACT_DIR}/sc"
unzip -qo "${MONO_ZIP}" "${PLEX_MONO_TTF_REGULAR}" "${PLEX_MONO_TTF_BOLD}" -d "${EXTRACT_DIR}/mono"
unzip -qo "${SC_ZIP}" "${PLEX_SANS_SC_TTF_REGULAR}" "${PLEX_SANS_SC_TTF_BOLD}" -d "${EXTRACT_DIR}/sc"

# Flatten to predictable paths for the merge step
cp "${EXTRACT_DIR}/mono/${PLEX_MONO_TTF_REGULAR}" "${EXTRACT_DIR}/IBMPlexMono-Regular.ttf"
cp "${EXTRACT_DIR}/mono/${PLEX_MONO_TTF_BOLD}" "${EXTRACT_DIR}/IBMPlexMono-Bold.ttf"
cp "${EXTRACT_DIR}/sc/${PLEX_SANS_SC_TTF_REGULAR}" "${EXTRACT_DIR}/IBMPlexSansSC-Regular.ttf"
cp "${EXTRACT_DIR}/sc/${PLEX_SANS_SC_TTF_BOLD}" "${EXTRACT_DIR}/IBMPlexSansSC-Bold.ttf"

# Copy OFL from SC package if present in zip
if unzip -l "${SC_ZIP}" | grep -q 'LICENSE.txt'; then
  unzip -p "${SC_ZIP}" '*/LICENSE.txt' > "${SANS_ROOT}/licenses/OFL-IBM-Plex.txt" 2>/dev/null \
    || unzip -p "${SC_ZIP}" 'ibm-plex-sans-sc/LICENSE.txt' > "${SANS_ROOT}/licenses/OFL-IBM-Plex.txt"
fi

log "sources ready under ${EXTRACT_DIR}"
ls -lh "${EXTRACT_DIR}"/IBMPlex*.ttf
