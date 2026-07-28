#!/usr/bin/env bash
# Report what a cache layer actually costs, in bytes, on the machine that built
# it.
#
# The caching plan in KIT-275 is only as good as its numbers, and the numbers
# are platform-specific: a closure measured on a maintainer's aarch64-darwin
# laptop says nothing about the x86_64-linux runner whose 10 GB budget is the
# real constraint. So the runner measures itself, every run, and the result goes
# into the job summary where the next person changing the strategy will see it.
#
# Usage: tools/cache-report.sh <layer-name> <result-symlink> [<result-symlink>…]

set -euo pipefail

layer="${1:?usage: cache-report.sh <layer> <result>…}"
shift

NIX_BIN="${NIX_BIN:-nix}"
# One argument, not two: "nix-command flakes" is a single space-separated value.
nix_run() { "${NIX_BIN}" --extra-experimental-features "nix-command flakes" "$@"; }

human() { numfmt --to=iec --suffix=B "$1" 2>/dev/null || echo "$1"; }

# Closure size of one path, in bytes. `path-info -S` prints the *closure* size,
# so summing the recursive listing would double-count badly — ask for the root
# only.
closure_of() {
  # `nix path-info result-shell` reads a bare word as a *flake reference*, not a
  # path, and dies with "cannot find flake 'flake:result-shell'". Anchor it.
  local p="$1"
  [[ "${p}" == /* || "${p}" == ./* ]] || p="./${p}"
  nix_run path-info --json -S "${p}" \
    | python3 -c 'import json,sys; d=json.load(sys.stdin)
vs = list(d.values()) if isinstance(d, dict) else d
print(sum(v["closureSize"] for v in vs))'
}

total=0
rows=""
for link in "$@"; do
  [[ -e "${link}" ]] || {
    printf 'cache-report: %s does not exist — skipping\n' "${link}" >&2
    continue
  }
  size="$(closure_of "${link}")"
  total=$(( total + size ))
  rows+="| \`${link}\` | $(human "${size}") |"$'\n'
done

# The store as a whole is what gets tarred into the cache entry, which is
# usually larger than the sum of the layers above: `nix build` drags in build
# dependencies too. Reporting only the closures would flatter the strategy.
# `du -sb` is GNU-only, which is fine — the number that matters is the runner's.
# Say so rather than printing a 0 that reads like an empty store.
if store_bytes="$(du -sb /nix/store 2>/dev/null | cut -f1)" && [[ -n "${store_bytes}" ]]; then
  store_human="$(human "${store_bytes}")"
else
  store_human="not measured (needs GNU \`du -sb\`)"
fi

{
  printf '## Cache layer: `%s`\n\n' "${layer}"
  printf '| path | closure |\n| --- | ---: |\n%s' "${rows}"
  printf '| **layer total** | **%s** |\n\n' "$(human "${total}")"
  printf '`/nix/store` on disk: **%s** — this, not the layer total, is what\n' \
    "${store_human}"
  printf 'gets uploaded, and what counts against the 10 GiB repository ceiling.\n\n'
} | tee -a "${GITHUB_STEP_SUMMARY:-/dev/null}"
