#!/usr/bin/env bash
# Survey / sweep CJK embolden strength against prepared Latin stems.
#
# Reads the real build steps rather than a `work/` directory that may or may not
# hold what the current pins say — `step` realises them if they are cold.
#   ./scripts/calibrate-stroke.sh
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/tools/diagnostic.sh"

CAL="${REPO_ROOT}/tools/calibrate-cjk-weight.py"

log "realising prepared Latin + raw Yozai"
LAT_R="$(step latin-prepared-Regular)/RecursiveLatin-Regular.ttf"
LAT_B="$(step latin-prepared-Bold)/RecursiveLatin-Bold.ttf"
YOZAI_R="$(step src-cjk-Regular)/Yozai-${YOZAI_FOR_REGULAR}.ttf"
YOZAI_B="$(step src-cjk-Bold)/Yozai-${YOZAI_FOR_BOLD}.ttf"

log "survey: prepared Latin vs raw Yozai"
python3 "${CAL}" --survey \
  --latin "${LAT_R}" --latin "${LAT_B}" \
  --cjk "${YOZAI_R}" \
  --cjk "${YOZAI_B}"

log "sweep Regular pair (Yozai ${YOZAI_FOR_REGULAR} → target Latin Regular)"
python3 "${CAL}" \
  --latin "${LAT_R}" \
  --cjk "${YOZAI_R}" \
  --strengths 0,2,4,6,8,10,12,14,16,18,20

log "sweep Bold pair (Yozai ${YOZAI_FOR_BOLD} → target Latin Bold)"
python3 "${CAL}" \
  --latin "${LAT_B}" \
  --cjk "${YOZAI_B}" \
  --strengths 0,4,8,12,16,20,24,28
