#!/usr/bin/env bash
# Apply quilt patch series onto work/Sarasa-Gothic.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

need_cmd quilt
[[ -d "${SARASA_DIR}" ]] || die "missing ${SARASA_DIR}; run 01-clone-sarasa.sh first"
[[ -f "${QUILT_PATCHES}/series" ]] || die "missing ${QUILT_PATCHES}/series"

# Fresh quilt state each run
rm -rf "${SARASA_DIR}/.pc"

cd "${SARASA_DIR}"
export QUILT_PATCHES
log "applying quilt series from ${QUILT_PATCHES}"
quilt push -a
log "applied:"
quilt applied
