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
#                                 (this is what CI builds — one job per cell,
#                                 KIT-305; the bare form still builds every cell)
#   just matrix                 → every cell every family declares
#   just fingerprint sans       → (re)write sans' regression baseline
#   just verify sans            → compare a fresh build against the baseline
#   just release sans coding tc → build one cell's release archive
#   just notes sans coding tc   → the release notes that archive ships with
#   just test                   → fontkit unit tests (lib/tests), no font build

set shell := ["bash", "-uc"]

# Flakes are still gated behind experimental-features on stock installs; pass it
# explicitly so a fresh checkout works without editing nix.conf first.
nix := "nix --extra-experimental-features 'nix-command flakes'"

families := "casual handwriting pixel rounded sans serif typewriter"

_default:
    @just --list --unsorted

# Refuse to start a font build off Linux (KIT-297).
#
# The flake stops offering the family attributes on darwin, so the machine-level
# answer is already "attribute 'sans' missing". This is the human-level one: the
# reason is not obvious, and the recipes below are where someone meets it.
#
# Not a capability problem — a darwin build runs fine and produces a *different
# font*, because FontForge rounds the icons the Nerd patch imports differently
# per architecture. Three hours, then a `just verify` failure that is nobody's
# bug. fingerprints/README.md has the measurement.
_linux-only recipe:
    #!/usr/bin/env bash
    set -euo pipefail
    # A plain `if`, not `[[ … ]] && exit 0`: under `set -e` that form is the
    # classic footgun — the failing test short-circuits the AND-list and the
    # message below never prints.
    if [[ "$(uname -s)" == "Linux" ]]; then
      exit 0
    fi
    exec >&2
    echo "just {{recipe}}: fonts are built on Linux only."
    echo
    echo "  This is $(uname -s)/$(uname -m). A build here would succeed and produce"
    echo "  a font that differs from the released one — FontForge redraws every"
    echo "  icon the Nerd patch imports, and that code rounds per architecture"
    echo "  (272 of 13797 glyphs, measured; see fingerprints/README.md)."
    echo
    echo "  Open a PR and let CI build it, or use a Linux machine or container."
    echo "  Everything that does not produce a shipped byte still works here:"
    echo "  just test / just dump / just fmt / just toolchain-fingerprint."
    exit 2

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

# Digest that keys the CI sources layer (sources-only projection of font.toml).
sources-cache-key:
    @python3 tools/sources-cache-key.py --digest

# Digest that keys the CI intermediates layer (latin-prepared + serif-sarasa).
intermediates-cache-key:
    @python3 tools/intermediates-cache-key.py --digest

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
build family profile="" region="": (_linux-only "build")
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
step family name: (_linux-only "step")
    {{nix}} build --out-link result-{{family}}-{{name}} .#{{family}}-{{name}}
    @ls -lLR result-{{family}}-{{name}}/

# The build steps one family has, with the axes that make each one rebuild.
steps family:
    @{{nix}} eval --json .#packages.$({{nix}} eval --raw --impure --expr builtins.currentSystem) \
      --apply 'ps: builtins.filter (n: builtins.match "{{family}}-.*" n != null) (builtins.attrNames ps)' \
      | jq -r '.[]'

# Run one family's gate against its products. The release step depends on this,
# so a red gate means no archive rather than an archive nobody checked.
gate family: (_linux-only "gate")
    {{nix}} build --no-link --print-build-logs .#{{family}}-verify

# Build a release archive (gated: it depends on `gate`).
#
# One archive per (profile, region) cell, named the way `just matrix` prints the
# cell (KIT-283):
#
#   just release sans                 → .#sans-release, the first cell
#   just release sans coding tc       → .#sans-coding-tc-release
#   just release handwriting text sc  → the reading face's archive
#
# The zip's version comes from `[naming] version` in font.toml, not from a flag:
# it is stamped into name ID 5 at build time, and a filename that could disagree
# with the font's own idea of its version is a bug waiting to be filed.
#
# Linux-only for the same reason `build` is (KIT-297): an archive is the product,
# and a darwin-built product is not the one that ships.
release family profile="" region="": (_linux-only "release")
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "{{profile}}" || -n "{{region}}" ]]; then
      if [[ -z "{{profile}}" || -z "{{region}}" ]]; then
        echo "just release <family> [<profile> <region>] — pass both or neither" >&2
        exit 2
      fi
      attr="{{family}}-{{profile}}-{{region}}-release"
    else
      attr="{{family}}-release"
    fi
    {{nix}} build --out-link result-{{family}}-release ".#$attr"
    ls -lL result-{{family}}-release/

# Render one cell's release notes from font.toml — pins, grid, weights, formats,
# source composition and the rename migration note. This is what the Release
# workflow publishes; run it locally to read the notes before tagging.
#
# Deliberately *not* Linux-only: it reads font.toml and writes markdown. Nothing
# it produces is a shipped byte, so it belongs with `just test` / `dump` / `fmt`
# on the list of things a Mac can still do (KIT-297).
notes family profile="coding" region="sc" version="":
    #!/usr/bin/env bash
    set -euo pipefail
    version="{{version}}"
    if [[ -z "$version" ]]; then
      version=$({{nix}} develop --command python3 -c "
    import tomllib
    with open('{{family}}/font.toml','rb') as fh:
        print(tomllib.load(fh)['naming'].get('version','0.1.0'))")
    fi
    {{nix}} develop --command fontkit release-notes \
      --manifest {{family}}/font.toml --profile {{profile}} \
      --region {{region}} --version "$version"

# Build every family, sequentially. Keeps going so one failure does not hide the rest.
build-all: (_linux-only "build-all")
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
fingerprint family: (_linux-only "fingerprint")
    {{nix}} develop --command python3 tools/fingerprint.py write {{family}}

# Compare the current build products against the committed baseline.
verify family: (_linux-only "verify")
    {{nix}} develop --command python3 tools/fingerprint.py check {{family}}

# Verify every family against its baseline.
verify-all: (_linux-only "verify-all")
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

# The toolchain's own fingerprint — accelerators, libm, and the two build steps
# that consume it.
#
# Runs anywhere, including the platforms that no longer build fonts; that is the
# point. It is what established which parts of the cross-platform difference are
# in *our* code (none) and which are in FontForge (all of it, KIT-297), and it is
# the first thing to run when CI's own answers start moving — a nixpkgs bump that
# quietly turns on fontTools' Cython accelerators would show up here as `so`.
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
