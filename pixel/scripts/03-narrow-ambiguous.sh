#!/usr/bin/env bash
# Narrow EAW=Ambiguous punctuation (“ ” ‘ ’ … · ‥ ․ ‧) to the half cell.
#
# Fusion's zh_hans flavor draws these nine at 1200 with the ink in the right
# half; terminals give an Ambiguous codepoint one cell, so `“心` paints the
# quote on top of the next character. Fusion's own latin flavor of the same
# release draws them at 600 on the same grid — transplant those.
#
# Runs before the Nerd patch so the metric hygiene in 04 sees the final
# advances.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

DONOR="${EXTRACT_DIR}/staged/fusion-halfwidth-donor.ttf"
[[ -f "${DONOR}" ]] || die "missing ${DONOR}; run 01-fetch-sources.sh"

mapfile -t FONTS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.ttf' | sort)
[[ ${#FONTS[@]} -gt 0 ]] || die "no fonts in ${OUT_DIR}; run 02-add-ligatures.sh first"

log "narrow ambiguous punctuation (donor: ${FUSION_TTF_HALFWIDTH_DONOR})"
"${PY}" "${PIXEL_ROOT}/scripts/narrow_ambiguous.py" --donor "${DONOR}" "${FONTS[@]}"

log "done narrow"
