#!/usr/bin/env bash
# Cloud Agent bootstrap for the AKR fonts repo.
#
# The whole toolchain is a Nix flake (see flake.nix / justfile), so the one
# durable dependency is Nix itself with flakes enabled. This image ships no
# systemd, so the daemon is a plain background process rather than a unit.
#
# Idempotent on purpose: with environment builds this runs once to make the
# snapshot, but it must also survive a re-run against an already-prepared tree.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
nix_profile="/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh"

# 1. Nix, with flakes. The Determinate installer writes
#    `extra-experimental-features = nix-command flakes` into /etc/nix/nix.conf.
#    `--init none`: no systemd here, so we manage the daemon ourselves (step 2).
if [ ! -e /nix/var/nix/profiles/default/bin/nix ]; then
  curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix \
    | sh -s -- install --no-confirm --init none
fi

# shellcheck disable=SC1090
[ -e "$nix_profile" ] && . "$nix_profile"

# 2. Start the daemon (no systemd → not a unit) and wait for its socket.
if [ ! -S /nix/var/nix/daemon-socket/socket ]; then
  sudo nohup /nix/var/nix/profiles/default/bin/nix-daemon >/tmp/nix-daemon.log 2>&1 &
  for _ in $(seq 1 60); do
    [ -S /nix/var/nix/daemon-socket/socket ] && break
    sleep 1
  done
fi

# 3. Make `nix` available to the interactive shells the agent opens later.
if ! grep -q 'nix-daemon.sh' "$HOME/.bashrc" 2>/dev/null; then
  printf '\n[ -e %s ] && . %s\n' "$nix_profile" "$nix_profile" >> "$HOME/.bashrc"
fi

# 4. Realise the pinned dev shell now, so `just build/test/...` is instant later.
#    Building it here is what a snapshot is for; leaving it for first use would
#    make an agent wait through a harfbuzz compile mid-task.
cd "$repo_root"
nix develop --command true

# 5. Website dependencies (site/ is a separate pnpm/Astro project).
if [ -d "$repo_root/site" ]; then
  corepack pnpm --dir "$repo_root/site" install --frozen-lockfile
fi
