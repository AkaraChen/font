#!/usr/bin/env bash
# Gate: EN cell / CJK cell are strict 2:1 at the pinned advances.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

PY="$(python_bin)"
shopt -s nullglob
fonts=("${OUT_DIR}"/KitPlexDual-*.ttf)
[[ ${#fonts[@]} -gt 0 ]] || die "no products in ${OUT_DIR}; run 02-merge.sh first"

log "verify 2:1 (expect half=${EN_ADV})"
"${PY}" "${SANS_ROOT}/scripts/verify-2to1.py" --expect-half "${EN_ADV}" "${fonts[@]}"
