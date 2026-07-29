# casual — Recursive Mono Casual (Latin) × Yozai 悠哉 (CJK), strict 2:1.
#
# Was: 01-fetch-sources.sh … 05-verify.sh / build.sh / common.sh /
#      package-release.sh (360 lines).
#
# This family is where the cross-family coupling was worst: `common.sh` exported
# `HANDWRITING_SCRIPTS` and three steps reached into `../handwriting/scripts/`
# for the CJK prepare and the merge engine, while `05-verify.sh` went looking
# for its own gate with `if [[ -f serif/… ]] elif [[ -f rounded/… ]]`. Both
# engines are `fontkit` modules now, so the reach is gone by construction — a
# derivation cannot see a path it was not given.
{ pkgs
, lib
, support
, sources
, manifest
,
}:

let
  inherit (support) step file profile region;
  m = manifest.data;
  inherit (m) grid;
  # One cell, composed rather than read: `[naming]` holds segments now, and the
  # region is a build axis (KIT-282).
  naming = support.namingFor m profile region;
  recursive = m.sources.recursive;
  yozai = m.sources.yozai;

  family = "casual";
  weights = map support.weightName m.build.weights;

  ps = naming.ps;

  # Which Yozai master backs each product face, and how hard to stroke it.
  # Measured, not guessed — see casual/font.toml and tools/calibrate-cjk-weight.py.
  cjkFor = {
    Regular = {
      master = support.weightName m.calibration.regular.source_weight;
      embolden = m.calibration.regular.embolden;
    };
    Bold = {
      master = support.weightName m.calibration.bold.source_weight;
      embolden = m.calibration.bold.embolden;
    };
  };

  # --- src ------------------------------------------------------------------
  srcLatin = weight: step "src-latin" { inherit family profile weight; } {
    nativeBuildInputs = [ pkgs.unzip ];
    buildCommand = ''
      mkdir -p $out unpacked
      unzip -q ${sources.perFamily.casual."ArrowType-Recursive.zip"} \
        ${lib.escapeShellArg recursive.artifacts.${lib.toLower weight}.member} -d unpacked
      cp unpacked/${lib.escapeShellArg recursive.artifacts.${lib.toLower weight}.member} \
        $out/RecursiveMonoCsl-${weight}.ttf
    '';
  };

  # Yozai ships Regular and Medium; the product's Bold face is built from
  # Medium, so the source step is named for the *master* it holds.
  srcCjk = weight: step "src-cjk" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      cp ${sources.perFamily.casual."Yozai-${cjkFor.${weight}.master}.ttf"} \
        $out/Yozai-${cjkFor.${weight}.master}.ttf
    '';
  };

  # --- latin-prepared -------------------------------------------------------
  # 600-unit Recursive cell → the 500 half cell, uniformly. No region axis: a
  # Japanese build would ask for these exact bytes.
  latinPrepared = weight: step "latin-prepared" { inherit family profile weight; } {
    buildCommand = ''
      mkdir -p $out
      python3 ${file "casual/scripts/prepare_latin.py"} \
        ${srcLatin weight}/RecursiveMonoCsl-${weight}.ttf \
        $out/RecursiveLatin-${weight}.ttf \
        --src-adv ${toString grid.latin_src_adv} \
        --en-adv ${toString grid.en_adv} \
        --uniform
    '';
  };

  # --- cjk-prepared ---------------------------------------------------------
  # No profile axis: stroking Yozai to match Recursive's ink is a property of
  # the two typefaces, not of whether the result is used for code or prose.
  cjkPrepared = weight: step "cjk-prepared" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      fontkit prepare-cjk \
        ${srcCjk weight}/Yozai-${cjkFor.${weight}.master}.ttf \
        $out/YozaiPrepared-${weight}.ttf \
        --embolden ${toString cjkFor.${weight}.embolden} \
        --slant-deg ${toString m.calibration.regular.slant_deg} \
        --pivot-y ${toString m.calibration.regular.slant_pivot_y}
    '';
  };

  # --- merged ---------------------------------------------------------------
  # The merge engine writes both faces from both pairs in one pass, so each
  # weight's derivation runs it and keeps its own face. That costs a second
  # merge and buys a per-weight cache entry — a Bold-only pin change stops
  # rebuilding Regular, which is the whole point of a weight axis.
  merged = weight: step "merged" { inherit family profile region weight; } {
    buildCommand = ''
      mkdir -p $out merged
      fontkit merge \
        --manifest ${manifest.file} \
        --profile ${profile} \
        --latin-regular ${latinPrepared "Regular"}/RecursiveLatin-Regular.ttf \
        --latin-bold ${latinPrepared "Bold"}/RecursiveLatin-Bold.ttf \
        --cjk-regular ${cjkPrepared "Regular"}/YozaiPrepared-Regular.ttf \
        --cjk-bold ${cjkPrepared "Bold"}/YozaiPrepared-Bold.ttf \
        --out-dir merged
      cp merged/${ps}-${weight}.ttf $out/
    '';
  };

  out = pkgs.runCommand "casual-out" { } ''
    mkdir -p $out
    ${lib.concatMapStringsSep "\n" (w: "cp ${merged w}/*.ttf $out/") weights}
    cp ${file "casual/licenses"}/OFL-Recursive.txt ${file "casual/licenses"}/OFL-Yozai.txt $out/
  '';

  # Dense profile: casual has always run the denser CJK sampling, which is also
  # the one that does not check OS/2.xAvgCharWidth.
  #
  # `--expect-half` replaces the inline python the old 05-verify.sh appended,
  # which asserted advance('A') == EN_ADV, advance('中') == CJK_ADV and that the
  # two were 2:1. The dense profile already proves the ratio across a far wider
  # CJK sample, so pinning the half cell is the only part that was adding
  # anything — and it is a flag, not a heredoc.
  verify = pkgs.runCommand "casual-verify"
    {
      nativeBuildInputs = [ support.pythonEnv ];
    }
    ''
      fontkit verify-2to1 --profile dense --expect-half ${toString grid.en_adv} ${out}/${ps}-*.ttf
      touch $out
    '';

  readme = pkgs.writeText "casual-README.txt" ''
    ${naming.family} @version@
    Derived from Recursive Mono Casual (${recursive.version}) and
    Yozai 悠哉 (${yozai.version}) under SIL OFL 1.1.
    Not an official ArrowType Recursive or LXGW product.

    Name recipe:
      Recursive = Recursive Mono Casual (Latin)
      Yozai     = 悠哉 (CJK handwriting)
      Dual      = 2:1 dual-width coding face

    Cell metrics: EN ${toString grid.en_adv} / CJK ${toString grid.cjk_adv} (strict 2:1)
    CJK embolden: Regular s=${toString m.calibration.regular.embolden} (Yozai ${cjkFor.Regular.master})
                  Bold    s=${toString m.calibration.bold.embolden} (Yozai ${cjkFor.Bold.master})
    Upstream pins: see casual/font.toml in the build repository.
  '';

in
{
  inherit out verify;

  # `nix build .#casual-coding-sc`. One entry because casual declares one cell.
  cells."${profile}-${region}" = out;

  steps = lib.listToAttrs (
    lib.concatMap
      (weight: [
        { name = "src-latin-${weight}"; value = srcLatin weight; }
        { name = "src-cjk-${weight}"; value = srcCjk weight; }
        { name = "latin-prepared-${weight}"; value = latinPrepared weight; }
        { name = "cjk-prepared-${weight}"; value = cjkPrepared weight; }
        { name = "merged-${weight}"; value = merged weight; }
      ])
      weights
  );

  release = {
    inherit family profile region readme verify;
    weight = "Regular";
    stem = naming.stem;
    fontDir = out;
    licenseDir = file "casual/licenses";
  };
}
