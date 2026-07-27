#!/usr/bin/env bash
# Fetch pinned Monaspace Radon NF members + LXGW WenKai TTFs.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

log "fetching Radon NF members from ${MONASPACE_RELEASE_TAG} (ranged, not the whole 315 MiB zip)"
"${PY}" "${HANDWRITING_ROOT}/scripts/fetch_zip_member.py" "${MONASPACE_NF_ZIP_URL}" \
  --member "${RADON_NF_MEMBER_REGULAR}" \
  --out "${EXTRACT_DIR}/MonaspaceRadonNF-Regular.otf" \
  --sha256 "${RADON_NF_SHA256_REGULAR}" \
  --member "${RADON_NF_MEMBER_BOLD}" \
  --out "${EXTRACT_DIR}/MonaspaceRadonNF-Bold.otf" \
  --sha256 "${RADON_NF_SHA256_BOLD}"

log "fetching LXGW WenKai ${WENKAI_RELEASE_TAG}"
download_file "${WENKAI_TTF_URL_MEDIUM}" "${EXTRACT_DIR}/LXGWWenKai-Medium.ttf" "${WENKAI_SHA256_MEDIUM}"
# Regular is not in the product (Medium is the measured match for Radon Regular)
# but calibrate-stroke.sh surveys it, so keep it pinned and cached.
download_file "${WENKAI_TTF_URL_REGULAR}" "${EXTRACT_DIR}/LXGWWenKai-Regular.ttf" "${WENKAI_SHA256_REGULAR}"

# Upstream licences (OFL 1.1 for both); keep the in-tree copies fresh.
refresh_license() {
  local repo="$1" upstream_file="$2" name="$3"
  local raw="${repo/github.com/raw.githubusercontent.com}/main/${upstream_file}"
  if curl -fsSL "${raw}" -o "${WORK_DIR}/${name}.new"; then
    mv "${WORK_DIR}/${name}.new" "${HANDWRITING_ROOT}/licenses/${name}"
    log "refreshed licenses/${name}"
  else
    rm -f "${WORK_DIR}/${name}.new"
    [[ -f "${HANDWRITING_ROOT}/licenses/${name}" ]] \
      || die "could not fetch ${raw} and no in-tree licenses/${name}"
    log "kept in-tree licenses/${name}"
  fi
}

refresh_license "${MONASPACE_REPO}" LICENSE OFL-Monaspace.txt
refresh_license "${WENKAI_REPO}" OFL.txt OFL-LXGWWenKai.txt

log "sources ready under ${EXTRACT_DIR}"
ls -lh "${EXTRACT_DIR}"
