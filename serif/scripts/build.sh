#!/usr/bin/env bash
# One-shot: clone pinned Sarasa → quilt push → prepare CJK → build TTF.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/01-clone-sarasa.sh"
"${SCRIPT_DIR}/02-apply-quilt.sh"
"${SCRIPT_DIR}/03-prepare-cjk.sh"
"${SCRIPT_DIR}/04-build.sh"

echo
echo "Done. Fonts in: ${SCRIPT_DIR}/../out/"
