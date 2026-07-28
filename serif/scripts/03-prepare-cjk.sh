#!/usr/bin/env bash
# Download LXGW Neo ZhiSong Plus, scale to UPM 1000, embolden Regular/Bold, install as SHS drop-ins.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

need_cmd curl
need_cmd python3
[[ -d "${SARASA_DIR}" ]] || die "missing ${SARASA_DIR}; run 01-clone-sarasa.sh + 02-apply-quilt.sh first"
ensure_dirs

SRC_TTF="${DOWNLOADS_DIR}/${LXGW_ASSET}"
if [[ ! -f "${SRC_TTF}" ]]; then
  log "downloading ${LXGW_URL}"
  curl -fL --retry 3 -o "${SRC_TTF}.partial" "${LXGW_URL}"
  mv "${SRC_TTF}.partial" "${SRC_TTF}"
else
  log "using cached ${SRC_TTF}"
fi

# Python venv: fonttools + skia-pathops.
# A pre-provisioned interpreter (the Nix devShell sets FONTKIT_PYTHON) replaces
# the venv entirely: no pip, no network, no version drift.
if [[ -n "${FONTKIT_PYTHON:-}" ]]; then
  "${FONTKIT_PYTHON}" -c "import fontTools, pathops" \
    || die "FONTKIT_PYTHON=${FONTKIT_PYTHON} cannot import: fontTools, pathops"
  PY="${FONTKIT_PYTHON}"
else
  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    log "creating venv ${VENV_DIR}"
    if command -v uv >/dev/null 2>&1; then
      uv venv "${VENV_DIR}"
      uv pip install --python "${VENV_DIR}/bin/python" fonttools skia-pathops
    else
      python3 -m venv "${VENV_DIR}"
      "${VENV_DIR}/bin/pip" install -U pip
      "${VENV_DIR}/bin/pip" install fonttools skia-pathops
    fi
  fi
  PY="${VENV_DIR}/bin/python"
fi

BASE_SCALED="${DOWNLOADS_DIR}/LXGWNeoZhiSongSC-Regular-base.ttf"
REG_OUT="${SARASA_DIR}/sources/shs/LXGWNeoZhiSongSC-Regular.ttf"
BOLD_OUT="${SARASA_DIR}/sources/shs/LXGWNeoZhiSongSC-Bold.ttf"
mkdir -p "${SARASA_DIR}/sources/shs"

log "scale UPM → ${CJK_TARGET_UPM}"
SRC_TTF="${SRC_TTF}" BASE_SCALED="${BASE_SCALED}" CJK_TARGET_UPM="${CJK_TARGET_UPM}" \
"${PY}" - <<'PY'
import os
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
from pathlib import Path

src = Path(os.environ["SRC_TTF"])
dst = Path(os.environ["BASE_SCALED"])
target = int(os.environ["CJK_TARGET_UPM"])
font = TTFont(src)
if font["head"].unitsPerEm != target:
    scale_upem(font, target)
font.save(dst)
print(f"saved {dst} UPM={TTFont(dst)['head'].unitsPerEm}")
PY

log "embolden Regular s=${CJK_EMBOLDEN_REGULAR}"
"${PY}" -m fontkit.embolden \
  "${BASE_SCALED}" "${REG_OUT}" \
  --strength "${CJK_EMBOLDEN_REGULAR}"

log "embolden Bold s=${CJK_EMBOLDEN_BOLD}"
"${PY}" -m fontkit.embolden \
  "${BASE_SCALED}" "${BOLD_OUT}" \
  --strength "${CJK_EMBOLDEN_BOLD}"

log "CJK sources ready:"
ls -lh "${REG_OUT}" "${BOLD_OUT}"
