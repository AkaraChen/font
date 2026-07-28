# sans — Lilex (Latin) × IBM Plex Sans SC (CJK) + Nerd Font Mono.
#
# Was: 01-fetch-sources.sh / 02-merge.sh / 03-nerd-patch.sh / 04-verify.sh /
#      build.sh / common.sh / package-release.sh (532 lines).
#
# 02-merge.sh had the worst of the cross-family reaches: `04-verify.sh:48` did
# `sys.path.insert(0, os.environ["SERIF_TOOLS"])` to borrow serif's measuring
# code, so a change under serif/ could move this product's stroke report without
# anyone touching sans/. Phase 2 made that `fontkit.measure`; this step can no
# longer see serif at all.
{ pkgs
, lib
, support
, sources
, pins
,
}:

let
  inherit (support) step file profile region patcher;
  get = pins.get;

  family = "sans";
  weights = [ "Regular" "Bold" ];

  ps = get "FAMILY_PS";
  basePs = get "BASE_FAMILY_PS";
  mergeFamily =
    let
      suffix = pins.pins.FAMILY_SUFFIX or "";
    in
    if suffix == "" then get "BASE_FAMILY_NAME" else "${get "BASE_FAMILY_NAME"} ${suffix}";

  emboldenFor = weight: get "CJK_EMBOLDEN_${lib.toUpper weight}";

  srcLatin = weight: step "src-latin" { inherit family weight; } {
    nativeBuildInputs = [ pkgs.unzip ];
    buildCommand = ''
      mkdir -p $out unpacked
      unzip -q ${sources.perFamily.sans."Lilex.zip"} \
        ${lib.escapeShellArg (get "LILEX_TTF_${lib.toUpper weight}")} -d unpacked
      cp unpacked/${lib.escapeShellArg (get "LILEX_TTF_${lib.toUpper weight}")} \
        $out/Lilex-${weight}.ttf
    '';
  };

  srcCjk = weight: step "src-cjk" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      cp ${sources.perFamily.sans."IBMPlexSansSC-${weight}.ttf"} \
        $out/IBMPlexSansSC-${weight}.ttf
    '';
  };

  # Plex Sans SC masters read light next to Lilex once the Latin is compressed
  # to the 550 cell; the embolden closes that gap without swapping weight
  # masters. Strengths are measured — sans/scripts/calibrate-stroke.sh.
  cjkPrepared = weight: step "cjk-prepared" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      ${support.emboldenOrCopy {
        strength = emboldenFor weight;
        src = "${srcCjk weight}/IBMPlexSansSC-${weight}.ttf";
        dst = "$out/IBMPlexSansSC-${weight}-weight.ttf";
      }}
    '';
  };

  # Latin scaling happens inside merge_plex.py, so sans has no latin-prepared
  # step of its own — Phase 5 is where the merge engines get split apart.
  merged = weight: step "merged" { inherit family profile region weight; } {
    buildCommand = ''
      mkdir -p $out merged
      python3 ${file "sans/scripts/merge_plex.py"} \
        --latin-regular ${srcLatin "Regular"}/Lilex-Regular.ttf \
        --latin-bold ${srcLatin "Bold"}/Lilex-Bold.ttf \
        --sc-regular ${cjkPrepared "Regular"}/IBMPlexSansSC-Regular-weight.ttf \
        --sc-bold ${cjkPrepared "Bold"}/IBMPlexSansSC-Bold-weight.ttf \
        --out-dir merged \
        --en-adv ${get "EN_ADV"} \
        --cjk-adv ${get "CJK_ADV"} \
        --latin-src-adv ${get "LILEX_SRC_ADV"} \
        --family ${lib.escapeShellArg mergeFamily} \
        --family-ps ${basePs} \
        --hhea-ascent ${get "HHEA_ASCENT"} \
        --hhea-descent ${get "HHEA_DESCENT"} \
        --hhea-line-gap ${get "HHEA_LINE_GAP"} \
        --os2-typo-ascender ${get "OS2_TYPO_ASCENDER"} \
        --os2-typo-descender ${get "OS2_TYPO_DESCENDER"} \
        --os2-typo-line-gap ${get "OS2_TYPO_LINE_GAP"} \
        --os2-win-ascent ${get "OS2_WIN_ASCENT"} \
        --os2-win-descent ${get "OS2_WIN_DESCENT"}

      cp merged/${basePs}-${weight}.ttf $out/
      # Terminals size cells from Unicode EAW, not from font metrics. Geometric
      # fit — there is no Sarasa Term donor on this 550 grid.
      fontkit narrow-symbol-widths --no-donor $out/${basePs}-${weight}.ttf
      fontkit fix-terminal-metrics $out/${basePs}-${weight}.ttf
    '';
  };

  nerd = weight: step "nerd" { inherit family region weight; } {
    nativeBuildInputs = [ support.fontforge ];
    buildCommand = ''
      export HOME=$TMPDIR
      mkdir -p $out
      fontkit nerd-patch \
        --patcher ${patcher} \
        --out $out \
        --family ${lib.escapeShellArg (get "FAMILY_NAME")} \
        --family-ps ${ps} \
        --narrow-symbols \
        ${merged weight}/*.ttf
    '';
  };

  out = pkgs.runCommand "sans-out" { } ''
    mkdir -p $out/nerd
    ${lib.concatMapStringsSep "\n" (w: "cp ${merged w}/*.ttf $out/") weights}
    ${lib.concatMapStringsSep "\n" (w: "cp ${nerd w}/*.ttf $out/nerd/") weights}
    cp ${file "sans/licenses"}/OFL-Lilex.txt ${file "sans/licenses"}/OFL-IBM-Plex.txt $out/
  '';

  verify = pkgs.runCommand "sans-verify"
    {
      nativeBuildInputs = [ support.verifyEnv ];
    }
    ''
      fontkit verify-2to1 \
        --expect-half ${get "EN_ADV"} --check-nerd --check-eaw ${out}/nerd/${ps}-*.ttf
      python3 ${file "sans/scripts/verify-features.py"} ${out}/nerd/${ps}-*.ttf

      # Informational: confirms Latin and CJK ended up at the same optical
      # weight after the embolden. Same measure path calibrate-stroke.sh uses.
      for font in ${out}/nerd/${ps}-*.ttf; do
        echo "==> $(basename "$font")"
        fontkit measure --font "$font" | tail -20
      done
      touch $out
    '';

  readme = pkgs.writeText "sans-README.txt" ''
    ${get "FAMILY_NAME"} @version@
    Derived from Lilex + IBM Plex Sans SC under SIL OFL 1.1.
    Nerd Font icons via ${get "NERD_FONTS_TAG"} FontPatcher (--complete --single-width-glyphs).
    Not an official Lilex, IBM, or Nerd Fonts product.

    Name recipe (same style as SarasaNZSSlab NFM):
      Lilex  = Lilex Latin / programming (ligatures + OT features preserved)
      SansSC = Plex Sans SC CJK
      NFM    = Nerd Font Mono

    Cell metrics: EN ${get "EN_ADV"} / CJK ${get "CJK_ADV"} (strict 2:1)
    Mono flags:   post.isFixedPitch=1, PANOSE bProportion=9
    Icons:        Nerd complete set at half-cell advance
    EAW:          N/Na/H → half, W/F → full (ambiguous left alone by default)

    Install: copy the .ttf into your OS fonts directory.
    In terminals/IDEs pick family "${get "FAMILY_NAME"}" and enable font ligatures.

    Upstream pins: see pins.env in the build repository.
  '';

in
{
  inherit out verify;

  steps = lib.listToAttrs (
    lib.concatMap
      (weight: [
        { name = "src-latin-${weight}"; value = srcLatin weight; }
        { name = "src-cjk-${weight}"; value = srcCjk weight; }
        { name = "cjk-prepared-${weight}"; value = cjkPrepared weight; }
        { name = "merged-${weight}"; value = merged weight; }
        { name = "nerd-${weight}"; value = nerd weight; }
      ])
      weights
  );

  release = {
    inherit family profile region readme verify;
    weight = "Regular";
    stem = ps;
    fontDir = pkgs.runCommand "sans-release-fonts" { } ''
      mkdir -p $out
      ${lib.concatMapStringsSep "\n" (w: "cp ${nerd w}/*.ttf $out/") weights}
    '';
    licenseDir = file "sans/licenses";
  };
}
