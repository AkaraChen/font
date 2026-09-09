#!/usr/bin/env bash
# Per-boot startup for the AKR fonts repo.
#
# The Nix store is baked into the snapshot by install.sh, but the daemon is a
# process, not a file, so it has to be (re)started every time the machine boots.
# This image has no systemd, so there is nothing else to do it.
set -euo pipefail

nix_profile="/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh"
# shellcheck disable=SC1090
[ -e "$nix_profile" ] && . "$nix_profile"

if [ ! -S /nix/var/nix/daemon-socket/socket ]; then
  sudo nohup /nix/var/nix/profiles/default/bin/nix-daemon >/tmp/nix-daemon.log 2>&1 &
  for _ in $(seq 1 60); do
    [ -S /nix/var/nix/daemon-socket/socket ] && break
    sleep 1
  done
fi
