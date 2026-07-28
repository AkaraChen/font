#!/usr/bin/env bash
# Preamble for the measuring tools under <family>/scripts/.
#
# This is NOT the build. The build is derivations (nix/families/), and nothing
# in it sources a shell library any more. What is left under <family>/scripts/
# is the handful of things a maintainer runs by hand when re-deriving a pin:
# stroke calibration, slant measurement, preview sheets. They need three things
# the build no longer hands anyone — the family's pins, a way to name a build
# step's store path, and log/die.
#
# Compare against the seven `common.sh` files this replaces. Gone with them:
# venv creation, `pip install`, the uv-or-venv fork, `download_file`, the
# sha256 gate that re-implemented what a fixed-output derivation is, and
# `NERD_PATCH_METHOD=auto`. None of those were diagnostics; they were a build
# system written in bash.
#
# Usage, from <family>/scripts/<tool>.sh:
#
#   source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/tools/diagnostic.sh"
#   latin="$(step latin-prepared-Regular)/RadonLatin-Regular.ttf"

set -euo pipefail

# BASH_SOURCE[1] is the script that sourced this, so the family is wherever
# *it* lives — this file has no idea and must not guess.
FAMILY_ROOT="$(cd "$(dirname "${BASH_SOURCE[1]}")/.." && pwd)"
FAMILY="$(basename "${FAMILY_ROOT}")"
REPO_ROOT="$(cd "${FAMILY_ROOT}/.." && pwd)"

log() { printf '==> %s\n' "$*" >&2; }
die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || die "no python3 — run this inside \`nix develop\`"
# The working copy is intentional: diagnostics validate the manifest being
# edited, even if the devShell still has an older fontkit package installed.
export PYTHONPATH="${REPO_ROOT}/lib${PYTHONPATH:+:${PYTHONPATH}}"
eval "$(python3 -m fontkit.manifest shell "${FAMILY_ROOT}/font.toml")"

# Realise one of this family's build steps and print its store path.
#
#   step src-latin-Regular   →  /nix/store/…-src-latin-sans-Regular
#
# This is why the steps are flake outputs and not an implementation detail of
# nix/families: measuring what the build actually produced beats re-deriving it
# in a second, drifting copy, which is what work/src/ was.
step() {
  nix --extra-experimental-features 'nix-command flakes' \
    build --no-link --print-out-paths "${REPO_ROOT}#${FAMILY}-$1"
}
