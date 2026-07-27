#!/usr/bin/env bash
# Patch radon/out TTFs with Nerd Font icons (single-width icons, keep CJK 2-cell).
#
# Strategy (same as serif/):
#   - Prefer Docker image nerdfonts/patcher
#   - Else: local fontforge -script font-patcher
#   - ALWAYS --single-width-glyphs; NEVER --mono (would crush CJK to 1 cell)
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

need_cmd curl
ensure_dirs

NERD_OUT="${OUT_DIR}/nerd"
PATCHER_DIR="${WORK_DIR}/nerd-font-patcher"
PATCHER_ZIP="${DOWNLOADS_DIR}/FontPatcher-${NERD_FONTS_TAG}.zip"
PATCHER_URL="${NERD_FONTS_PATCHER_URL:-https://github.com/ryanoasis/nerd-fonts/releases/download/${NERD_FONTS_TAG}/FontPatcher.zip}"

mkdir -p "${NERD_OUT}" "${DOWNLOADS_DIR}"

mapfile -t BASE_FONTS < <(find "${OUT_DIR}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
if [[ ${#BASE_FONTS[@]} -eq 0 ]]; then
  die "no fonts in ${OUT_DIR}; run 03-merge.sh first"
fi

log "base fonts:"
printf '  %s\n' "${BASE_FONTS[@]}"

PATCH_ARGS=(
  --complete
  --single-width-glyphs
  --careful
  --makegroups 1
  --quiet
)

patch_with_docker() {
  need_cmd docker
  local img="${NERD_FONTS_DOCKER_IMAGE}"
  log "pulling/using docker image ${img}"
  docker pull "${img}" >/dev/null

  local stage="${WORK_DIR}/nerd-in"
  log "docker patch → ${NERD_OUT}"
  for f in "${BASE_FONTS[@]}"; do
    rm -rf "${stage}"
    mkdir -p "${stage}"
    cp -f "$f" "${stage}/"
    log "  docker: $(basename "$f")"
    docker run --rm \
      -e PN=1 \
      -v "${stage}:/in:ro" \
      -v "${NERD_OUT}:/out" \
      "${img}" \
      "${PATCH_ARGS[@]}"
  done
}

ensure_local_patcher() {
  if [[ -x "${PATCHER_DIR}/font-patcher" || -f "${PATCHER_DIR}/font-patcher" ]]; then
    return 0
  fi
  if [[ ! -f "${PATCHER_ZIP}" ]]; then
    log "downloading FontPatcher ${NERD_FONTS_TAG}"
    curl -fL --retry 3 -o "${PATCHER_ZIP}.partial" "${PATCHER_URL}"
    mv "${PATCHER_ZIP}.partial" "${PATCHER_ZIP}"
  else
    log "using cached ${PATCHER_ZIP}"
  fi
  rm -rf "${PATCHER_DIR}"
  mkdir -p "${PATCHER_DIR}"
  need_cmd unzip
  unzip -qo "${PATCHER_ZIP}" -d "${PATCHER_DIR}"
  [[ -f "${PATCHER_DIR}/font-patcher" ]] || die "FontPatcher.zip missing font-patcher"
}

patch_with_fontforge() {
  need_cmd fontforge
  ensure_local_patcher
  log "local fontforge patch → ${NERD_OUT}"
  for f in "${BASE_FONTS[@]}"; do
    log "  patching $(basename "$f")"
    fontforge -script "${PATCHER_DIR}/font-patcher" \
      "$f" \
      --glyphdir "${PATCHER_DIR}/src/glyphs/" \
      --outputdir "${NERD_OUT}" \
      "${PATCH_ARGS[@]}"
  done
}

if [[ "${NERD_PATCH_METHOD:-auto}" == "docker" ]] || {
  [[ "${NERD_PATCH_METHOD:-auto}" == "auto" ]] && command -v docker >/dev/null 2>&1
}; then
  if ! patch_with_docker; then
    log "docker patch failed; trying local fontforge"
    patch_with_fontforge
  fi
elif [[ "${NERD_PATCH_METHOD:-auto}" == "fontforge" ]] || command -v fontforge >/dev/null 2>&1; then
  patch_with_fontforge
else
  die "need docker or fontforge for Nerd patch (set NERD_PATCH_METHOD=docker|fontforge)"
fi

log "nerd products (pre-rename):"
ls -lh "${NERD_OUT}"/*.{ttf,otf} 2>/dev/null || ls -lh "${NERD_OUT}/"

PY=""
if [[ -x "${VENV_DIR}/bin/python" ]]; then
  PY="${VENV_DIR}/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
fi

RENAME="${RADON_ROOT}/scripts/rename_nerd_family.py"
if [[ -n "${PY}" && -f "${RENAME}" ]]; then
  mapfile -t RAW_NERD < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
  if [[ ${#RAW_NERD[@]} -gt 0 ]]; then
    log "shorten Nerd family names → ${NERD_FONT_FAMILY}"
    "${PY}" "${RENAME}" \
      --family "${NERD_FONT_FAMILY}" \
      --family-ps "${NERD_FONT_FAMILY_PS}" \
      --rename-file \
      "${RAW_NERD[@]}"
  fi
fi

FIX_METRICS="${RADON_ROOT}/scripts/fix-terminal-metrics.py"
if [[ -n "${PY}" && -f "${FIX_METRICS}" ]]; then
  mapfile -t NAMED_NERD < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
  if [[ ${#NAMED_NERD[@]} -gt 0 ]]; then
    log "fix terminal metrics (xAvgCharWidth / head bbox)"
    "${PY}" "${FIX_METRICS}" "${NAMED_NERD[@]}"
  fi
fi

log "nerd products:"
ls -lh "${NERD_OUT}"/*.{ttf,otf} 2>/dev/null || ls -lh "${NERD_OUT}/"

VERIFY="${RADON_ROOT}/scripts/verify-2to1.py"
if [[ -f "${VERIFY}" && -n "${PY}" ]]; then
  log "post-Nerd 2:1 verification"
  mapfile -t NERD_FONTS < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
  if [[ ${#NERD_FONTS[@]} -gt 0 ]]; then
    "${PY}" "${VERIFY}" --expect-half "${EN_ADV}" "${NERD_FONTS[@]}"
  fi
fi

log "done. Nerd fonts in ${NERD_OUT}"
