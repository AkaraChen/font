#!/usr/bin/env bash
# Fetch pinned Monaspace Radon (frozen) + LXGW WenKai Medium.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
need_cmd unzip

FROZEN_ZIP="${DOWNLOADS_DIR}/monaspace-frozen-${MONASPACE_TAG}.zip"
WENKAI_MED="${DOWNLOADS_DIR}/LXGWWenKai-Medium.ttf"

download_file "${MONASPACE_FROZEN_ZIP_URL}" "${FROZEN_ZIP}" "${MONASPACE_FROZEN_ZIP_SHA256}"
download_file "${WENKAI_TTF_MEDIUM_URL}" "${WENKAI_MED}" "${WENKAI_TTF_MEDIUM_SHA256}"

# Optional Regular (for stroke A/B; not required for product)
if [[ -n "${WENKAI_TTF_REGULAR_URL:-}" && -n "${WENKAI_TTF_REGULAR_SHA256:-}" ]]; then
  download_file "${WENKAI_TTF_REGULAR_URL}" \
    "${DOWNLOADS_DIR}/LXGWWenKai-Regular.ttf" \
    "${WENKAI_TTF_REGULAR_SHA256}" || true
fi

log "extracting Radon frozen TTFs"
rm -rf "${EXTRACT_DIR}/radon"
mkdir -p "${EXTRACT_DIR}/radon"
unzip -qo "${FROZEN_ZIP}" \
  "${RADON_TTF_REGULAR}" \
  "${RADON_TTF_BOLD}" \
  -d "${EXTRACT_DIR}/radon"

cp "${EXTRACT_DIR}/radon/${RADON_TTF_REGULAR}" "${EXTRACT_DIR}/MonaspaceRadon-Regular.ttf"
cp "${EXTRACT_DIR}/radon/${RADON_TTF_BOLD}" "${EXTRACT_DIR}/MonaspaceRadon-Bold.ttf"
cp "${WENKAI_MED}" "${EXTRACT_DIR}/LXGWWenKai-Medium.ttf"

# Bundle OFL texts if present in monaspace zip
if unzip -l "${FROZEN_ZIP}" | grep -qi 'LICENSE\|OFL'; then
  mkdir -p "${RADON_ROOT}/licenses"
  unzip -p "${FROZEN_ZIP}" '**/LICENSE*' 2>/dev/null | head -c 200000 \
    > "${RADON_ROOT}/licenses/LICENSE-Monaspace.txt" || true
fi

# WenKai OFL from GitHub raw (best-effort; also ship a short notice)
mkdir -p "${RADON_ROOT}/licenses"
if [[ ! -s "${RADON_ROOT}/licenses/OFL-LXGW-WenKai.txt" ]]; then
  curl -fsSL --retry 2 \
    "https://raw.githubusercontent.com/lxgw/LxgwWenKai/${WENKAI_TAG}/OFL.txt" \
    -o "${RADON_ROOT}/licenses/OFL-LXGW-WenKai.txt" \
    || log "could not fetch WenKai OFL (non-fatal)"
fi
if [[ ! -s "${RADON_ROOT}/licenses/LICENSE-Monaspace.txt" ]]; then
  curl -fsSL --retry 2 \
    "https://raw.githubusercontent.com/githubnext/monaspace/${MONASPACE_TAG}/LICENSE" \
    -o "${RADON_ROOT}/licenses/LICENSE-Monaspace.txt" \
    || log "could not fetch Monaspace LICENSE (non-fatal)"
fi

log "sources ready under ${EXTRACT_DIR}"
ls -lh \
  "${EXTRACT_DIR}/MonaspaceRadon-Regular.ttf" \
  "${EXTRACT_DIR}/MonaspaceRadon-Bold.ttf" \
  "${EXTRACT_DIR}/LXGWWenKai-Medium.ttf"
