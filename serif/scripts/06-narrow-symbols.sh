#!/usr/bin/env bash
# Make advance widths agree with Unicode East_Asian_Width, then re-fix metrics.
#
# Why this step exists:
#   A terminal never asks the font how wide a character is -- it sizes the cell
#   from Unicode's EAW table (wcwidth). EAW N/Na/H always get exactly 1 cell.
#   Sarasa *Mono* draws many of those symbols (⏵ ✓ ⌘ ↑ …) at 2-cell advance,
#   so the ink overflows into the next cell and the line stops lining up.
#   Sarasa *Term* has proper 1-cell drawings of the same shapes; we transplant
#   them (falling back to geometric fitting for codepoints Term lacks).
#
# Runs after 05-nerd-patch.sh. Saving the font recomputes head bbox, so
# fix-terminal-metrics.py is re-run here rather than left to 05.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

need_cmd curl
ensure_dirs

NERD_OUT="${OUT_DIR}/nerd"
DONOR_DIR="${WORK_DIR}/term-donor"
DONOR_ARCHIVE="${DOWNLOADS_DIR}/$(basename "${SARASA_TERM_ARCHIVE_URL}")"

mapfile -t FONTS < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) | sort)
[[ ${#FONTS[@]} -gt 0 ]] || die "no fonts in ${NERD_OUT}; run 05-nerd-patch.sh first"

PY=""
if [[ -n "${FONTKIT_PYTHON:-}" ]]; then
  "${FONTKIT_PYTHON}" -c "import fontTools" \
    || die "FONTKIT_PYTHON=${FONTKIT_PYTHON} cannot import: fontTools"
  PY="${FONTKIT_PYTHON}"
elif [[ -x "${VENV_DIR}/bin/python" ]]; then
  PY="${VENV_DIR}/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  die "need python3 (or ${VENV_DIR}/bin/python)"
fi

if [[ ! -f "${DONOR_ARCHIVE}" ]]; then
  log "downloading half-width symbol donor"
  curl -fL --retry 3 -o "${DONOR_ARCHIVE}.partial" "${SARASA_TERM_ARCHIVE_URL}"
  mv "${DONOR_ARCHIVE}.partial" "${DONOR_ARCHIVE}"
else
  log "using cached ${DONOR_ARCHIVE}"
fi

mkdir -p "${DONOR_DIR}"
if [[ ! -f "${DONOR_DIR}/${SARASA_TERM_REGULAR}" ]]; then
  log "extracting donor → ${DONOR_DIR}"
  if command -v 7zz >/dev/null 2>&1; then
    7zz x -y -o"${DONOR_DIR}" "${DONOR_ARCHIVE}" \
      "${SARASA_TERM_REGULAR}" "${SARASA_TERM_BOLD}" >/dev/null
  elif command -v 7z >/dev/null 2>&1; then
    7z x -y -o"${DONOR_DIR}" "${DONOR_ARCHIVE}" \
      "${SARASA_TERM_REGULAR}" "${SARASA_TERM_BOLD}" >/dev/null
  else
    "${PY}" - "${DONOR_ARCHIVE}" "${DONOR_DIR}" \
      "${SARASA_TERM_REGULAR}" "${SARASA_TERM_BOLD}" <<'PYEOF'
import sys
try:
    import py7zr
except ImportError:
    sys.exit("need 7z/7zz on PATH, or `pip install py7zr` into the venv")
archive, out, *targets = sys.argv[1:]
with py7zr.SevenZipFile(archive) as a:
    a.extract(path=out, targets=targets)
PYEOF
  fi
fi

for f in "${FONTS[@]}"; do
  case "$(basename "$f")" in
    *Bold*) donor="${DONOR_DIR}/${SARASA_TERM_BOLD}" ;;
    *) donor="${DONOR_DIR}/${SARASA_TERM_REGULAR}" ;;
  esac
  [[ -f "${donor}" ]] || die "donor not found: ${donor}"
  log "narrow EAW symbols: $(basename "$f")  (donor $(basename "${donor}"))"
  "${PY}" "${SERIF_ROOT}/scripts/narrow-symbol-widths.py" "$f" --donor "${donor}"
done

# narrow-symbol-widths.py saves via fontTools, which recomputes head from all
# glyphs; redo the dual-width metric hygiene afterwards.
log "re-fix terminal metrics (xAvgCharWidth / head bbox)"
"${PY}" "${SERIF_ROOT}/scripts/fix-terminal-metrics.py" "${FONTS[@]}"

# Iosevka parks richer programming ligations under dlig / language packs.
# Editors turn on calt with "font ligatures", but almost never dlig — fold
# dlig into default calt so ++ -- ## ~~ counter-arrows logic etc. apply.
log "expand default calt with discretionary ligatures (dlig)"
"${PY}" "${SERIF_ROOT}/scripts/expand-default-ligatures.py" "${FONTS[@]}"

log "final verification (2:1 + nerd + EAW)"
"${PY}" "${SERIF_ROOT}/scripts/verify-2to1.py" --check-nerd --check-eaw "${FONTS[@]}"

log "done. products in ${NERD_OUT}"
