#!/usr/bin/env bash
# One-shot product build: Sarasa MonoSlab × Neo ZhiSong Opt → Nerd Font Mono.
# Final products: out/nerd/SarasaNZSSlabNFM-{Regular,Bold}.ttf
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/01-clone-sarasa.sh"
"${SCRIPT_DIR}/02-apply-quilt.sh"
"${SCRIPT_DIR}/03-prepare-cjk.sh"
"${SCRIPT_DIR}/04-build.sh"      # intermediate unhinted TTFs under out/
"${SCRIPT_DIR}/05-nerd-patch.sh" # Nerd patch + 2:1 --check-nerd → out/nerd/
"${SCRIPT_DIR}/06-narrow-symbols.sh" # EAW-correct symbol widths + final gate

echo
echo "Done. Nerd Fonts in: ${SCRIPT_DIR}/../out/nerd/"
ls -lh "${SCRIPT_DIR}/../out/nerd/"/*.{ttf,otf} 2>/dev/null || true
