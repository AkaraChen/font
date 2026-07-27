#!/usr/bin/env bash
# One-shot: Fusion 12px mono + hand-drawn ligatures + Nerd Font Mono product.
# Final: out/nerd/FusionPixel12NFM-Regular.ttf
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/01-fetch-sources.sh"
"${SCRIPT_DIR}/02-add-ligatures.sh"
"${SCRIPT_DIR}/03-nerd-patch.sh"
"${SCRIPT_DIR}/04-verify.sh"

echo
echo "Done. Product in: ${SCRIPT_DIR}/../out/nerd/"
ls -lh "${SCRIPT_DIR}/../out/nerd/"/*.{ttf,otf} 2>/dev/null || true
