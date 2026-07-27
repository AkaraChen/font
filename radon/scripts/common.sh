#!/usr/bin/env bash
# Shared helpers for radon/ build scripts.
set -euo pipefail

RADON_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "${RADON_ROOT}/pins.env"

WORK_DIR="${RADON_ROOT}/work"
DOWNLOADS_DIR="${WORK_DIR}/downloads"
EXTRACT_DIR="${WORK_DIR}/src"
VENV_DIR="${WORK_DIR}/venv"
OUT_DIR="${RADON_ROOT}/out"
PREP_DIR="${WORK_DIR}/prepared"

log() { printf '==> %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

ensure_dirs() {
  mkdir -p "${WORK_DIR}" "${DOWNLOADS_DIR}" "${EXTRACT_DIR}" "${OUT_DIR}" "${PREP_DIR}"
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

ensure_python() {
  if [[ -x "${VENV_DIR}/bin/python" ]] && "${VENV_DIR}/bin/python" -c "import fontTools, pathops" 2>/dev/null; then
    return 0
  fi
  mkdir -p "${WORK_DIR}"
  log "creating venv at ${VENV_DIR}"
  if command -v uv >/dev/null 2>&1; then
    uv venv "${VENV_DIR}"
    uv pip install --python "${VENV_DIR}/bin/python" -q 'fonttools>=4.50' brotli skia-pathops
    uv pip install --python "${VENV_DIR}/bin/python" -q Pillow \
      || log "Pillow not installed; sample render will be skipped"
  else
    need_cmd python3
    python3 -m venv "${VENV_DIR}"
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
    python -m pip install -q --upgrade pip
    python -m pip install -q 'fonttools>=4.50' brotli skia-pathops
    python -m pip install -q Pillow \
      || log "Pillow not installed; sample render will be skipped"
  fi
  "${VENV_DIR}/bin/python" -c "import fontTools, pathops" \
    || die "fontTools/pathops not importable in ${VENV_DIR}"
}

python_bin() {
  ensure_python
  echo "${VENV_DIR}/bin/python"
}
