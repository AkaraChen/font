# AKR fonts — UX layer over Nix.
#
# just is deliberately NOT the build system: Nix is. Everything here is an alias
# for a nix invocation, for all seven families since Phase 5 — `just build sans`
# is `nix build .#sans` plus the copy into sans/out that the fingerprint net
# reads.
#
#   just dev                    → enter the pinned toolchain shell
#   just build sans             → nix build .#sans, materialised into sans/out
#   just build sans coding tc   → nix build .#sans-coding-tc, one matrix cell
#   just matrix                 → every cell every family declares
#   just fingerprint sans       → (re)write sans' regression baseline
#   just verify sans            → compare a fresh build against the baseline
#   just test                   → fontkit unit tests (lib/tests), no font build

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

# Every cell every family declares, read out of `[[build.matrix]]`.
#
# Not a hand-maintained list: the completion criterion for the region axis
# (KIT-282) is that this and `[[build.matrix]]` agree, and the only way to keep
# two lists agreeing is to have one. `just build <family> <profile> <region>`
# takes any line of this.
matrix:
    @{{nix}} eval --json .#lib.matrix | jq -r \
      '.[] | "\(.family) \(.profile) \(.region)  weights=\(.weights | join(",")) formats=\(.formats | join(","))"'

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
#
# With a profile and a region it builds one cell of `[[build.matrix]]` instead:
#
#   just build sans             → .#sans            every cell, into sans/out
#   just build sans coding tc   → .#sans-coding-tc  one cell, into sans/out-coding-tc
#
# The one-cell form writes to its own directory on purpose. `<family>/out` is
# what the fingerprint baseline is keyed on, and a partial build landing there
# would make `just verify` report every other region as MISSING.
build family profile="" region="":
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "{{profile}}" || -n "{{region}}" ]]; then
      if [[ -z "{{profile}}" || -z "{{region}}" ]]; then
        echo "just build <family> [<profile> <region>] — pass both or neither" >&2
        exit 2
      fi
      attr="{{family}}-{{profile}}-{{region}}"
      dest="{{family}}/out-{{profile}}-{{region}}"
    else
      attr="{{family}}"
      dest="{{family}}/out"
    fi
    out="$({{nix}} build --no-link --print-out-paths --print-build-logs ".#$attr")"
    rm -rf "$dest"
    cp -R "$out" "$dest"
    chmod -R u+w "$dest"
    ls -lhR "$dest"

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

# The toolchain's own fingerprint — what a laptop and CI have to agree on.
#
# `just verify` failing off `x86_64-linux` is expected and explained
# (fingerprints/README.md); this is the tool that explained it, and the one to
# reach for when a *new* disagreement turns up. CI prints the same table in the
# "Toolchain fingerprint" step of every family job, so diffing a local run
# against a CI log names the thing that differs.
toolchain-fingerprint:
    @{{nix}} develop --command python3 tools/toolchain-fingerprint.py

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
