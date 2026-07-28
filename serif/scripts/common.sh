#!/usr/bin/env bash
# Shared helpers for serif/ build scripts.
set -euo pipefail

SERIF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${SERIF_ROOT}/.." && pwd)"
# shellcheck disable=SC1091
source "${SERIF_ROOT}/pins.env"

WORK_DIR="${SERIF_ROOT}/work"
SARASA_DIR="${WORK_DIR}/Sarasa-Gothic"
DOWNLOADS_DIR="${WORK_DIR}/downloads"
VENV_DIR="${WORK_DIR}/venv"
OUT_DIR="${SERIF_ROOT}/out"

export QUILT_PATCHES="${SERIF_ROOT}/patches"

log() { printf '==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

# fontkit: the build steps shared by every family (lib/fontkit), invoked as
# `"${PY}" -m fontkit.<step>`. The working copy wins over any installed copy on
# purpose — an edit is live without a Nix rebuild, and CI gates the code that is
# actually committed. The Nix package exists for derivations that have no
# checkout; see nix/fontkit.nix.
export PYTHONPATH="${REPO_ROOT}/lib${PYTHONPATH:+:${PYTHONPATH}}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

ensure_dirs() {
  mkdir -p "${WORK_DIR}" "${DOWNLOADS_DIR}" "${OUT_DIR}"
}
