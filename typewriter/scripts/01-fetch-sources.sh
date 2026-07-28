#!/usr/bin/env bash
# Fetch pinned Courier Prime TTFs + Zhuque Fangsong zip.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
need_cmd unzip

PRIME_REG="${DOWNLOADS_DIR}/CourierPrime-Regular.ttf"
PRIME_BOLD="${DOWNLOADS_DIR}/CourierPrime-Bold.ttf"
ZHUQUE_ZIP="${DOWNLOADS_DIR}/ZhuqueFangsong-${ZHUQUE_RELEASE_TAG}.zip"

download_file "${COURIER_PRIME_TTF_REGULAR_URL}" "${PRIME_REG}" "${COURIER_PRIME_TTF_REGULAR_SHA256}"
download_file "${COURIER_PRIME_TTF_BOLD_URL}" "${PRIME_BOLD}" "${COURIER_PRIME_TTF_BOLD_SHA256}"
download_zip "${ZHUQUE_ZIP_URL}" "${ZHUQUE_ZIP}" "${ZHUQUE_ZIP_SHA256}"

log "extracting Zhuque Fangsong"
rm -rf "${EXTRACT_DIR}/zhuque"
mkdir -p "${EXTRACT_DIR}/zhuque"
unzip -qo "${ZHUQUE_ZIP}" "${ZHUQUE_TTF_IN_ZIP}" -d "${EXTRACT_DIR}/zhuque"

# Flatten to predictable paths
cp "${PRIME_REG}" "${EXTRACT_DIR}/CourierPrime-Regular.ttf"
cp "${PRIME_BOLD}" "${EXTRACT_DIR}/CourierPrime-Bold.ttf"
cp "${EXTRACT_DIR}/zhuque/${ZHUQUE_TTF_IN_ZIP}" "${EXTRACT_DIR}/ZhuqueFangsong-Regular.ttf"

# Licenses stay committed under licenses/
log "sources ready under ${EXTRACT_DIR}"
ls -lh \
  "${EXTRACT_DIR}/CourierPrime-Regular.ttf" \
  "${EXTRACT_DIR}/CourierPrime-Bold.ttf" \
  "${EXTRACT_DIR}/ZhuqueFangsong-Regular.ttf"
