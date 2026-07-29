# Shared scaffolding for the per-step family derivations.
#
# Phase 1 fixed the granularity contract (nix/granularity.nix) and the pinned
# sources (nix/sources). This is the layer that turns them into actual build
# steps, replacing the ~2900 lines of shell orchestration the six families
# carried between them.
#
# Three things live here because every family needs them identically:
#
#   pythonEnv   the interpreter the steps run on. `common.sh`'s `ensure_python`
#               — 30 lines of "uv, or venv, or pip, or die" per family — is
#               exactly this attribute now.
#   patcher     the pinned nerd-fonts checkout. Five families patch with it and
#               each used to unzip its own copy into <family>/work/.
#   step        granularity.mkStep with the defaults every step wants.
{ pkgs
, lib
, granularity
, sources
, fontkit
, root
,
}:

let
  weightName =
    weight:
    lib.toUpper (builtins.substring 0 1 weight)
    + builtins.substring 1 (builtins.stringLength weight - 1) weight;

  # fontTools + skia-pathops + fontkit, and nothing else. The devShell carries
  # more (Pillow, uharfbuzz, numpy) because the diagnostics under tools/ need
  # them; a build step that imported one of those would be reaching outside the
  # build vocabulary, so it is not in scope here and fails loudly if it tries.
  pythonEnv = pkgs.python3.withPackages (ps: [
    ps.fonttools
    ps.skia-pathops
    fontkit
  ]);

  # verify-features.py shapes text to prove the ligatures actually fire. It used
  # to print "uharfbuzz not installed — ligature shaping gate skipped" and pass,
  # which is a gate that reports green for the one thing it exists to check.
  verifyEnv = pkgs.python3.withPackages (ps: [
    ps.fonttools
    ps.skia-pathops
    ps.uharfbuzz
    fontkit
  ]);

  # Already a directory: the pin is a sparse checkout of the nerd-fonts repo, not
  # a release zip, so there is nothing to unpack. font-patcher resolves
  # `bin/scripts/name_parser` and `src/glyphs/` relative to its own path, which
  # is why those two are in the checkout.
  patcher = sources.fontPatcher;

  # The default scene and master. Five of the seven families build only this
  # cell and say so by taking these names; handwriting reads `[[build.matrix]]`
  # because Phase 6 (KIT-281) gave it a second profile, and sans / pixel read it
  # because Phase 7 (KIT-282) gave them the other regions.
  profile = "coding";
  region = "sc";

  # Every (profile, region) cell a family's matrix declares, as a flat list.
  # One reading of `[[build.matrix]]` for all seven modules, so "what does this
  # family build" has one answer rather than seven spellings of it.
  cellsOf =
    m:
    lib.concatMap
      (entry: map
        (region: {
          inherit (entry) profile;
          inherit region;
          weights = map weightName entry.weights;
          formats = entry.formats or [ "ttf" ];
        })
        entry.regions)
      m.build.matrix;

  # `[naming]` segments composed into one cell's names — the same arithmetic
  # `fontkit.manifest.naming_for` does, because both sides read the same TOML
  # and a product's file name (Nix) and its name table (Python) must not
  # disagree about what family it belongs to.
  #
  # Composed rather than looked up: `AKR Sans SC NFM` and `AKR Sans JP NFM` are
  # the same three segments and one axis value, and writing both out is how the
  # two eventually stop matching.
  namingFor =
    m: profile: region:
    let
      n = (builtins.removeAttrs m.naming [ "coding" "text" ]) // (m.naming.${profile} or { });
      compose = variant: lib.concatStringsSep " " [ n.house n.style (lib.toUpper region) variant ];
      strip = lib.replaceStrings [ " " ] [ "" ];
      family = compose n.variant;
      baseFamily = if (n.base_variant or null) == null then null else compose n.base_variant;
    in
    n // {
      inherit family region;
      ps = strip family;
      stem = strip family;
      id16 = family;
      base_family = baseFamily;
      base_ps = if baseFamily == null then null else strip baseFamily;
    };

  # granularity.mkStep, plus the defaults a font build step always wants.
  #
  # SOURCE_DATE_EPOCH is set to 0 rather than left at the stdenv default
  # (315532800). fontTools writes head.modified from it, and the devShell — the
  # side the fingerprint baselines were taken on — sets 0. The fingerprint
  # deliberately drops head.modified, so this changes no baseline; it is here so
  # that products built inside and outside the sandbox stay byte-comparable when
  # someone reaches for sha256 anyway.
  step =
    name: axes: args:
    granularity.mkStep pkgs name axes (
      {
        dontUnpack = true;
        SOURCE_DATE_EPOCH = "0";
      }
      // args
      // {
        nativeBuildInputs = [ pythonEnv ] ++ (args.nativeBuildInputs or [ ]);
      }
    );

  # `fontkit embolden --strength 0` is not a no-op: the pathops round-trip
  # rewrites every outline whatever the strength, so a family that pins 0
  # (rounded — Resource Han Rounded ships a real Bold) must copy the master
  # instead. The shells branched on this with `awk "BEGIN{exit !(s > 0)}"`;
  # the answer is fixed at pin time, so it belongs in eval.
  emboldenOrCopy =
    { strength, src, dst }:
    if strength == "0" || strength == "0.0" then
      "cp ${src} ${dst}"
    else
      "fontkit embolden ${src} ${dst} --strength ${strength}";

  # A file from the working tree as a build input. Single files, never the whole
  # checkout: a step that took `root` would rebuild when any family's README
  # changed, which is the cache key mistake nix/granularity.nix exists to stop.
  file = path: root + "/${path}";

  # --- the format axis (KIT-283) --------------------------------------------
  #
  # `packaged` is the only step in the granularity contract with a `format`
  # axis, and this is every family's use of it: hand over the TTF this cell
  # built and the format its `[[build.matrix]]` row declared, get back a
  # derivation holding exactly that one file.
  #
  # Per weight, not per cell. A derivation that converted three weights at once
  # would have to name one of them, and `packaged-handwriting-text-sc-Light-otf`
  # holding a Bold as well is the kind of graph nobody can bisect — the same
  # reason `merged` is per weight rather than per family.
  #
  # WOFF2 costs almost nothing here (a Brotli re-wrap of tables that already
  # exist) and OTF costs a qu2cu conversion of every glyph. That difference is
  # real, and it is visible in exactly the right place: two different derivations
  # with two different build times, rather than one step with a flag.
  convert =
    { family
    , profile
    , region
    , weight
    , format
    , src
    }:
    step "packaged" { inherit family profile region weight format; } {
      buildCommand = ''
        mkdir -p $out
        fontkit convert --format ${format} --out-dir $out ${src}/*.ttf
      '';
    };

  # What a cell declares beyond the TTF the build already produced. `ttf` is not
  # a conversion — it is what came out of `merged` / `nerd` — so a family that
  # declares `formats = ["ttf"]` gets no extra derivations at all.
  extraFormats = formats: lib.filter (f: f != "ttf") formats;

in
{
  inherit
    pythonEnv
    verifyEnv
    patcher
    profile
    region
    step
    file
    emboldenOrCopy
    weightName
    namingFor
    cellsOf
    convert
    extraFormats
    ;

  inherit (pkgs) fontforge;
}
