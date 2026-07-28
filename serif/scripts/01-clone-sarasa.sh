#!/usr/bin/env bash
# Materialise the Sarasa Gothic source tree at the pinned commit into
# work/Sarasa-Gothic. Always leaves a clean tree (no quilt state) ready for
# 02-apply-quilt.sh.
#
# Preferred path (KIT-275): FONTKIT_SARASA_SRC points at `nix build .#sarasa-src`
# — fetchFromGitHub at SARASA_COMMIT, hash-pinned by SARASA_SRC_HASH. That is a
# 304 MiB tree fetched once per pin and shared by every later build; the clone
# below re-downloaded it on every cold run and verified only the commit id, not
# the bytes delivered for it.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs

# Keep node_modules across re-materialisations if present (speed)
KEEP_NM=""
if [[ -d "${SARASA_DIR}/node_modules" ]]; then
  KEEP_NM="${WORK_DIR}/.node_modules.bak"
  rm -rf "${KEEP_NM}"
  mv "${SARASA_DIR}/node_modules" "${KEEP_NM}"
fi

rm -rf "${SARASA_DIR}"

if [[ -n "${FONTKIT_SARASA_SRC:-}" ]]; then
  [[ -d "${FONTKIT_SARASA_SRC}" ]] \
    || die "FONTKIT_SARASA_SRC=${FONTKIT_SARASA_SRC} is not a directory"
  log "copying Sarasa ${SARASA_REF} (${SARASA_COMMIT}) from ${FONTKIT_SARASA_SRC}"
  mkdir -p "${SARASA_DIR}"
  # Store paths are read-only and quilt needs to patch in place.
  cp -R "${FONTKIT_SARASA_SRC}/." "${SARASA_DIR}/"
  chmod -R u+w "${SARASA_DIR}"
  # No .git in a fetchFromGitHub tree, so there is no rev-parse to run — the
  # store path *is* the verification: Nix rejected any tree whose NAR hash did
  # not equal SARASA_SRC_HASH.
  log "Sarasa source = ${SARASA_COMMIT} (nix, hash-verified)"
else
  need_cmd git
  log "cloning ${SARASA_REPO} @ ${SARASA_REF} (${SARASA_COMMIT})"
  git clone --depth 1 --branch "${SARASA_REF}" "${SARASA_REPO}" "${SARASA_DIR}"
  git -C "${SARASA_DIR}" checkout -f "${SARASA_COMMIT}"
  got="$(git -C "${SARASA_DIR}" rev-parse HEAD)"
  [[ "${got}" == "${SARASA_COMMIT}" ]] || die "expected ${SARASA_COMMIT}, got ${got}"
  log "Sarasa HEAD = ${got}"
fi

if [[ -n "${KEEP_NM}" && -d "${KEEP_NM}" ]]; then
  mv "${KEEP_NM}" "${SARASA_DIR}/node_modules"
fi
