#!/usr/bin/env bash
# Prepare WenKai Medium: embolden (Regular/Bold strengths) + mild oblique.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_dirs
PY="$(python_bin)"

SRC="${EXTRACT_DIR}/LXGWWenKai-Medium.ttf"
[[ -f "${SRC}" ]] || die "missing ${SRC}; run 01-fetch-sources.sh first"

EMBOLDEN="${RADON_ROOT}/tools/embolden_cjk.py"
OBLIQUE="${RADON_ROOT}/scripts/oblique_cjk.py"
[[ -f "${EMBOLDEN}" ]] || die "missing ${EMBOLDEN}"
[[ -f "${OBLIQUE}" ]] || die "missing ${OBLIQUE}"

REG_EMB="${PREP_DIR}/WenKai-Regular-embolden.ttf"
BLD_EMB="${PREP_DIR}/WenKai-Bold-embolden.ttf"
REG_OUT="${PREP_DIR}/WenKai-Regular-prepared.ttf"
BLD_OUT="${PREP_DIR}/WenKai-Bold-prepared.ttf"

log "embolden CJK Regular strength=${CJK_EMBOLDEN_REGULAR}"
"${PY}" "${EMBOLDEN}" "${SRC}" "${REG_EMB}" --strength "${CJK_EMBOLDEN_REGULAR}"

log "embolden CJK Bold strength=${CJK_EMBOLDEN_BOLD}"
"${PY}" "${EMBOLDEN}" "${SRC}" "${BLD_EMB}" --strength "${CJK_EMBOLDEN_BOLD}"

ANGLE="${CJK_OBLIQUE_DEG}"
# pins store positive "slight lean" magnitude as degrees of right lean via
# post.italicAngle convention (negative). Accept either sign in pins.
if awk "BEGIN {exit !(${ANGLE} > 0)}"; then
  ANGLE_POST="-${ANGLE}"
else
  ANGLE_POST="${ANGLE}"
fi

log "oblique CJK angle=${ANGLE_POST}° (post.italicAngle)"
"${PY}" "${OBLIQUE}" "${REG_EMB}" "${REG_OUT}" --angle "${ANGLE_POST}"
"${PY}" "${OBLIQUE}" "${BLD_EMB}" "${BLD_OUT}" --angle "${ANGLE_POST}"

log "prepared CJK:"
ls -lh "${REG_OUT}" "${BLD_OUT}"
