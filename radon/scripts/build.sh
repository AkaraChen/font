#!/usr/bin/env bash
# One-shot: fetch → prepare CJK → merge → verify → Nerd patch.
# Product:
#   out/RadonWenKaiDual-{Regular,Bold}.ttf
#   out/nerd/RadonWenKaiNFM-{Regular,Bold}.ttf
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/01-fetch-sources.sh"
"${SCRIPT_DIR}/02-prepare-cjk.sh"
"${SCRIPT_DIR}/03-merge.sh"
"${SCRIPT_DIR}/04-verify.sh"

# Nerd patch is best-effort when neither docker nor fontforge is available.
if command -v docker >/dev/null 2>&1 || command -v fontforge >/dev/null 2>&1; then
  "${SCRIPT_DIR}/05-nerd-patch.sh"
else
  echo "==> skip Nerd patch (no docker/fontforge); base Dual fonts still valid" >&2
fi

echo
echo "Done. Products in: ${SCRIPT_DIR}/../out/"
ls -lh "${SCRIPT_DIR}/../out/"/*.ttf 2>/dev/null || true
ls -lh "${SCRIPT_DIR}/../out/nerd/"/*.ttf 2>/dev/null || true
