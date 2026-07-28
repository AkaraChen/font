# AKR fonts — UX layer over Nix.
#
# just is deliberately NOT the build system: Nix is. Everything here is an alias
# for a nix invocation, for all seven families since Phase 5 — `just build sans`
# is `nix build .#sans` plus the copy into sans/out that the fingerprint net
# reads.
#
#   just dev                → enter the pinned toolchain shell
#   just build sans         → nix build .#sans, materialised into sans/out
#   just fingerprint sans   → (re)write sans' regression baseline
#   just verify sans        → compare a fresh build against the baseline
#   just test               → fontkit unit tests (lib/tests), no font build

set shell := ["bash", "-uc"]

# Flakes are still gated behind experimental-features on stock installs; pass it
# explicitly so a fresh checkout works without editing nix.conf first.
nix := "nix --extra-experimental-features 'nix-command flakes'"

families := "casual handwriting pixel rounded sans serif typewriter"

_default:
    @just --list --unsorted

# Enter the pinned toolchain shell.
dev:
    {{nix}} develop

# List the families this repo builds.
matrix:
    @for f in {{families}}; do echo "$f"; done

# Realise every pinned upstream input (nix/sources). The build steps depend on
# these directly; this is for looking at them.
sources:
    @{{nix}} build --no-link --print-out-paths .#source-cache

# Realise one family's sources under readable filenames, for poking at them.
sources-of family:
    {{nix}} build --out-link result-sources-{{family}} .#sources-{{family}}
    @ls -lL result-sources-{{family}}/

# What makes each build step rebuild — the derivation-granularity contract.
# The axes listed here are the cache keys; anything not listed is shared.
graph:
    @{{nix}} eval --json .#lib.granularity.steps | jq -r \
      'to_entries[] | "\(.key)\n  axes: \(.value.axes | join(", "))\n  \(.value.note)\n"'

# Report the closure size of a cache layer (what CI counts against the 10 GB cap).
cache-report layer +results:
    @tools/cache-report.sh {{layer}} {{results}}

# Build one family and materialise its products under <family>/out.
#
# All seven are derivations since Phase 5 (KIT-280) moved serif's Sarasa
# toolchain in, so this is a `nix build` and a copy — no family branch left.
# The copy exists because tools/fingerprint.py walks <family>/out and names each
# product by its path relative to it — pointing it at a store path instead would
# work, but then a baseline would depend on where the store happens to be.
build family:
    #!/usr/bin/env bash
    set -euo pipefail
    out="$({{nix}} build --no-link --print-out-paths --print-build-logs .#{{family}})"
    rm -rf {{family}}/out
    cp -R "$out" {{family}}/out
    chmod -R u+w {{family}}/out
    ls -lhR {{family}}/out

# Build one step in isolation — for bisecting a fingerprint diff, or feeding a
# calibration run. `just steps <family>` lists what a family has.
step family name:
    {{nix}} build --out-link result-{{family}}-{{name}} .#{{family}}-{{name}}
    @ls -lLR result-{{family}}-{{name}}/

# The build steps one family has, with the axes that make each one rebuild.
steps family:
    @{{nix}} eval --json .#packages.$({{nix}} eval --raw --impure --expr builtins.currentSystem) \
      --apply 'ps: builtins.filter (n: builtins.match "{{family}}-.*" n != null) (builtins.attrNames ps)' \
      | jq -r '.[]'

# Run one family's gate against its products. The release step depends on this,
# so a red gate means no archive rather than an archive nobody checked.
gate family:
    {{nix}} build --no-link --print-build-logs .#{{family}}-verify

# Build the release archive (gated: it depends on `gate`).
release family:
    {{nix}} build --out-link result-{{family}}-release .#{{family}}-release
    @ls -lL result-{{family}}-release/

# Build every family, sequentially. Keeps going so one failure does not hide the rest.
build-all:
    #!/usr/bin/env bash
    set -uo pipefail
    failed=()
    for f in {{families}}; do
      just build "$f" || failed+=("$f")
    done
    if (( ${#failed[@]} )); then
      printf 'failed: %s\n' "${failed[*]}" >&2
      exit 1
    fi

# (Re)write a family's fingerprint baseline from its current build products.
# Idempotent: same products in, byte-identical files out.
fingerprint family:
    {{nix}} develop --command python3 tools/fingerprint.py write {{family}}

# Compare the current build products against the committed baseline.
verify family:
    {{nix}} develop --command python3 tools/fingerprint.py check {{family}}

# Verify every family against its baseline.
verify-all:
    #!/usr/bin/env bash
    set -uo pipefail
    failed=()
    for f in {{families}}; do
      just verify "$f" || failed+=("$f")
    done
    if (( ${#failed[@]} )); then
      printf 'fingerprint drift: %s\n' "${failed[*]}" >&2
      exit 1
    fi

# Print one font file's normalised fingerprint (for ad-hoc inspection).
dump font:
    {{nix}} develop --command python3 tools/fingerprint.py dump {{font}}

# Run the fontkit unit tests (seconds — no font build needed).
test:
    {{nix}} develop --command env PYTHONPATH=lib python3 -m pytest lib/tests -q

# Evaluate the flake on every declared system, and build + test fontkit.
check:
    {{nix}} flake check --all-systems

# Refresh the nixpkgs pin. Deliberate act — re-run build + verify afterwards.
update:
    {{nix}} flake update

fmt:
    {{nix}} fmt
