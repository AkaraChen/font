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

if [[ -x "${VENV_DIR}/bin/python" ]]; then
  OUT_DIR="${OUT_DIR}" "${VENV_DIR}/bin/python" - <<'PY'
from fontTools.ttLib import TTFont
from pathlib import Path
import os
for p in sorted(Path(os.environ["OUT_DIR"]).glob("*.ttf")):
    f = TTFont(p)
    cmap = f.getBestCmap()
    h = f["hmtx"]
    def w(ch):
        g = cmap.get(ord(ch))
        return h[g][0] if g else None
    a, z = w("A"), w("中")
    print(f"{p.name}: A={a} 中={z} ratio={z/a if a else None}")
    f.close()
PY
fi
