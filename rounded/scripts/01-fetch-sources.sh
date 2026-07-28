#!/usr/bin/env bash
# Fetch pinned Iosevka Curly (ss20) TTF zip + Resource Han Rounded CN 7z.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
need_cmd unzip

IOSEVKA_ZIP="${DOWNLOADS_DIR}/IosevkaCurly-${IOSEVKA_RELEASE_TAG}.zip"
RHR_ARC="${DOWNLOADS_DIR}/RHR-CN-${RHR_RELEASE_TAG}.7z"

download_zip "${IOSEVKA_ZIP_URL}" "${IOSEVKA_ZIP}" "${IOSEVKA_ZIP_SHA256}"
download_zip "${RHR_ZIP_URL}" "${RHR_ARC}" "${RHR_ZIP_SHA256}"

log "extracting Iosevka Curly Regular/Bold"
rm -rf "${EXTRACT_DIR}/iosevka"
mkdir -p "${EXTRACT_DIR}/iosevka"
unzip -qo "${IOSEVKA_ZIP}" \
  "${IOSEVKA_TTF_REGULAR}" \
  "${IOSEVKA_TTF_BOLD}" \
  -d "${EXTRACT_DIR}/iosevka"
cp "${EXTRACT_DIR}/iosevka/${IOSEVKA_TTF_REGULAR}" "${EXTRACT_DIR}/IosevkaCurly-Regular.ttf"
cp "${EXTRACT_DIR}/iosevka/${IOSEVKA_TTF_BOLD}" "${EXTRACT_DIR}/IosevkaCurly-Bold.ttf"

log "extracting Resource Han Rounded CN"
rm -rf "${EXTRACT_DIR}/rhr"
mkdir -p "${EXTRACT_DIR}/rhr"
# Prefer 7z; fall back to 7za / bsdtar if available
if command -v 7z >/dev/null 2>&1; then
  7z x "${RHR_ARC}" -o"${EXTRACT_DIR}/rhr" -y >/dev/null
elif command -v 7za >/dev/null 2>&1; then
  7za x "${RHR_ARC}" -o"${EXTRACT_DIR}/rhr" -y >/dev/null
else
  die "need 7z/7za to extract ${RHR_ARC}"
fi

# RHR archive may drop files at top level or under a folder
find_rhr() {
  local name="$1"
  local found
  found="$(find "${EXTRACT_DIR}/rhr" -type f -name "${name}" | head -1)"
  [[ -n "${found}" ]] || die "missing ${name} inside RHR archive"
  echo "${found}"
}
cp "$(find_rhr "${RHR_TTF_REGULAR}")" "${EXTRACT_DIR}/RHR-Regular.ttf"
cp "$(find_rhr "${RHR_TTF_BOLD}")" "${EXTRACT_DIR}/RHR-Bold.ttf"

log "sources ready under ${EXTRACT_DIR}"
ls -lh \
  "${EXTRACT_DIR}/IosevkaCurly-Regular.ttf" \
  "${EXTRACT_DIR}/IosevkaCurly-Bold.ttf" \
  "${EXTRACT_DIR}/RHR-Regular.ttf" \
  "${EXTRACT_DIR}/RHR-Bold.ttf"
