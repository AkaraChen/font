# AKR fonts — UX layer over Nix.
#
# just is deliberately NOT the build system: Nix is. Everything here is either
# an alias for a nix invocation or a thin wrapper that runs the existing family
# scripts inside `nix develop`. Phase 0 changes no build logic.
#
#   just dev                → enter the pinned toolchain shell
#   just build sans         → run sans/scripts/build.sh in that shell, timed
#   just fingerprint sans   → (re)write sans' regression baseline
#   just verify sans        → compare a fresh build against the baseline

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

# Build one family: runs its existing scripts/build.sh step by step, timed.
build family:
    {{nix}} develop --command tools/build-family.sh {{family}}

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

# Show the recorded per-step wall-clock timings from the last build.
timings family:
    @cat {{family}}/work/step-timings.tsv

# Evaluate the flake on every declared system.
check:
    {{nix}} flake check --all-systems

# Refresh the nixpkgs pin. Deliberate act — re-run build + verify afterwards.
update:
    {{nix}} flake update

fmt:
    {{nix}} fmt
