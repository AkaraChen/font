#!/usr/bin/env bash
# Turn Monaspace's ligature sets on by default.
#
# Radon parks essentially every coding ligature behind stylistic sets — `liga`
# alone only carries a couple, and default `calt` does texture healing — so a
# stock Radon feels like ligatures are off in editors that flip nothing but
# `calt`. This unions ss01–ss10's lookups into calt (same move serif/ makes for
# Iosevka's dlig); the ss** features stay intact for anyone toggling them.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

PY="$(python_bin)"
shopt -s nullglob
stem="${PRODUCT_STEM:-RadonWenKaiNFM}"
fonts=("${OUT_DIR}/${stem}"-*.ttf)
[[ ${#fonts[@]} -gt 0 ]] || die "no products in ${OUT_DIR}; run 04-merge.sh first"

log "folding ${LIGATURE_SETS} into default calt"
"${PY}" "${REPO_ROOT}/serif/scripts/expand-default-ligatures.py" \
  --include "${LIGATURE_SETS}" "${fonts[@]}"
