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

  # --- Phase 6 (KIT-281) ----------------------------------------------------

  # A profile is a set of vertical metrics before it is anything else, and both
  # Nix and Python read the same table. Enforced on the eval side too so a
  # missing `[metrics.text]` is a `nix flake check` failure in seconds rather
  # than a merge step that dies an hour into a build.
  every-built-profile-has-metrics = ok "every-built-profile-has-metrics"
    (
      lib.all
        (f:
          let m = sources.manifests.${f}.data;
          in !(m ? merge) || lib.all (p: m.metrics or { } ? ${p}) m.build.profiles)
        sources.families
    ) "a family declares a profile with no [metrics.<profile>] table";

  # Two profiles must not ship under one family name: a host would treat them as
  # two styles of one family and pick either of them for Bold.
  #
  # Asserted on the *composed* name rather than on "is there a [naming.<profile>]
  # table", because with segment-based naming (KIT-282) a table that overrode
  # only `product_name_zh` would satisfy the older spelling and still collide.
  second-profile-is-renamed = ok "second-profile-is-renamed"
    (
      lib.all
        (f:
          let
            m = sources.manifests.${f}.data;
            names = map (p: (families.support.namingFor m p "sc").family) m.build.profiles;
          in
          lib.length (lib.unique names) == lib.length names)
        sources.families
    ) "two of a family's profiles compose to the same family name";

  # --- Phase 7 (KIT-282) ----------------------------------------------------

  # The rename's whole point: no upstream reserved font name survives in a
  # product's family name. `pins.env` warned about this in five places and the
  # rfn_note fields asked for it; this is the check that keeps it true.
  #
  # Matched case-insensitively against the composed name for every cell — an
  # `AKR Sans SC NFM` that someone later respelled `AKR Lilex SC NFM` is the
  # exact regression being prevented.
  no-upstream-reserved-name-in-a-family-name =
    let
      reserved = [
        "iosevka"
        "monaspace"
        "radon"
        "lilex"
        "plex"
        "lxgw"
        "wenkai"
        "sarasa"
        "recursive"
        "yozai"
        "courier"
        "zhuque"
        "fusion"
        "resourcehan"
        "neozhisong"
      ];
      composed = lib.concatMap
        (f:
          let
            m = sources.manifests.${f}.data;
            regions = m.build.regions;
          in
          lib.concatMap
            (p: lib.concatMap
              (r:
                let n = families.support.namingFor m p r;
                in [ n.family ] ++ lib.optional (n.base_family != null) n.base_family)
              regions)
            m.build.profiles)
        sources.families;
      offending = lib.filter
        (name: lib.any (word: lib.hasInfix word (lib.toLower (lib.replaceStrings [ " " ] [ "" ] name))) reserved)
        composed;
    in
    ok "no-upstream-reserved-name-in-a-family-name" (offending == [ ])
      "a composed family name still carries an upstream reserved name: ${
        lib.concatStringsSep ", " offending
      }";

  # Name ID 1 carries the weight for anything outside RIBBI, so the 31-character
  # Windows budget is a property of the longest *product* name a matrix cell can
  # produce — family plus `Light` — not of the family name.
  every-product-name-fits-the-windows-budget =
    let
      # The same split fontkit.naming.ribbi_split does: Regular and Bold stay in
      # name ID 2, anything else moves into name ID 1.
      productName = family: weight:
        if lib.elem weight [ "regular" "bold" ] then
          family
        else
          "${family} ${lib.toUpper (builtins.substring 0 1 weight)}${builtins.substring 1 (-1) weight}";
      names = lib.concatMap
        (f:
          let m = sources.manifests.${f}.data;
          in lib.concatMap
            (entry: lib.concatMap
              (r:
                let n = families.support.namingFor m entry.profile r;
                in map (w: productName n.family w) entry.weights
                ++ lib.optional (n.base_family != null) n.base_family)
              entry.regions)
            m.build.matrix)
        sources.families;
      over = lib.filter (name: lib.stringLength name > 31) names;
    in
    ok "every-product-name-fits-the-windows-budget" (over == [ ])
      "name ID 1 over the 31-character Windows budget: ${lib.concatStringsSep ", " over}";

  # The region axis is only free if the Latin side really is shared, and sans is
  # the family that has to prove it: four regions, two weights, and *two*
  # `src-latin` derivations rather than eight.
  #
  # `latin-prepared-rejects-region` above says the contract forbids widening the
  # key; this says the family did not find some other way to fan out — a
  # per-region `srcLatin` that simply ignores its region argument would pass the
  # contract check and fail this one.
  sans-builds-one-latin-for-four-regions = ok "sans-builds-one-latin-for-four-regions"
    (
      let
        steps = families.byFamily.sans.steps;
        regions = sources.manifests.sans.data.build.regions;
        weights = sources.manifests.sans.data.build.weights;
        latin = lib.filter (lib.hasPrefix "src-latin-") (lib.attrNames steps);
        paths = lib.unique (map (name: steps.${name}.drvPath) latin);
      in
      lib.length regions == 4
      && lib.length latin == lib.length weights
      && lib.length paths == lib.length weights
    ) "sans fans its Latin build out per region, or stopped declaring four regions";

  # "不支持的显式声明，不是静默缺失" — an axis value a family cannot produce is
  # declared with a reason, and a declared value is never also disowned.
  unsupported-is-declared-with-a-reason = ok "unsupported-is-declared-with-a-reason"
    (
      lib.all
        (f:
          let
            m = sources.manifests.${f}.data;
            entries = m.build.unsupported or [ ];
          in
          lib.all
            (e:
              e ? axis && e ? values && e ? reason
              && e.reason != ""
              && lib.length e.values > 0
              && lib.all (v: !(lib.elem v m.build.${e.axis})) e.values)
            entries)
        sources.families
    ) "a build.unsupported entry has no reason, or disowns a value the family also declares";

  # The three families that cannot take a Light say so. Without this the check
  # is satisfied by deleting the declarations, which is the failure mode the
  # completion criterion names.
  light-impossibility-is-on-the-record = ok "light-impossibility-is-on-the-record"
    (
      lib.all
        (f:
          let m = sources.manifests.${f}.data;
          in lib.any
            (e: e.axis == "weights" && lib.elem "light" e.values)
            (m.build.unsupported or [ ]))
        [ "serif" "typewriter" "pixel" ]
    ) "serif / typewriter / pixel must declare that Light is impossible, not just omit it";

  # The mirror of `nerd-rejects-profile`: Phase 6 gave src-latin a profile axis
  # because "no Nerd patch" is a different upstream file, not an un-patch step.
  # Region is still not an axis, and must not become one.
  src-latin-rejects-region = ok "src-latin-rejects-region"
    (throws (mkName "src-latin" {
      family = "handwriting";
      profile = "text";
      region = "sc";
      weight = "Light";
    })) "src-latin accepted a region axis — five regions would fetch five copies";

  manifest-source-url = ok "manifest-source-url"
    (
      let
        manifest = sources.manifests.sans.data;
        commit = manifest.sources.plex.commit;
        url = manifest.sources.plex.artifacts.sc_regular.url;
      in
      lib.hasInfix commit url && !(lib.hasInfix "$" url)
    ) "font.toml source URL does not contain its pinned commit";
}
