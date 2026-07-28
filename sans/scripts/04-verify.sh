#!/usr/bin/env bash
# Gate: EN/CJK 2:1 + mono flags + EAW + Lilex features + Nerd PUA half-cell.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

PY="$(python_bin)"
NERD_OUT="${OUT_DIR}/nerd"

mapfile -t NERD_FONTS < <(find "${NERD_OUT}" -maxdepth 1 -type f \( -name '*.ttf' -o -name '*.otf' \) 2>/dev/null | sort)
if [[ ${#NERD_FONTS[@]} -gt 0 ]]; then
  FONTS=("${NERD_FONTS[@]}")
  EXTRA_GATES=(--check-nerd --check-eaw)
  log "verify Nerd products (${#FONTS[@]}) with nerd + EAW gates"
else
  # intermediate Dual only
  shopt -s nullglob
  stem_base="${BASE_FAMILY_PS:-LilexSansSCDual}"
  FONTS=("${OUT_DIR}/${stem_base}"-*.ttf)
  EXTRA_GATES=(--check-eaw)
  [[ ${#FONTS[@]} -gt 0 ]] || die "no products in ${OUT_DIR}; run 02-merge.sh first"
  log "verify intermediate Dual products (${#FONTS[@]}) with EAW gate"
fi

log "verify 2:1 (expect half=${EN_ADV})"
"${PY}" "${SANS_ROOT}/scripts/verify-2to1.py" \
  --expect-half "${EN_ADV}" \
  "${EXTRA_GATES[@]}" \
  "${FONTS[@]}"

log "verify Lilex coding features (calt / ligatures)"
"${PY}" "${SANS_ROOT}/scripts/verify-features.py" "${FONTS[@]}"

# Stem report (informational — not a hard gate). Confirms Latin/CJK optical weight
# after embolden; same measure path as calibrate-stroke.sh (stem_max_ratio=0.40).
if [[ -f "${SERIF_TOOLS}/measure_stroke_width.py" ]]; then
  log "stroke match report (Latin vs CJK sample stems; informational)"
  export SERIF_TOOLS
  for font in "${FONTS[@]}"; do
    log "  $(basename "${font}")"
    SERIF_TOOLS="${SERIF_TOOLS}" "${PY}" - "${font}" <<'PY' || true
import os
import statistics
import sys

from fontTools.ttLib import TTFont

sys.path.insert(0, os.environ["SERIF_TOOLS"])
from measure_stroke_width import (  # noqa: E402
    DEFAULT_CJK,
    DEFAULT_LATIN,
    codepoint_name,
    glyph_to_path,
    measure_stems,
    path_to_polylines,
)

def v_med(font, chars):
    gs = font.getGlyphSet()
    vs = []
    for ch in chars:
        name = codepoint_name(font, ch)
        if not name:
            continue
        try:
            path = glyph_to_path(gs, name)
            if not list(path.contours):
                continue
            m = measure_stems(path_to_polylines(path), stem_max_ratio=0.40)
            if m["v_median"] is not None:
                vs.append(m["v_median"])
        except Exception:
            continue
    return statistics.median(vs) if vs else float("nan")

font = TTFont(sys.argv[1])
lv = v_med(font, DEFAULT_LATIN)
cv = v_med(font, DEFAULT_CJK)
print(f"    Latin v_median={lv:.2f}  CJK v_median={cv:.2f}  Δ={cv - lv:+.2f}")
font.close()
PY
  done
else
  log "skip stroke report (serif tools not present)"
fi

log "verify ok"
