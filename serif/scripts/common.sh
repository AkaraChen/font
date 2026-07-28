#!/usr/bin/env bash
# Shared helpers for serif/ build scripts.
set -euo pipefail

SERIF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${SERIF_ROOT}/.." && pwd)"

# The working copy wins over an installed fontkit so manifest validation and
# shell compatibility use the code being built.
export PYTHONPATH="${REPO_ROOT}/lib${PYTHONPATH:+:${PYTHONPATH}}"
PY="${FONTKIT_PYTHON:-python3}"
command -v "${PY}" >/dev/null 2>&1 || {
  printf 'error: missing Python interpreter: %s\n' "${PY}" >&2
  exit 1
}
"${PY}" -c 'import pydantic' 2>/dev/null || {
  printf '%s\n' \
    'error: serif manifest validation requires the pinned dev shell.' \
    'run from the repository root: nix develop --command serif/scripts/build.sh' >&2
  exit 1
}
eval "$("${PY}" -m fontkit.manifest shell "${SERIF_ROOT}/font.toml")"

# Pinned artifacts come from the Nix store when it has been realised
# (FONTKIT_SRC_CACHE), and from curl when it has not. Same sha256 gate either
# way — see tools/src-cache.sh.
# shellcheck disable=SC1091
source "${REPO_ROOT}/tools/src-cache.sh"

download_file() { src_fetch "$@"; }
download_zip() { src_fetch "$@"; }

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
need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

# serif fetched LXGWNeoZhiSongPlus.ttf and the Sarasa Term donor with a bare
# curl and no integrity check at all — the only family that did. Both now have
# a sha256 in font.toml, and both go through src_fetch like everywhere else.
sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

verify_sha256() {
  local file="$1" expected="$2" got
  got="$(sha256_of "${file}")"
  [[ "${got}" == "${expected}" ]] || die "sha256 mismatch for ${file}: expected ${expected}, got ${got}"
}

ensure_dirs() {
  mkdir -p "${WORK_DIR}" "${DOWNLOADS_DIR}" "${OUT_DIR}"
}
