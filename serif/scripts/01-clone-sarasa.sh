#!/usr/bin/env bash
# Clone Sarasa Gothic at the pinned ref into work/Sarasa-Gothic.
# Always leaves a clean tree (no quilt state) ready for 02-apply-quilt.sh.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

need_cmd git
ensure_dirs

# Keep node_modules across re-clones if present (speed)
KEEP_NM=""
if [[ -d "${SARASA_DIR}/node_modules" ]]; then
  KEEP_NM="${WORK_DIR}/.node_modules.bak"
  rm -rf "${KEEP_NM}"
  mv "${SARASA_DIR}/node_modules" "${KEEP_NM}"
fi

rm -rf "${SARASA_DIR}"
log "cloning ${SARASA_REPO} @ ${SARASA_REF} (${SARASA_COMMIT})"
git clone --depth 1 --branch "${SARASA_REF}" "${SARASA_REPO}" "${SARASA_DIR}"
git -C "${SARASA_DIR}" checkout -f "${SARASA_COMMIT}"

if [[ -n "${KEEP_NM}" && -d "${KEEP_NM}" ]]; then
  mv "${KEEP_NM}" "${SARASA_DIR}/node_modules"
fi

got="$(git -C "${SARASA_DIR}" rev-parse HEAD)"
[[ "${got}" == "${SARASA_COMMIT}" ]] || die "expected ${SARASA_COMMIT}, got ${got}"
log "Sarasa HEAD = ${got}"
