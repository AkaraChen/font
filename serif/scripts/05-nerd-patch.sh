#!/usr/bin/env bash
# Patch serif/out TTFs with Nerd Font icons (single-width icons, keep CJK 2-cell).
#
# Strategy:
#   - Use official FontPatcher from ryanoasis/nerd-fonts (pinned in pins.env)
#   - Prefer Docker image nerdfonts/patcher when available (no local FontForge)
#   - Else: local fontforge -script font-patcher
#   - ALWAYS pass --single-width-glyphs (icons = 1 cell)
#   - NEVER pass --mono / -s: that forces ALL existing glyphs (incl. CJK) to 1 cell
#
# Output: serif/out/nerd/*NerdFont*.ttf  (or *Nerd Font Mono* naming)
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

# Collect base fonts
mapfile -t BASE_FONTS < <(find "${OUT_DIR}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
if [[ ${#BASE_FONTS[@]} -eq 0 ]]; then
  die "no fonts in ${OUT_DIR}; run 04-build.sh first"
fi

log "base fonts:"
printf '  %s\n' "${BASE_FONTS[@]}"

# Patcher args: complete set + single-width icons + careful (keep existing glyphs)
# Do NOT pass --name: it collapses style to Regular and races Bold/Regular filenames.
# Short Windows-safe names applied afterwards via rename_nerd_family.py
# no --mono: preserve dual-width CJK (would force CJK to 1 cell)
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

  # One font per container: parallel patching with --name can race on filenames;
  # sequential also keeps Regular/Bold style suffixes stable.
  local stage="${WORK_DIR}/nerd-in"
  log "docker patch → ${NERD_OUT}"
  for f in "${BASE_FONTS[@]}"; do
    rm -rf "${stage}"
    mkdir -p "${stage}"
    cp -f "$f" "${stage}/"
    log "  docker: $(basename "$f")"
    # PN=1: single job; entrypoint finds fonts under /in
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

# Prefer docker (reproducible, no FontForge install); fall back to local.
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

# Short Windows-safe family names + stable filenames
RENAME="${SERIF_ROOT}/scripts/rename_nerd_family.py"
if [[ -n "${PY}" && -f "${RENAME}" ]]; then
  mapfile -t RAW_NERD < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
  if [[ ${#RAW_NERD[@]} -gt 0 ]]; then
    log "shorten Nerd family names → ${NERD_FONT_FAMILY:-SarasaNZSSlab NFM}"
    "${PY}" "${RENAME}" \
      --family "${NERD_FONT_FAMILY:-SarasaNZSSlab NFM}" \
      --family-ps "${NERD_FONT_FAMILY_PS:-SarasaNZSSlabNFM}" \
      --rename-file \
      "${RAW_NERD[@]}"
  fi
fi

# Dual-width hygiene: xAvgCharWidth=half + head bbox from half/full only.
# Mitigates terminal right-margin gaps when hosts use average/bbox as cell width.
FIX_METRICS="${SERIF_ROOT}/scripts/fix-terminal-metrics.py"
if [[ -n "${PY}" && -f "${FIX_METRICS}" ]]; then
  mapfile -t NAMED_NERD < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
  if [[ ${#NAMED_NERD[@]} -gt 0 ]]; then
    log "fix terminal metrics (xAvgCharWidth / head bbox)"
    "${PY}" "${FIX_METRICS}" "${NAMED_NERD[@]}"
  fi
fi

log "nerd products:"
ls -lh "${NERD_OUT}"/*.{ttf,otf} 2>/dev/null || ls -lh "${NERD_OUT}/"

# Optional post-verify
VERIFY="${SERIF_ROOT}/scripts/verify-2to1.py"
if [[ -f "${VERIFY}" && -n "${PY}" ]]; then
  log "post-Nerd 2:1 verification (with --check-nerd)"
  mapfile -t NERD_FONTS < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
  if [[ ${#NERD_FONTS[@]} -gt 0 ]]; then
    "${PY}" "${VERIFY}" --check-nerd "${NERD_FONTS[@]}"
  fi
fi

log "done. Nerd fonts in ${NERD_OUT}"
