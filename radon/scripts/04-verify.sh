#!/usr/bin/env bash
# Gate: EN cell / CJK cell are strict 2:1 at the pinned advances.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

PY="$(python_bin)"
shopt -s nullglob
stem="${PRODUCT_STEM:-RadonWenKaiDual}"
fonts=("${OUT_DIR}/${stem}"-*.ttf)
[[ ${#fonts[@]} -gt 0 ]] || die "no products in ${OUT_DIR}; run 03-merge.sh first"

log "verify 2:1 (expect half=${EN_ADV})"
"${PY}" "${RADON_ROOT}/scripts/verify-2to1.py" --expect-half "${EN_ADV}" "${fonts[@]}"

# Ligature feature smoke: calt or dlig or liga must exist
log "check coding-ligature features present"
OUT_DIR="${OUT_DIR}" PRODUCT_STEM="${PRODUCT_STEM:-RadonWenKaiDual}" "${PY}" - <<'PY'
from pathlib import Path
import os, sys
from fontTools.ttLib import TTFont
out = Path(os.environ["OUT_DIR"])
stem = os.environ.get("PRODUCT_STEM", "RadonWenKaiDual")
need = {"calt", "dlig", "liga", "rlig"}
for f in sorted(out.glob(f"{stem}-*.ttf")):
    font = TTFont(f)
    feats = set()
    if "GSUB" in font:
        feats = {fr.FeatureTag for fr in font["GSUB"].table.FeatureList.FeatureRecord}
    font.close()
    hit = sorted(feats & need)
    print(f"  {f.name}: lig-ish features {hit}")
    if not hit:
        print(f"error: {f.name} missing calt/dlig/liga/rlig", file=sys.stderr)
        sys.exit(1)
print("  OK ligature features")
PY
