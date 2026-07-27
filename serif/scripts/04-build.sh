#!/usr/bin/env bash
# npm install + build unhinted MonoSlab NeoZhiSong Opt TTFs.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

need_cmd npm
need_cmd node
[[ -d "${SARASA_DIR}" ]] || die "missing ${SARASA_DIR}"
[[ -f "${SARASA_DIR}/sources/shs/LXGWNeoZhiSongSC-Regular.ttf" ]] || die "missing CJK Regular; run 03-prepare-cjk.sh"
[[ -f "${SARASA_DIR}/sources/shs/LXGWNeoZhiSongSC-Bold.ttf" ]] || die "missing CJK Bold; run 03-prepare-cjk.sh"

if ! command -v ttfautohint >/dev/null 2>&1; then
  log "warning: ttfautohint not on PATH (Sarasa latin prep may fail)"
fi

cd "${SARASA_DIR}"
if [[ ! -d node_modules ]]; then
  log "npm install"
  npm install
else
  log "node_modules present; skip npm install"
fi

log "npm run build ${BUILD_TARGET}"
npm run build "${BUILD_TARGET}"

ensure_dirs
cp -f out/TTF-Unhinted/SarasaMonoSlabSC-Regular.ttf \
  "${OUT_DIR}/SarasaMonoSlabNeoZhiSongSC-Opt-Regular.ttf"
cp -f out/TTF-Unhinted/SarasaMonoSlabSC-Bold.ttf \
  "${OUT_DIR}/SarasaMonoSlabNeoZhiSongSC-Opt-Bold.ttf"

log "products:"
ls -lh "${OUT_DIR}"/*.ttf

# Strict 2:1 gate (ASCII / CJK / fullwidth / box drawing)
VERIFY="${SERIF_ROOT}/scripts/verify-2to1.py"
if [[ -f "${VERIFY}" ]]; then
  PY=""
  if [[ -x "${VENV_DIR}/bin/python" ]]; then
    PY="${VENV_DIR}/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
  fi
  if [[ -n "${PY}" ]]; then
    log "strict 2:1 verification"
    mapfile -t PRODUCTS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.ttf' | sort)
    "${PY}" "${VERIFY}" "${PRODUCTS[@]}"
  else
    log "warning: no python for verify-2to1.py"
  fi
fi
