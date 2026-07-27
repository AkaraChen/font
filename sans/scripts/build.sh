#!/usr/bin/env bash
# One-shot: fetch pinned Lilex + Plex Sans SC → merge → verify 2:1 + features.
# Product: out/LilexSansSCDual-{Regular,Bold}.ttf
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/01-fetch-sources.sh"
"${SCRIPT_DIR}/02-merge.sh"
"${SCRIPT_DIR}/03-verify.sh"

echo
echo "Done. Products in: ${SCRIPT_DIR}/../out/"
ls -lh "${SCRIPT_DIR}/../out/"/*.ttf 2>/dev/null || true
