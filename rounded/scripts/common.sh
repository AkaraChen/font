#!/usr/bin/env bash
# Shared helpers for rounded/ build scripts.
set -euo pipefail

ROUNDED_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${ROUNDED_ROOT}/.." && pwd)"
# shellcheck disable=SC1091
source "${ROUNDED_ROOT}/pins.env"

WORK_DIR="${ROUNDED_ROOT}/work"
DOWNLOADS_DIR="${WORK_DIR}/downloads"
EXTRACT_DIR="${WORK_DIR}/src"
VENV_DIR="${WORK_DIR}/venv"
OUT_DIR="${ROUNDED_ROOT}/out"
# Reuse serif embolden / stroke tools (no copy)
SERIF_TOOLS="${REPO_ROOT}/serif/tools"

log() { printf '==> %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

ensure_dirs() {
  mkdir -p "${WORK_DIR}" "${DOWNLOADS_DIR}" "${EXTRACT_DIR}" "${OUT_DIR}"
}

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

verify_sha256() {
  local file="$1" expected="$2"
  local got
  got="$(sha256_of "${file}")"
  [[ "${got}" == "${expected}" ]] || die "sha256 mismatch for ${file}: expected ${expected}, got ${got}"
}

download_file() {
  local url="$1" dest="$2" sha="$3"
  if [[ -f "${dest}" ]]; then
    if [[ "$(sha256_of "${dest}")" == "${sha}" ]]; then
      log "cached $(basename "${dest}")"
      return 0
    fi
    log "stale cache for $(basename "${dest}"), re-downloading"
    rm -f "${dest}"
  fi
  need_cmd curl
  log "downloading ${url}"
  curl -fL --retry 3 --retry-delay 2 -o "${dest}.partial" "${url}"
  mv "${dest}.partial" "${dest}"
  verify_sha256 "${dest}" "${sha}"
}

download_zip() {
  download_file "$1" "$2" "$3"
}

ensure_python() {
  # A pre-provisioned interpreter (the Nix devShell sets this) replaces the venv
  # entirely: no pip, no network, no version drift. It must already import
  # everything this family needs — missing modules are a hard failure, never a
  # silently degraded build.
  if [[ -n "${FONTKIT_PYTHON:-}" ]]; then
    "${FONTKIT_PYTHON}" -c "import fontTools, pathops, PIL" \
      || die "FONTKIT_PYTHON=${FONTKIT_PYTHON} cannot import: fontTools, pathops, PIL"
    return 0
  fi
  if [[ -x "${VENV_DIR}/bin/python" ]] && "${VENV_DIR}/bin/python" -c "import fontTools" 2>/dev/null; then
    # pathops needed for Bold embolden
    if "${VENV_DIR}/bin/python" -c "import pathops" 2>/dev/null; then
      return 0
    fi
  fi
  mkdir -p "${WORK_DIR}"
  log "creating venv at ${VENV_DIR}"
  if command -v uv >/dev/null 2>&1; then
    uv venv "${VENV_DIR}"
    uv pip install --python "${VENV_DIR}/bin/python" -q 'fonttools>=4.50' brotli 'skia-pathops'
    uv pip install --python "${VENV_DIR}/bin/python" -q Pillow \
      || die "sample-render dependencies failed to install; this used to be a warning that let the build \"succeed\" with no sample sheet"
  else
    need_cmd python3
    python3 -m venv "${VENV_DIR}"
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
    python -m pip install -q --upgrade pip
    python -m pip install -q 'fonttools>=4.50' brotli 'skia-pathops'
    python -m pip install -q Pillow \
      || die "sample-render dependencies failed to install; this used to be a warning that let the build \"succeed\" with no sample sheet"
  fi
  "${VENV_DIR}/bin/python" -c "import fontTools, pathops" \
    || die "fontTools/pathops not importable in ${VENV_DIR}"
}

python_bin() {
  ensure_python
  if [[ -n "${FONTKIT_PYTHON:-}" ]]; then
    echo "${FONTKIT_PYTHON}"
  else
    echo "${VENV_DIR}/bin/python"
  fi
}
