#!/usr/bin/env bash
# Bridge between "Nix fetched it" and "the build script wants it".
#
# **serif only, and only until serif's Sarasa toolchain moves into Nix.** The
# other six families take their pinned artifacts as build inputs — a store path
# handed to a derivation, with nothing to look up and nothing to fall back to.
# serif still runs a shell pipeline, so it still needs the lookup.
#
# Phase 3 deleted this file along with the six families that used it, which
# broke serif's build: serif/scripts/common.sh sources it. It is back, scoped to
# its one remaining caller, rather than left deleted with serif carrying an
# unpinned curl — the hash gate below is the only thing standing between serif
# and an unverified download.
#
# Every family script already knows the sha256 of what it is about to download —
# it verifies against it afterwards. So the cheapest bridge is a lookup by that
# same hash: nix/source-cache.nix publishes by-sha256/<hex>, and this file makes
# download_file / download_zip check there before reaching for curl.
#
# FONTKIT_SRC_CACHE is set by `just build serif`, which realises the cache, or
# by hand:  export FONTKIT_SRC_CACHE=$(nix build --no-link --print-out-paths .#source-cache)
#
# Unset or missing entry → the caller's own curl path runs, unchanged.

# Copy the pinned artifact for <sha256> into <dest>. 0 on hit, 1 on miss.
src_cache_get() {
  local sha="$1" dest="$2"
  [[ -n "${FONTKIT_SRC_CACHE:-}" ]] || return 1
  local hit="${FONTKIT_SRC_CACHE}/by-sha256/${sha}"
  [[ -f "${hit}" ]] || return 1
  mkdir -p "$(dirname "${dest}")"
  # Store paths are read-only; the copy must not be, because several steps
  # unzip/rewrite in place.
  cp -f "${hit}" "${dest}"
  chmod u+w "${dest}"
  return 0
}

# Drop-in replacement for the per-family download_file/download_zip.
#
# Same three arguments, same postcondition (file at $dest with sha256 == $3).
# The caller's own implementation is used as the fallback and is expected to be
# named ${1}_via_curl — see the wiring in each family's common.sh.
src_fetch() {
  local url="$1" dest="$2" sha="$3"

  if [[ -f "${dest}" ]] && [[ "$(sha256_of "${dest}")" == "${sha}" ]]; then
    log "cached $(basename "${dest}")"
    return 0
  fi

  if src_cache_get "${sha}" "${dest}"; then
    log "from nix store: $(basename "${dest}")"
    verify_sha256 "${dest}" "${sha}"
    return 0
  fi

  [[ -f "${dest}" ]] && log "stale cache for $(basename "${dest}"), re-downloading"
  need_cmd curl
  log "downloading ${url}"
  curl -fL --retry 3 --retry-delay 2 -o "${dest}.partial" "${url}"
  mv "${dest}.partial" "${dest}"
  verify_sha256 "${dest}" "${sha}"
}
