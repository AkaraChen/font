#!/usr/bin/env bash
# Gates: strict 2:1 dual-width.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

PY="$(python_bin)"
shopt -s nullglob
stem="${PRODUCT_STEM:-RecursiveYozaiDual}"
fonts=("${OUT_DIR}/${stem}"-*.ttf)
[[ ${#fonts[@]} -gt 0 ]] || die "no products in ${OUT_DIR}; run 04-merge.sh first"

log "verify 2:1 metrics"
if [[ -f "${REPO_ROOT}/serif/scripts/verify-2to1.py" ]]; then
  "${PY}" "${REPO_ROOT}/serif/scripts/verify-2to1.py" "${fonts[@]}"
elif [[ -f "${REPO_ROOT}/rounded/scripts/verify-2to1.py" ]]; then
  "${PY}" "${REPO_ROOT}/rounded/scripts/verify-2to1.py" --expect-half "${EN_ADV}" "${fonts[@]}"
else
  die "no verify-2to1.py found under serif/ or rounded/"
fi

log "spot-check advances + stroke notes"
for font in "${fonts[@]}"; do
  "${PY}" - <<PY
from fontTools.ttLib import TTFont
f = TTFont("${font}")
cm = f.getBestCmap(); h = f["hmtx"]
sample = {ch: h[cm[ord(ch)]][0] for ch in "Aa0中文，" if ord(ch) in cm}
print("  ${font##*/}:", sample)
assert sample.get("A") == ${EN_ADV}, sample
assert sample.get("中") == ${CJK_ADV}, sample
assert 2 * sample["A"] == sample["中"]
f.close()
print("  OK 2:1")
PY
done

log "all gates passed"
