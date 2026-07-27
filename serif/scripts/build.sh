#!/usr/bin/env bash
# One-shot: clone pinned Sarasa → quilt push → prepare CJK → build TTF.
# Optional: NERD=1 ./scripts/build.sh  → also run Nerd patch + re-verify.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/01-clone-sarasa.sh"
"${SCRIPT_DIR}/02-apply-quilt.sh"
"${SCRIPT_DIR}/03-prepare-cjk.sh"
"${SCRIPT_DIR}/04-build.sh"

if [[ "${NERD:-0}" == "1" || "${NERD:-}" == "true" ]]; then
  "${SCRIPT_DIR}/05-nerd-patch.sh"
fi

echo
echo "Done. Fonts in: ${SCRIPT_DIR}/../out/"
[[ "${NERD:-0}" == "1" || "${NERD:-}" == "true" ]] && echo "Nerd fonts in: ${SCRIPT_DIR}/../out/nerd/"
