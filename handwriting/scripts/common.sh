#!/usr/bin/env bash
# Shared helpers for handwriting/ build scripts.
set -euo pipefail

HANDWRITING_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${HANDWRITING_ROOT}/.." && pwd)"
# shellcheck disable=SC1091
source "${HANDWRITING_ROOT}/pins.env"

WORK_DIR="${HANDWRITING_ROOT}/work"
DOWNLOADS_DIR="${WORK_DIR}/downloads"
EXTRACT_DIR="${WORK_DIR}/src"
STAGE_DIR="${WORK_DIR}/stage"
VENV_DIR="${WORK_DIR}/venv"
OUT_DIR="${HANDWRITING_ROOT}/out"
# Stroke measuring / embolden tools are shared with serif/ — not duplicated here.
SERIF_TOOLS="${REPO_ROOT}/serif/tools"

log() { printf '==> %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

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

download_file() {
  local url="$1" dest="$2" sha="$3"
  if [[ -f "${dest}" ]] && [[ "$(sha256_of "${dest}")" == "${sha}" ]]; then
    log "cached $(basename "${dest}")"
    return 0
  fi
  [[ -f "${dest}" ]] && log "stale cache for $(basename "${dest}"), re-downloading"
  need_cmd curl
  log "downloading ${url}"
  curl -fL --retry 3 --retry-delay 2 -o "${dest}.partial" "${url}"
  mv "${dest}.partial" "${dest}"
  verify_sha256 "${dest}" "${sha}"
}

ensure_python() {
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
      || log "Pillow/freetype-py not installed; sample render will be skipped"
  else
    need_cmd python3
    python3 -m venv "${VENV_DIR}"
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
    python -m pip install -q --upgrade pip
    python -m pip install -q 'fonttools>=4.50' brotli skia-pathops uharfbuzz
    python -m pip install -q Pillow freetype-py numpy \
      || log "Pillow/freetype-py not installed; sample render will be skipped"
  fi
  "${VENV_DIR}/bin/python" -c "import fontTools, pathops, uharfbuzz" \
    || die "fontTools + skia-pathops + uharfbuzz not importable in ${VENV_DIR}"
}

python_bin() {
  ensure_python
  echo "${VENV_DIR}/bin/python"
}
