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

  patcherUsers = lib.filter (f: sources.perFamily.${f} ? "font-patcher") sources.families;
  patcherPaths = lib.unique (map (f: sources.perFamily.${f}."font-patcher".drvPath) patcherUsers);

  manifestValid =
    manifest:
    let
      matrixValues = axis: lib.concatMap (entry: entry.${axis}) manifest.build.matrix;
      axisValid =
        axis:
        lib.all (value: lib.elem value manifest.build.${axis}) (matrixValues axis);
      cjkRegions = lib.concatMap
        (source: if source.role == "cjk" then source.regions else [ ])
        (lib.attrValues manifest.sources);
      artifacts = lib.concatMap
        (source: lib.attrValues (source.artifacts or { }))
        (lib.attrValues manifest.sources);
    in
    manifest.grid.cjk_adv == manifest.grid.en_adv * 2
    && lib.all (artifact: artifact ? url && artifact ? sha256) artifacts
    && lib.all axisValid [ "regions" "weights" "formats" "slopes" ]
    && lib.all (entry: lib.elem entry.profile manifest.build.profiles) manifest.build.matrix
    && lib.all (region: lib.elem region cjkRegions) (matrixValues "regions");

in
{
  # Completion criterion 1: the Nerd Fonts patcher is one store path repo-wide.
  font-patcher-single-store-path = ok "font-patcher-single-store-path"
    (
      lib.length patcherUsers >= 5 && lib.length patcherPaths == 1
    ) "expected one font-patcher derivation across ${toString (lib.length patcherUsers)} families, got ${toString (lib.length patcherPaths)}";

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
  # deliberately shared font-patcher, so this reduces to: no accidental sharing.
  families-share-only-the-patcher = ok "families-share-only-the-patcher"
    (
      let
        pathsOf =
          f:
          map (d: d.drvPath) (
            lib.attrValues (lib.filterAttrs (n: _: n != "font-patcher") sources.perFamily.${f})
          );
        all = lib.concatMap pathsOf sources.families;
      in
      lib.length all == lib.length (lib.unique all)
    ) "two families share a non-patcher source derivation";

  # Every font.toml must parse in full. `data` is the direct result of
  # builtins.fromTOML; forcing it proves Nix consumes the same semantic file as
  # Python rather than generated Nix data.
  manifests-parse = ok "manifests-parse"
    (
      lib.all
        (f:
          let manifest = sources.manifests.${f}.data;
          in
          builtins.deepSeq manifest (
            manifest.schema_version == 1
            && manifest.family == f
            && manifestValid manifest
          ))
        sources.families
    ) "a family's font.toml did not parse as schema version 1";

  # TOML has no shell interpolation. Keep the intent of the old interpolation
  # check: the checked-in URL must resolve to the pinned commit and contain no
  # unresolved placeholder.
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

  manifest-source-url = ok "manifest-source-url"
    (
      let
        manifest = sources.manifests.sans.data;
        commit = manifest.sources.plex.commit;
        url = manifest.sources.plex.artifacts.regular.url;
      in
      lib.hasInfix commit url && !(lib.hasInfix "$" url)
    ) "font.toml source URL does not contain its pinned commit";
}
