#!/usr/bin/env bash
# Measure Iosevka N Slab (Latin) vs Neo ZhiSong (CJK) stem widths and recommend
# calibration.*.embolden values for font.toml. Does not write it.
#
# Metric: scanline vertical-stem median (shared lib/fontkit/measure.py). Song
# horizontals stay thinner than the Latin by design and are reported, not
# targeted — matching verticals is what removes the "CJK reads heavier than the
# Latin" look in mixed coding text.
#
# Reads the real build steps instead of re-downloading upstream releases into
# work/downloads/, which is what this script did while serif had a shell
# pipeline. The Latin target now comes out of the merged product — its Latin
# *is* Iosevka N Slab, already at the product grid — so there is no second copy
# of it to drift, and no venv to provision.
#
#   ./scripts/calibrate-stroke.sh
#
# `step merged-*` builds the family: the Latin only exists inside Sarasa's
# output. Cold that is the whole upstream build; warm it is a store lookup.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/tools/diagnostic.sh"

CAL="${REPO_ROOT}/tools/calibrate-cjk-weight.py"
STEM="SarasaMonoSlabNeoZhiSongSC-Opt"

log "realising the merged product (Latin target) and the raw CJK master"
LAT_R="$(step merged-Regular)/${STEM}-Regular.ttf"
LAT_B="$(step merged-Bold)/${STEM}-Bold.ttf"
CJK="$(step src-cjk-Regular)/${LXGW_ASSET}"

# Both weights are emboldened from the same Regular master — Neo ZhiSong ships
# no Bold — so the two sweeps differ only in their Latin target and range.
STRENGTHS_REG="${STRENGTHS_REG:-0,4,6,7,7.5,8,9,10,12,14}"
STRENGTHS_BOLD="${STRENGTHS_BOLD:-16,20,22,24,26,28,32}"

log "survey: product Latin vs raw Neo ZhiSong"
python3 "${CAL}" --survey \
  --latin "${LAT_R}" --latin "${LAT_B}" \
  --cjk "${CJK}" \
  --upm "${UPM}"

log "sweep Regular (target = product Latin Regular)"
python3 "${CAL}" \
  --latin "${LAT_R}" \
  --cjk "${CJK}" \
  --upm "${UPM}" \
  --strengths "${STRENGTHS_REG}"

log "sweep Bold (target = product Latin Bold, same Regular CJK master)"
python3 "${CAL}" \
  --latin "${LAT_B}" \
  --cjk "${CJK}" \
  --upm "${UPM}" \
  --strengths "${STRENGTHS_BOLD}"

log "done. Compare recommendations with font.toml ([calibration.regular] / [calibration.bold])."
