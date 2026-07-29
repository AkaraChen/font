# Selective intermediate products kept across CI runs (KIT-304).
#
# Family jobs restore sources + toolchain and rebuild *everything* above that
# every run — Nix's store hash is unused between runs because those jobs save
# nothing (docs/caching.md §3). The products layer as a whole does not fit the
# remaining 10 GB budget, so this is a hand-picked subset:
#
#   * latin-prepared  — region-independent; one face serves every region cell
#   * serif-sarasa    — the multi-minute upstream npm build; only rebuilds when
#                       SARASA_COMMIT / patches / CJK prep inputs move
#
# Final packaged faces are still not cached. `nix build .#ci-intermediates` is
# the single GC root the warmer job keeps; family builds then find the outputs
# already in the store.
{ pkgs
, lib
, families
,
}:

let
  # Attrs exported under packages.<system> — names must match flake outputs.
  want = [
    # casual: one profile, two weights
    "casual-latin-prepared-Regular"
    "casual-latin-prepared-Bold"
    # handwriting: two profiles × their matrix weights
    "handwriting-latin-prepared-coding-Regular"
    "handwriting-latin-prepared-coding-Bold"
    "handwriting-latin-prepared-text-Light"
    "handwriting-latin-prepared-text-Regular"
    "handwriting-latin-prepared-text-Bold"
    # serif's upstream Sarasa build (extras.sarasa → serif-sarasa)
    "serif-sarasa"
  ];

  missing = lib.filter (n: !(families ? ${n})) want;
  resolved =
    assert lib.assertMsg (missing == [ ])
      ("nix/intermediates: missing package attrs: "
        + lib.concatStringsSep ", " missing);
    map (n: { name = n; path = families.${n}; }) want;

in
pkgs.linkFarm "ci-intermediates" resolved
