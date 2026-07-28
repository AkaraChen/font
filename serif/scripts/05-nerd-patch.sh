#!/usr/bin/env bash
# Patch serif/out TTFs with Nerd Font icons (single-width icons, keep CJK 2-cell).
#
# Strategy:
#   - Use the pinned ryanoasis/nerd-fonts checkout (see font.toml / nix/sources)
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
# The patcher is a pinned checkout now, not a release zip — `just build serif`
# realises it and exports this. See nix/sources/default.nix for why a commit.
PATCHER_SRC="${FONTKIT_FONT_PATCHER:-}"

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

ensure_local_patcher() {
  if [[ -f "${PATCHER_DIR}/font-patcher" ]]; then
    return 0
  fi
  [[ -n "${PATCHER_SRC}" ]] \
    || die "FONTKIT_FONT_PATCHER is unset — run this via \`just build serif\`, which realises .#font-patcher"
  # Copied rather than used in place: font-patcher resolves its helper modules
  # and glyph sources relative to its own path, and writes nothing — but the
  # store path is read-only and this keeps serif's behaviour identical to the
  # six derivation families, which stage the same way.
  rm -rf "${PATCHER_DIR}"
  mkdir -p "${PATCHER_DIR}"
  cp -R "${PATCHER_SRC}"/. "${PATCHER_DIR}/"
  chmod -R u+w "${PATCHER_DIR}"
  [[ -f "${PATCHER_DIR}/font-patcher" ]] || die "${PATCHER_SRC} has no font-patcher"
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

# One patcher, no ladder. The container existed because FontForge used to be
# "whatever the maintainer installed", which meant two runners could produce
# two different fonts and nothing would say so. The toolchain is pinned now.
patch_with_fontforge

log "nerd products (pre-rename):"
ls -lh "${NERD_OUT}"/*.{ttf,otf} 2>/dev/null || ls -lh "${NERD_OUT}/"

PY=""
if [[ -n "${FONTKIT_PYTHON:-}" ]]; then
  "${FONTKIT_PYTHON}" -c "import fontTools" \
    || die "FONTKIT_PYTHON=${FONTKIT_PYTHON} cannot import: fontTools"
  PY="${FONTKIT_PYTHON}"
elif [[ -x "${VENV_DIR}/bin/python" ]]; then
  PY="${VENV_DIR}/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
fi

# Short Windows-safe family names + stable filenames
if [[ -n "${PY}" ]]; then
  mapfile -t RAW_NERD < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
  if [[ ${#RAW_NERD[@]} -gt 0 ]]; then
    log "shorten Nerd family names → ${NERD_FONT_FAMILY:-SarasaNZSSlab NFM}"
    "${PY}" -m fontkit.rename_nerd_family \
      --family "${NERD_FONT_FAMILY:-SarasaNZSSlab NFM}" \
      --family-ps "${NERD_FONT_FAMILY_PS:-SarasaNZSSlabNFM}" \
      --rename-file \
      "${RAW_NERD[@]}"
  fi
fi

# The Nerd patch runs FontForge, which clears post.isFixedPitch on a
# dual-width font and drops the product out of every "monospace only" picker.
# Restore that, PANOSE bProportion and the half-cell xAvgCharWidth.
if [[ -n "${PY}" ]]; then
  mapfile -t NAMED_NERD < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
  if [[ ${#NAMED_NERD[@]} -gt 0 ]]; then
    log "fix terminal metrics (isFixedPitch / PANOSE / xAvgCharWidth)"
    "${PY}" -m fontkit.fix_terminal_metrics "${NAMED_NERD[@]}"
  fi
fi

log "nerd products:"
ls -lh "${NERD_OUT}"/*.{ttf,otf} 2>/dev/null || ls -lh "${NERD_OUT}/"

# Optional post-verify
if [[ -n "${PY}" ]]; then
  log "post-Nerd 2:1 verification (with --check-nerd)"
  mapfile -t NERD_FONTS < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
  if [[ ${#NERD_FONTS[@]} -gt 0 ]]; then
    "${PY}" -m fontkit.verify2to1 --profile dense --check-nerd "${NERD_FONTS[@]}"
  fi
fi

log "done. Nerd fonts in ${NERD_OUT}"
