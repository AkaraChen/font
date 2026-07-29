# handwriting — Monaspace Radon (Latin) × LXGW WenKai 霞鹜文楷 (CJK).
#
# Was: 01-fetch-sources.sh … 06-verify.sh / build.sh / common.sh /
#      package-release.sh (350 lines).
#
# 01-fetch-sources.sh is the step that disappears most completely. It ran an
# HTTP-range extractor against a 315 MiB zip, then hedged with `if src_cache_get
# … else run the extractor`, then `curl`ed two licence files over the top of the
# committed copies on every build. The range extraction is a fixed-output
# derivation now (nix/sources), the hedge is what a store path is, and a build
# step that rewrites tracked files was never a fetch.
#
# Phase 6 (KIT-281) made this the first family with two profiles, so the module
# reads `[[build.matrix]]` instead of one hard-coded weight list. The two
# profiles differ in exactly three places, and every one of them is a row of the
# 判据 table rather than a Nix convenience:
#
#   src-latin        coding takes the pre-patched `MonaspaceRadonNF-*`, text
#                    takes the plain `MonaspaceRadon-*` from the same release.
#                    There is no un-patch step — "no Nerd Font patch" is a
#                    different donor.
#   merged           `--profile` decides the grid declaration, the cell policy
#                    and which ambiguous punctuation comes from WenKai.
#   expand-ligatures coding only. Folding ss01–ss10 into `calt` is what makes an
#                    editor show every Radon ligature by default; prose gets
#                    `liga` and the sets stay opt-in.
#
# `cjk-prepared` is shared by both, which is the granularity contract's other
# ★ claim doing its job: WenKai is emboldened and sheared to match Radon's ink,
# and ink does not change because the reader is reading instead of typing.
{ pkgs
, lib
, support
, sources
, manifest
,
}:

let
  inherit (support) step file region;
  m = manifest.data;
  inherit (m) grid;

  family = "handwriting";
  ps = profile: (support.namingFor m profile region).ps;

  # One entry per profile in [[build.matrix]]. `weights` is per entry, which is
  # how text gets a Light and coding does not.
  matrix = map
    (entry: {
      inherit (entry) profile;
      weights = map support.weightName entry.weights;
      formats = entry.formats;
    })
    m.build.matrix;

  entryFor = profile: lib.head (lib.filter (e: e.profile == profile) matrix);
  profiles = map (e: e.profile) matrix;

  cjkFor = weight: {
    master = support.weightName m.calibration.${lib.toLower weight}.source_weight;
    inherit (m.calibration.${lib.toLower weight}) embolden;
  };

  # The Latin donor is a function of the profile. Nothing else about the Latin
  # side is: the narrowing recipe, the cell and the UPM are the product grid,
  # which both profiles share.
  latinSrc = profile: weight:
    if profile == "coding" then
      { file = "MonaspaceRadonNF-${weight}.otf"; }
    else
      { file = "MonaspaceRadon-${weight}.otf"; };

  srcLatin = profile: weight:
    let src = latinSrc profile weight; in
    step "src-latin" { inherit family profile weight; } {
      buildCommand = ''
        mkdir -p $out
        cp ${sources.perFamily.handwriting.${src.file}} $out/${src.file}
      '';
    };

  # WenKai has no Bold; Medium backs both product faces and Light backs the
  # Light (measured — see [calibration.<weight>]).
  srcCjk = weight: step "src-cjk" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      cp ${sources.perFamily.handwriting."LXGWWenKai-${(cjkFor weight).master}.ttf"} \
        $out/LXGWWenKai-${(cjkFor weight).master}.ttf
    '';
  };

  # Radon's 1240/2000 cell → narrow to 1111 (x only) → 90 % uniform → 500/1000.
  # Identical arithmetic for both profiles: the Latin↔CJK proportion is what
  # this family *is*, and the 判据 table does not list it as a scene difference.
  latinPrepared = profile: weight:
    let src = latinSrc profile weight; in
    step "latin-prepared" { inherit family profile weight; } {
      buildCommand = ''
        mkdir -p $out
        python3 ${file "handwriting/scripts/prepare_latin.py"} \
          ${srcLatin profile weight}/${src.file} \
          $out/RadonLatin-${weight}.ttf \
          --src-upm ${toString grid.latin_src_upm} \
          --upm ${toString grid.upm} \
          --src-adv ${toString grid.latin_src_adv} \
          --narrow-adv ${toString grid.latin_narrow_adv} \
          --uniform-scale ${toString grid.latin_uniform_scale} \
          --en-adv ${toString grid.en_adv}
      '';
    };

  cjkPrepared = weight: step "cjk-prepared" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      fontkit prepare-cjk \
        ${srcCjk weight}/LXGWWenKai-${(cjkFor weight).master}.ttf \
        $out/WenKaiSlanted-${weight}.ttf \
        --embolden ${toString (cjkFor weight).embolden} \
        --slant-deg ${toString m.calibration.${lib.toLower weight}.slant_deg} \
        --pivot-y ${toString m.calibration.${lib.toLower weight}.slant_pivot_y}
    '';
  };

  # Merge exactly the weight this derivation is named for. It used to build
  # every weight and copy one out, which was invisible at two weights and would
  # have been three merges of throwaway work per product at three.
  #
  # Then, for coding only, fold Monaspace's stylistic sets into default `calt`.
  # Radon parks essentially every coding ligature behind ss01–ss10, so an editor
  # that only flips `calt` shows none of them; 05-expand-ligatures.sh existed for
  # that and is one flag of the merge step now, not a script that reached into
  # serif/.
  merged = profile: weight: step "merged" { inherit family profile region weight; } {
    buildCommand = ''
      mkdir -p $out merged
      fontkit merge \
        --manifest ${manifest.file} \
        --profile ${profile} \
        --weight ${weight} \
        --latin ${latinPrepared profile weight}/RadonLatin-${weight}.ttf \
        --cjk ${cjkPrepared weight}/WenKaiSlanted-${weight}.ttf \
        --out-dir merged

      cp merged/${ps profile}-${weight}.ttf $out/
    '' + lib.optionalString (profile == "coding") ''
      fontkit expand-ligatures \
        --include ${lib.concatStringsSep "," m.options.ligature_sets} \
        $out/${ps profile}-${weight}.ttf
    '';
  };

  # The `format` axis, finally carrying more than one value. WOFF2 is a re-wrap
  # of the same tables, not a second build — see lib/fontkit/convert.py.
  packagedFormat = profile: weight: format:
    step "packaged" { inherit family profile region weight format; } {
      buildCommand = ''
        mkdir -p $out
        fontkit convert --format ${format} --out-dir $out \
          ${merged profile weight}/${ps profile}-${weight}.ttf
      '';
    };

  productsOf = profile:
    let entry = entryFor profile; in
    lib.concatMap
      (weight:
        [ "cp ${merged profile weight}/*.ttf $out/" ]
        ++ map (format: "cp ${packagedFormat profile weight format}/*.${format} $out/")
          (lib.filter (f: f != "ttf") entry.formats))
      entry.weights;

  out = pkgs.runCommand "handwriting-out" { } ''
    mkdir -p $out
    ${lib.concatStringsSep "\n" (lib.concatMap productsOf profiles)}
    cp ${file "handwriting/licenses"}/OFL-Monaspace.txt \
       ${file "handwriting/licenses"}/OFL-LXGWWenKai.txt $out/
  '';

  # verify-features.py needs a real shaper to prove the ligatures fire, so this
  # runs on verifyEnv (uharfbuzz) rather than the build interpreter.
  #
  # Two gates, not one with a flag: every assertion in `verify-2to1` is a claim
  # about a terminal cell, and a text product fails all of them *for being
  # correct*. See lib/fontkit/verify_text.py.
  verify = pkgs.runCommand "handwriting-verify"
    {
      nativeBuildInputs = [ support.verifyEnv ];
    }
    ''
      fontkit verify-2to1 --profile dense --check-nerd --check-eaw \
        ${out}/${ps "coding"}-*.ttf
      python3 ${file "handwriting/scripts/verify-features.py"} \
        --expect-half ${toString grid.en_adv} ${out}/${ps "coding"}-*.ttf

      fontkit verify-text --expect-full ${toString grid.cjk_adv} \
        ${out}/${ps "text"}-*.ttf

      # Informational, like sans'. See the note there about measure.py and
      # all-off-curve contours.
      for font in ${out}/*.ttf; do
        fontkit measure --font "$font" | tail -20 || true
      done
      touch $out
    '';

  readme = profile: pkgs.writeText "handwriting-${profile}-README.txt" (
    let naming = support.namingFor m profile region; in
    ''
      ${naming.family} @version@
      Derived from Monaspace Radon (${m.sources.monaspace.version}) and
      LXGW WenKai 霞鹜文楷 (${m.sources.wenkai.version}) under SIL OFL 1.1.
      Not an official Monaspace / GitHub Next or LXGW product.

      Name recipe:
        Radon    = Monaspace Radon (Latin, ligatures + OpenType features)
        WenKai   = 霞鹜文楷 (CJK, sheared ${toString m.calibration.regular.slant_deg}° to Radon's lean)
    '' + (
      if profile == "coding" then ''
          NFM      = Nerd Font Mono product (icons at one cell)

        Cell metrics: EN ${toString grid.en_adv} / CJK ${toString grid.cjk_adv} (strict 2:1)
        Nerd icons:   from the upstream Monaspace Radon NF build, one cell each
        Ligatures:    Radon liga + calt (on by default), plus ss01–ss10 / cv** opt-in
        Weights:      Regular, Bold
      '' else ''
          Text     = reading face, not a terminal face

        This is NOT a monospaced font and does not advertise itself as one. It
        drops the strict 2:1 declaration, carries no Nerd icons, and leaves
        East_Asian_Width alone so … and — stay full width the way Chinese
        typography sets them. Line box is typographic: ${toString m.metrics.text.os2_typo_line_gap} units of leading.

        Ligatures:    Radon liga only; ss01–ss10 / cv** stay opt-in
        Weights:      Light, Regular, Bold
        Formats:      TTF and WOFF2 (no OTF — see build.unsupported in font.toml)
      ''
    ) + ''

      Upstream pins: see handwriting/font.toml in the build repository.
    ''
  );

  releaseFor = profile:
    let
      entry = entryFor profile;
      naming = support.namingFor m profile region;
    in
    {
      inherit family profile region verify;
      inherit (entry) formats;
      readme = readme profile;
      weight = lib.head entry.weights;
      stem = naming.stem;
      fontDir = pkgs.runCommand "handwriting-${profile}-products" { } ''
        mkdir -p $out
        ${lib.concatStringsSep "\n" (productsOf profile)}
      '';
      licenseDir = file "handwriting/licenses";
    };

in
{
  inherit out verify;

  # `nix build .#handwriting-coding-sc` / `.#handwriting-text-sc`. One entry per
  # (profile, region) cell in [[build.matrix]] — the products of that cell, with
  # no licence files, so a cell is exactly what its matrix row says it is.
  cells = lib.listToAttrs (map
    (entry: {
      name = "${entry.profile}-${region}";
      value = pkgs.runCommand "handwriting-${entry.profile}-${region}" { } ''
        mkdir -p $out
        ${lib.concatStringsSep "\n" (productsOf entry.profile)}
      '';
    })
    matrix);

  steps = lib.listToAttrs (
    lib.concatMap
      (entry: lib.concatMap
        (weight: [
          { name = "src-latin-${entry.profile}-${weight}"; value = srcLatin entry.profile weight; }
          { name = "src-cjk-${weight}"; value = srcCjk weight; }
          { name = "latin-prepared-${entry.profile}-${weight}"; value = latinPrepared entry.profile weight; }
          { name = "cjk-prepared-${weight}"; value = cjkPrepared weight; }
          { name = "merged-${entry.profile}-${weight}"; value = merged entry.profile weight; }
        ]
        ++ map
          (format: {
            name = "packaged-${entry.profile}-${weight}-${format}";
            value = packagedFormat entry.profile weight format;
          })
          (lib.filter (f: f != "ttf") entry.formats))
        entry.weights)
      matrix
  );

  release = releaseFor "coding";

  # `nix build .#handwriting-text-release`. The coding archive keeps the bare
  # `<family>-release` name it has always had.
  extraReleases.text = releaseFor "text";
}
