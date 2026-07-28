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
, pins
,
}:

let
  inherit (support) step file profile region;
  get = pins.get;

  family = "casual";
  weights = [ "Regular" "Bold" ];

  ps = get "FAMILY_PS";
  familyName =
    let
      suffix = pins.pins.FAMILY_SUFFIX or "";
    in
    if suffix == "" then get "FAMILY_NAME" else "${get "FAMILY_NAME"} ${suffix}";

  # Which Yozai master backs each product face, and how hard to stroke it.
  # Measured, not guessed — see casual/pins.env and tools/calibrate-cjk-weight.py.
  cjkFor = {
    Regular = {
      master = get "YOZAI_FOR_REGULAR";
      embolden = get "CJK_EMBOLDEN_REGULAR";
    };
    Bold = {
      master = get "YOZAI_FOR_BOLD";
      embolden = get "CJK_EMBOLDEN_BOLD";
    };
  };

  # --- src ------------------------------------------------------------------
  srcLatin = weight: step "src-latin" { inherit family weight; } {
    nativeBuildInputs = [ pkgs.unzip ];
    buildCommand = ''
      mkdir -p $out unpacked
      unzip -q ${sources.perFamily.casual."ArrowType-Recursive.zip"} \
        ${lib.escapeShellArg (get "RECURSIVE_TTF_${lib.toUpper weight}")} -d unpacked
      cp unpacked/${lib.escapeShellArg (get "RECURSIVE_TTF_${lib.toUpper weight}")} \
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
        --src-adv ${get "LATIN_SRC_ADV"} \
        --en-adv ${get "EN_ADV"} \
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
        --embolden ${cjkFor.${weight}.embolden} \
        --slant-deg ${get "CJK_SLANT_DEG"} \
        --pivot-y ${get "CJK_SLANT_PIVOT_Y"}
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
        --latin-regular ${latinPrepared "Regular"}/RecursiveLatin-Regular.ttf \
        --latin-bold ${latinPrepared "Bold"}/RecursiveLatin-Bold.ttf \
        --cjk-regular ${cjkPrepared "Regular"}/YozaiPrepared-Regular.ttf \
        --cjk-bold ${cjkPrepared "Bold"}/YozaiPrepared-Bold.ttf \
        --out-dir merged \
        --en-adv ${get "EN_ADV"} \
        --cjk-adv ${get "CJK_ADV"} \
        --family ${lib.escapeShellArg familyName} \
        --family-ps ${ps} \
        --version ${pins.pins.PRODUCT_VERSION or "0.1.0"} \
        --slant-deg ${get "CJK_SLANT_DEG"} \
        --hhea-ascent ${get "HHEA_ASCENT"} \
        --hhea-descent ${get "HHEA_DESCENT"} \
        --hhea-line-gap ${get "HHEA_LINE_GAP"} \
        --os2-typo-ascender ${get "OS2_TYPO_ASCENDER"} \
        --os2-typo-descender ${get "OS2_TYPO_DESCENDER"} \
        --os2-typo-line-gap ${get "OS2_TYPO_LINE_GAP"} \
        --os2-win-ascent ${get "OS2_WIN_ASCENT"} \
        --os2-win-descent ${get "OS2_WIN_DESCENT"}
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
      fontkit verify-2to1 --profile dense --expect-half ${get "EN_ADV"} ${out}/${ps}-*.ttf
      touch $out
    '';

  readme = pkgs.writeText "casual-README.txt" ''
    ${get "FAMILY_NAME"} @version@
    Derived from Recursive Mono Casual (${get "RECURSIVE_RELEASE_TAG"}) and
    Yozai 悠哉 (${get "YOZAI_RELEASE_TAG"}) under SIL OFL 1.1.
    Not an official ArrowType Recursive or LXGW product.

    Name recipe:
      Recursive = Recursive Mono Casual (Latin)
      Yozai     = 悠哉 (CJK handwriting)
      Dual      = 2:1 dual-width coding face

    Cell metrics: EN ${get "EN_ADV"} / CJK ${get "CJK_ADV"} (strict 2:1)
    CJK embolden: Regular s=${get "CJK_EMBOLDEN_REGULAR"} (Yozai ${get "YOZAI_FOR_REGULAR"})
                  Bold    s=${get "CJK_EMBOLDEN_BOLD"} (Yozai ${get "YOZAI_FOR_BOLD"})
    Upstream pins: see casual/pins.env in the build repository.
  '';

in
{
  inherit out verify;

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
    stem = get "PRODUCT_STEM";
    fontDir = out;
    licenseDir = file "casual/licenses";
  };
}
