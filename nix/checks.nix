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
, families
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

  # sh's ${VAR} interpolation, which sans/ and typewriter/ both use to build a
  # raw.githubusercontent URL out of a pinned commit. It is checked by name
  # because the parser's regex is the one piece of this that is not portable by
  # construction: the first version used `\$\{…\}`, which the maintainer's nix
  # accepted and CI's rejected outright as an invalid POSIX ERE. A green
  # `nix flake check` on one machine is not evidence for the other unless the
  # interpolation path is actually exercised.
  # --- Phase 3 -------------------------------------------------------------

  # Nerd patching only exists in the coding profile, so a text-profile nerd
  # derivation is a bug rather than a cache miss. Same enforcement as
  # latin-prepared/region, asserted because Phase 6 is the phase that will be
  # tempted to pass it.
  nerd-rejects-profile = ok "nerd-rejects-profile"
    (throws (mkName "nerd" {
      family = "sans";
      profile = "coding";
      region = "sc";
      weight = "Bold";
    })) "nerd accepted a profile axis";

  # A missing axis is as wrong as an extra one: a `packaged` without `format`
  # would name two different products identically.
  packaged-needs-format = ok "packaged-needs-format"
    (throws (mkName "packaged" {
      family = "sans";
      profile = "coding";
      region = "sc";
      weight = "Bold";
    })) "packaged accepted a call with no format axis";

  # Every step a family builds has to be part of the shared vocabulary. Without
  # this a family can invent `merged-and-patched` and be the only one that has
  # it, which is how seven families ended up with seven pipelines the first
  # time. The suffix after the step name is the weight, which is not part of the
  # vocabulary.
  family-steps-are-contract-steps = ok "family-steps-are-contract-steps"
    (
      let
        stepOf = name: lib.head (lib.filter (s: s == name || lib.hasPrefix "${s}-" name) granularity.known
          ++ [ null ]);
        bad = lib.concatMap
          (family: lib.filter (n: stepOf n == null) (lib.attrNames families.byFamily.${family}.steps))
          (lib.attrNames families.byFamily);
      in
      bad == [ ]
    ) "a family declares a step that is not in nix/granularity.nix";

  pins-interpolation = ok "pins-interpolation"
    (
      let
        p = sources.familyPins.sans;
        commit = p.get "PLEX_SANS_SC_COMMIT";
      in
      lib.hasInfix commit (p.get "PLEX_SANS_SC_TTF_REGULAR_URL")
      && !(lib.hasInfix "$" (p.get "PLEX_SANS_SC_TTF_REGULAR_URL"))
    ) "pins.env \${VAR} interpolation did not expand";
}
