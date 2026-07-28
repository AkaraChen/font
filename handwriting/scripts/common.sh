#!/usr/bin/env bash
# Shared helpers for handwriting/ build scripts.
set -euo pipefail

HANDWRITING_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${HANDWRITING_ROOT}/.." && pwd)"
# shellcheck disable=SC1091
source "${HANDWRITING_ROOT}/pins.env"

# Pinned artifacts come from the Nix store when it has been realised
# (FONTKIT_SRC_CACHE), and from curl when it has not. Same sha256 gate either
# way — see tools/src-cache.sh.
# shellcheck disable=SC1091
source "${REPO_ROOT}/tools/src-cache.sh"

download_file() { src_fetch "$@"; }
download_zip() { src_fetch "$@"; }

WORK_DIR="${HANDWRITING_ROOT}/work"
DOWNLOADS_DIR="${WORK_DIR}/downloads"
EXTRACT_DIR="${WORK_DIR}/src"
STAGE_DIR="${WORK_DIR}/stage"
VENV_DIR="${WORK_DIR}/venv"
OUT_DIR="${HANDWRITING_ROOT}/out"

log() { printf '==> %s\n' "$*" >&2; }
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
  mkdir -p "${WORK_DIR}" "${DOWNLOADS_DIR}" "${EXTRACT_DIR}" "${STAGE_DIR}" "${OUT_DIR}"
}

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


ensure_python() {
  # A pre-provisioned interpreter (the Nix devShell sets this) replaces the venv
  # entirely: no pip, no network, no version drift. It must already import
  # everything this family needs — missing modules are a hard failure, never a
  # silently degraded build.
  if [[ -n "${FONTKIT_PYTHON:-}" ]]; then
    "${FONTKIT_PYTHON}" -c "import fontTools, pathops, uharfbuzz, PIL, freetype, numpy" \
      || die "FONTKIT_PYTHON=${FONTKIT_PYTHON} cannot import: fontTools, pathops, uharfbuzz, PIL, freetype, numpy"
    return 0
  fi
  if [[ -x "${VENV_DIR}/bin/python" ]] \
    && "${VENV_DIR}/bin/python" -c "import fontTools, pathops, uharfbuzz" 2>/dev/null; then
    return 0
  fi
  mkdir -p "${WORK_DIR}"
  log "creating venv at ${VENV_DIR}"
  # uharfbuzz is required: the ligature gate shapes text rather than trusting
  # feature tags. Pillow / freetype-py are optional (sample rendering only).
  if command -v uv >/dev/null 2>&1; then
    uv venv "${VENV_DIR}"
    uv pip install --python "${VENV_DIR}/bin/python" -q \
      'fonttools>=4.50' brotli skia-pathops uharfbuzz
    uv pip install --python "${VENV_DIR}/bin/python" -q Pillow freetype-py numpy \
      || die "sample-render dependencies failed to install; this used to be a warning that let the build \"succeed\" with no sample sheet"
  else
    need_cmd python3
    python3 -m venv "${VENV_DIR}"
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
    python -m pip install -q --upgrade pip
    python -m pip install -q 'fonttools>=4.50' brotli skia-pathops uharfbuzz
    python -m pip install -q Pillow freetype-py numpy \
      || die "sample-render dependencies failed to install; this used to be a warning that let the build \"succeed\" with no sample sheet"
  fi
  "${VENV_DIR}/bin/python" -c "import fontTools, pathops, uharfbuzz" \
    || die "fontTools + skia-pathops + uharfbuzz not importable in ${VENV_DIR}"
}

python_bin() {
  ensure_python
  if [[ -n "${FONTKIT_PYTHON:-}" ]]; then
    echo "${FONTKIT_PYTHON}"
  else
    echo "${VENV_DIR}/bin/python"
  fi
}
