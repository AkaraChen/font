#!/usr/bin/env bash
# One-shot: fetch → prepare Latin → prepare CJK → merge → verify.
# Product: out/RadonWenKaiNFM-{Regular,Bold}.ttf
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/01-fetch-sources.sh"
"${SCRIPT_DIR}/02-prepare-latin.sh"
"${SCRIPT_DIR}/03-prepare-cjk.sh"
"${SCRIPT_DIR}/04-merge.sh"
"${SCRIPT_DIR}/05-expand-ligatures.sh"
"${SCRIPT_DIR}/06-verify.sh"

echo
echo "Done. Products in: ${SCRIPT_DIR}/../out/"
ls -lh "${SCRIPT_DIR}/../out/"/*.ttf 2>/dev/null || true
