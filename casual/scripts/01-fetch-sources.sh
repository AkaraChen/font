#!/usr/bin/env bash
# Fetch pinned Recursive zip members + Yozai TTFs.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
need_cmd unzip
PY="$(python_bin)"

ZIP_PATH="${DOWNLOADS_DIR}/ArrowType-Recursive-${RECURSIVE_RELEASE_TAG}.zip"
download_file "${RECURSIVE_ZIP_URL}" "${ZIP_PATH}" "${RECURSIVE_ZIP_SHA256}"

log "extracting Recursive Mono Casual statics"
TMP_EXTRACT="${WORK_DIR}/recursive-extract"
rm -rf "${TMP_EXTRACT}"
mkdir -p "${TMP_EXTRACT}"
unzip -qo "${ZIP_PATH}" \
  "${RECURSIVE_TTF_REGULAR}" \
  "${RECURSIVE_TTF_BOLD}" \
  -d "${TMP_EXTRACT}"

cp "${TMP_EXTRACT}/${RECURSIVE_TTF_REGULAR}" "${EXTRACT_DIR}/RecursiveMonoCsl-Regular.ttf"
cp "${TMP_EXTRACT}/${RECURSIVE_TTF_BOLD}" "${EXTRACT_DIR}/RecursiveMonoCsl-Bold.ttf"
verify_sha256 "${EXTRACT_DIR}/RecursiveMonoCsl-Regular.ttf" "${RECURSIVE_SHA256_REGULAR}"
verify_sha256 "${EXTRACT_DIR}/RecursiveMonoCsl-Bold.ttf" "${RECURSIVE_SHA256_BOLD}"

log "fetching Yozai ${YOZAI_RELEASE_TAG}"
download_file "${YOZAI_TTF_URL_REGULAR}" "${EXTRACT_DIR}/Yozai-Regular.ttf" "${YOZAI_SHA256_REGULAR}"
download_file "${YOZAI_TTF_URL_MEDIUM}" "${EXTRACT_DIR}/Yozai-Medium.ttf" "${YOZAI_SHA256_MEDIUM}"

# Upstream licences
if [[ -f "${CASUAL_ROOT}/licenses/OFL-Recursive.txt" ]]; then
  log "kept in-tree licenses/OFL-Recursive.txt"
else
  die "missing licenses/OFL-Recursive.txt"
fi
if [[ -f "${CASUAL_ROOT}/licenses/OFL-Yozai.txt" ]]; then
  log "kept in-tree licenses/OFL-Yozai.txt"
else
  # best-effort refresh from upstream
  raw="${YOZAI_REPO/github.com/raw.githubusercontent.com}/master/OFL.txt"
  if curl -fsSL "${raw}" -o "${CASUAL_ROOT}/licenses/OFL-Yozai.txt"; then
    log "refreshed licenses/OFL-Yozai.txt"
  else
    die "missing licenses/OFL-Yozai.txt"
  fi
fi

log "sources ready under ${EXTRACT_DIR}"
ls -lh "${EXTRACT_DIR}"
