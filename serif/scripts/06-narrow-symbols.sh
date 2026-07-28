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
# Runs after 05-nerd-patch.sh. The narrow pass saves the font again, so the
# mono advertisement is re-asserted here rather than left to 05.
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

download_file "${SARASA_TERM_ARCHIVE_URL}" "${DONOR_ARCHIVE}" "${SARASA_TERM_ARCHIVE_SHA256}"

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
  "${PY}" -m fontkit.narrow_symbol_widths "$f" --donor "${donor}" \
    --protect-ambiguous --widen-shared skip
done

# Re-assert the mono advertisement after the narrow pass's own save.
log "re-fix terminal metrics (isFixedPitch / PANOSE / xAvgCharWidth)"
"${PY}" -m fontkit.fix_terminal_metrics "${FONTS[@]}"

# Iosevka parks richer programming ligations under dlig / language packs.
# Editors turn on calt with "font ligatures", but almost never dlig — fold
# dlig into default calt so ++ -- ## ~~ counter-arrows logic etc. apply.
log "expand default calt with discretionary ligatures (dlig)"
"${PY}" "${SERIF_ROOT}/scripts/expand-default-ligatures.py" "${FONTS[@]}"

log "final verification (2:1 + nerd + EAW)"
"${PY}" -m fontkit.verify2to1 --profile dense --check-nerd --check-eaw "${FONTS[@]}"

log "done. products in ${NERD_OUT}"
