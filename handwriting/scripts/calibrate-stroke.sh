#!/usr/bin/env bash
# Measure Radon vs WenKai stems and print the pins they imply.
# Run after 01-fetch-sources.sh + 02-prepare-latin.sh; needs the Light weight
# too, which the product build does not download.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

LIGHT="${EXTRACT_DIR}/LXGWWenKai-Light.ttf"
if [[ ! -f "${LIGHT}" ]]; then
  log "fetching LXGWWenKai-Light.ttf (survey only, not pinned into the product)"
  curl -fL --retry 3 -o "${LIGHT}" \
    "${WENKAI_REPO}/releases/download/${WENKAI_RELEASE_TAG}/LXGWWenKai-Light.ttf"
fi

for f in "${STAGE_DIR}/RadonLatin-Regular.ttf" "${STAGE_DIR}/RadonLatin-Bold.ttf"; do
  [[ -f "${f}" ]] || die "missing ${f}; run 02-prepare-latin.sh first"
done

log "slant: what angle does Radon actually lean at?"
"${PY}" "${HANDWRITING_ROOT}/scripts/measure-slant.py" "${EXTRACT_DIR}/MonaspaceRadonNF-Regular.otf"

log "weight survey: which WenKai weight matches which Radon weight?"
"${PY}" "${HANDWRITING_ROOT}/scripts/calibrate_cjk_weight.py" --survey \
  --latin "${STAGE_DIR}/RadonLatin-Regular.ttf" \
  --latin "${STAGE_DIR}/RadonLatin-Bold.ttf" \
  --cjk "${LIGHT}" \
  --cjk "${EXTRACT_DIR}/LXGWWenKai-Regular.ttf" \
  --cjk "${EXTRACT_DIR}/LXGWWenKai-Medium.ttf"

log "embolden sweep for the Bold face (WenKai ${WENKAI_FOR_BOLD} → Radon Bold)"
"${PY}" "${HANDWRITING_ROOT}/scripts/calibrate_cjk_weight.py" \
  --latin "${STAGE_DIR}/RadonLatin-Bold.ttf" \
  --cjk "${EXTRACT_DIR}/LXGWWenKai-${WENKAI_FOR_BOLD}.ttf" \
  --strengths 10,12,14,15,16,18

cat >&2 <<'EOF'

Read the tables above into pins.env:
  WENKAI_FOR_REGULAR / WENKAI_FOR_BOLD  ← the weight whose Δv is smallest
  CJK_EMBOLDEN_REGULAR / CJK_EMBOLDEN_BOLD ← the sweep's BEST strength (0 if the
    design weight already lands within a few units — a real weight beats a
    stroked one, since embolden rounds Kai's brush entries and exits)
  CJK_SLANT_DEG ← the stem median from the slant block
EOF
