#!/usr/bin/env bash
# Radon NF (CFF, 1240/2000 cell) → TrueType on the half cell (500/1000).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

for weight in Regular Bold; do
  src="${EXTRACT_DIR}/MonaspaceRadonNF-${weight}.otf"
  [[ -f "${src}" ]] || die "missing ${src}; run 01-fetch-sources.sh first"
  log "preparing Latin ${weight}"
  "${PY}" "${KAI_ROOT}/scripts/prepare_latin.py" \
    "${src}" "${STAGE_DIR}/RadonLatin-${weight}.ttf" \
    --src-upm "${SRC_UPM}" \
    --upm "${UPM}" \
    --src-adv "${LATIN_SRC_ADV}" \
    --narrow-adv "${LATIN_NARROW_ADV}" \
    --uniform-scale "${LATIN_UNIFORM_SCALE}" \
    --en-adv "${EN_ADV}"
done

ls -lh "${STAGE_DIR}"/RadonLatin-*.ttf
