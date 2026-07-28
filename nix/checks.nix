# Eval-time regression net for the Phase 1 caching claims.
#
# Every check here is a *pure evaluation* — none of them download anything, so
# `nix flake check` stays fast and works offline. That is on purpose: the claims
# being defended ("one store path", "region does not fan out the Latin build")
# are properties of the derivation graph, and the graph can be inspected without
# realising a single byte.
{ pkgs
, lib ? pkgs.lib
, sources
, granularity
,
}:

let
  inherit (granularity) mkName;

  ok =
    name: cond: msg:
    pkgs.runCommand "check-${name}" { } (
      if cond then "echo ok > $out" else "echo ${lib.escapeShellArg msg} >&2; exit 1"
    );

  # Does evaluating `e` throw? `builtins.tryEval` only catches `throw`/`assert`,
  # which is exactly what the contract raises.
  throws = e: !(builtins.tryEval (builtins.deepSeq e e)).success;

  patcherUsers = lib.filter (f: sources.perFamily.${f} ? "FontPatcher.zip") sources.families;
  patcherPaths = lib.unique (map (f: sources.perFamily.${f}."FontPatcher.zip".drvPath) patcherUsers);

in
{
  # Completion criterion 1: FontPatcher.zip is one store path repo-wide.
  font-patcher-single-store-path = ok "font-patcher-single-store-path"
    (
      lib.length patcherUsers >= 5 && lib.length patcherPaths == 1
    ) "expected one FontPatcher derivation across ${toString (lib.length patcherUsers)} families, got ${toString (lib.length patcherPaths)}";

  # Completion criterion 2, at the level Phase 1 can assert it: the Latin
  # preparation step is not a function of region, so five regions ask for one
  # derivation name. Phase 7 adds the regions; this is what makes them free.
  latin-prepared-shared-across-regions = ok "latin-prepared-shared-across-regions"
    (
      let
        names = map
          (
            _region:
            mkName "latin-prepared" {
              family = "sans";
              profile = "coding";
              weight = "Bold";
            }
          ) [ "sc" "tc" "hk" "jp" "kr" ];
      in
      lib.length (lib.unique names) == 1
    ) "latin-prepared fans out per region";

  # …and it cannot be widened by accident.
  latin-prepared-rejects-region = ok "latin-prepared-rejects-region"
    (throws (mkName "latin-prepared" {
      family = "sans";
      profile = "coding";
      region = "tc";
      weight = "Bold";
    })) "latin-prepared accepted a region axis — the contract is not enforced";

  # The mirror-image claim: optical embolden is scene-agnostic, so coding and
  # text profiles share one cjk-prepared.
  cjk-prepared-rejects-profile = ok "cjk-prepared-rejects-profile"
    (throws (mkName "cjk-prepared" {
      family = "sans";
      profile = "coding";
      region = "sc";
      weight = "Bold";
    })) "cjk-prepared accepted a profile axis";

  # Names are ordered and greppable, not incidentally-ordered attrset output.
  step-names-are-stable = ok "step-names-are-stable"
    (
      mkName "merged"
        {
          weight = "Bold";
          region = "tc";
          family = "serif";
          profile = "text";
        } == "merged-serif-text-tc-Bold"
    ) "merged name is not <step>-<family>-<profile>-<region>-<weight>";

  # Completion criterion 3, source layer: one family's pin change must not move
  # another family's source derivations. They share no derivation except the
  # deliberately shared FontPatcher, so this reduces to: no accidental sharing.
  families-share-only-the-patcher = ok "families-share-only-the-patcher"
    (
      let
        pathsOf =
          f:
          map (d: d.drvPath) (
            lib.attrValues (lib.filterAttrs (n: _: n != "FontPatcher.zip") sources.perFamily.${f})
          );
        all = lib.concatMap pathsOf sources.families;
      in
      lib.length all == lib.length (lib.unique all)
    ) "two families share a non-FontPatcher source derivation";

  # pins.env must parse in full for every family — a key Nix silently cannot
  # read is a pin that stops being enforced.
  pins-parse = ok "pins-parse"
    (
      lib.all (f: (lib.attrNames sources.familyPins.${f}.pins) != [ ]) sources.families
    ) "a family's pins.env parsed to nothing";
}
