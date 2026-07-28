#!/usr/bin/env bash
# One-shot: fetch → prepare CJK → merge Dual → Nerd Font Mono → verify.
# Product: out/nerd/TypewriterMonoNFM-{Regular,Bold}.ttf
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/01-fetch-sources.sh"
"${SCRIPT_DIR}/02-prepare-cjk.sh"
"${SCRIPT_DIR}/03-merge.sh"
"${SCRIPT_DIR}/04-nerd-patch.sh"
"${SCRIPT_DIR}/05-verify.sh"

echo
echo "Done. Product in: ${SCRIPT_DIR}/../out/nerd/"
ls -lh "${SCRIPT_DIR}/../out/nerd/"/*.{ttf,otf} 2>/dev/null || true
