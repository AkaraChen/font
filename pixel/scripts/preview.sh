#!/usr/bin/env bash
# Render preview sheets with a REAL shaper + rasterizer (HarfBuzz + FreeType).
#
# Do not hand-roll a previewer for this font. A naive "fill each contour with
# squares" previewer cannot handle Fusion's multi-contour glyphs with counters
# ('t', 'f', 'e', quotes) and paints them as solid blocks — which once led to a
# whole review round chasing a font bug that did not exist.
#
# Requires: harfbuzz (hb-view). Optional: imagemagick (stacks the sheet).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

need_cmd hb-view
export LC_ALL="${LC_ALL:-en_US.UTF-8}"

FONT="${1:-}"
if [[ -z "${FONT}" ]]; then
  FONT="${OUT_DIR}/nerd/${PRODUCT_STEM}-Regular.ttf"
  [[ -f "${FONT}" ]] || FONT="${OUT_DIR}/${BASE_FAMILY_PS}-Regular.ttf"
fi
[[ -f "${FONT}" ]] || die "no font to preview (pass a path, or run 02-add-ligatures.sh)"

PREVIEW_DIR="${OUT_DIR}/preview"
rm -rf "${PREVIEW_DIR}"
mkdir -p "${PREVIEW_DIR}"

# 12px design size; 96 = 8x nearest-neighbour-ish zoom for inspection
SIZE="${PREVIEW_SIZE:-96}"

render() { # render <name> <feature-args> <text>
  local name="$1" feat="$2" text="$3"
  hb-view --font-size="${SIZE}" --margin=12 --features="${feat}" \
    --output-file="${PREVIEW_DIR}/${name}.png" "${FONT}" "${text}"
}

log "preview ${FONT} → ${PREVIEW_DIR}"

render 01-compare-2cell   +calt '== != <= >= => -> <- <> |> <| ++ -- //'
render 02-compare-3cell   +calt '=== !== <=> <-> --> <-- ==> <== ... ///'
render 03-comments        +calt '/* */ /** **/ <!-- :: := ::='
render 04-off-2cell       -calt '== != <= >= => -> <- <> |> <| ++ -- //'
render 05-off-3cell       -calt '=== !== <=> <-> --> <-- ==> <== ... ///'

# Real code lines, ligatures live
n=0
while IFS= read -r line; do
  [[ -n "${line}" ]] || continue
  n=$((n + 1))
  render "$(printf '10-code-%02d' "${n}")" +calt "${line}"
done < "${PIXEL_ROOT}/samples/coding-mixed.txt"

if command -v magick >/dev/null 2>&1; then
  log "stacking contact sheet"
  # shellcheck disable=SC2046
  magick $(ls "${PREVIEW_DIR}"/*.png | sort) \
    -background white -gravity west -append \
    "${PREVIEW_DIR}/sheet.png"
fi

log "preview files:"
ls -1 "${PREVIEW_DIR}"
