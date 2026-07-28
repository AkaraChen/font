#!/usr/bin/env bash
# npm install + build unhinted MonoSlab NeoZhiSong Opt TTFs.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

need_cmd npm
need_cmd node
# Sarasa's verdafile.mjs shells out to otc2otf (L200) and otf2ttf (L220/235)
# during source prep, and its own check-env.mjs only console.error()s when they
# are absent. Both come from AFDKO, which was never in this repo's need_cmd list
# — serif only ever built because the maintainer's machine happened to have it.
need_cmd otc2otf
need_cmd otf2ttf
# Only the hinted targets consume ttfautohint and we build ttf-unhinted, but a
# missing binary used to be a warning that let the build "succeed" with wrong
# products. Declare it.
need_cmd ttfautohint
[[ -d "${SARASA_DIR}" ]] || die "missing ${SARASA_DIR}"
[[ -f "${SARASA_DIR}/sources/shs/LXGWNeoZhiSongSC-Regular.ttf" ]] || die "missing CJK Regular; run 03-prepare-cjk.sh"
[[ -f "${SARASA_DIR}/sources/shs/LXGWNeoZhiSongSC-Bold.ttf" ]] || die "missing CJK Bold; run 03-prepare-cjk.sh"

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

log "intermediate (pre-Nerd) products:"
ls -lh "${OUT_DIR}"/*.ttf
log "next: 05-nerd-patch.sh (product is out/nerd/; 2:1 gate runs there)"
