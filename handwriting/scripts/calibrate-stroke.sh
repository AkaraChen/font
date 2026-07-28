#!/usr/bin/env bash
# Measure Radon vs WenKai stems and print the pins they imply.
#
# The Light weight is downloaded here rather than pinned: it is a survey input
# that never reaches a product, so putting it in pins.env would add a hash the
# build must keep valid for a font it never opens.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/tools/diagnostic.sh"

CAL="${REPO_ROOT}/tools/calibrate-cjk-weight.py"

log "realising prepared Latin + WenKai masters"
LAT_R="$(step latin-prepared-Regular)/RadonLatin-Regular.ttf"
LAT_B="$(step latin-prepared-Bold)/RadonLatin-Bold.ttf"
RADON_RAW="$(step src-latin-Regular)/MonaspaceRadonNF-Regular.otf"
WENKAI_MED="$(step src-cjk-Bold)/LXGWWenKai-${WENKAI_FOR_BOLD}.ttf"

SURVEY_DIR="${FAMILY_ROOT}/work/survey"
mkdir -p "${SURVEY_DIR}"
LIGHT="${SURVEY_DIR}/LXGWWenKai-Light.ttf"
REGULAR="${SURVEY_DIR}/LXGWWenKai-Regular.ttf"
for weight in Light Regular; do
  dest="${SURVEY_DIR}/LXGWWenKai-${weight}.ttf"
  [[ -f "${dest}" ]] || {
    log "fetching LXGWWenKai-${weight}.ttf (survey only, not pinned into the product)"
    curl -fL --retry 3 -o "${dest}" \
      "${WENKAI_REPO}/releases/download/${WENKAI_RELEASE_TAG}/LXGWWenKai-${weight}.ttf"
  }
done

log "slant: what angle does Radon actually lean at?"
python3 "${REPO_ROOT}/tools/measure-slant.py" "${RADON_RAW}"

log "weight survey: which WenKai weight matches which Radon weight?"
python3 "${CAL}" --survey \
  --latin "${LAT_R}" \
  --latin "${LAT_B}" \
  --cjk "${LIGHT}" \
  --cjk "${REGULAR}" \
  --cjk "${WENKAI_MED}"

log "embolden sweep for the Bold face (WenKai ${WENKAI_FOR_BOLD} → Radon Bold)"
python3 "${CAL}" \
  --latin "${LAT_B}" \
  --cjk "${WENKAI_MED}" \
  --strengths 10,12,14,15,16,18

cat >&2 <<'EOF'

Read the tables above into pins.env:
  WENKAI_FOR_REGULAR / WENKAI_FOR_BOLD  ← the weight whose Δv is smallest
  CJK_EMBOLDEN_REGULAR / CJK_EMBOLDEN_BOLD ← the sweep's BEST strength (0 if the
    design weight already lands within a few units — a real weight beats a
    stroked one, since embolden rounds Kai's brush entries and exits)
  CJK_SLANT_DEG ← the stem median from the slant block
EOF
