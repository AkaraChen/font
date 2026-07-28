# rounded — Iosevka Curly ss20 (Latin) × Resource Han Rounded SC (CJK) + Nerd.
#
# Was: 01-fetch-sources.sh … 05-verify.sh / build.sh / common.sh /
#      package-release.sh (519 lines).
#
# 01-fetch-sources.sh is where the "look around and hope" pattern was most
# visible: `if command -v 7z … elif command -v 7za … else die`, then a
# `find | head -1` because "the RHR archive may drop files at top level or
# under a folder". p7zip is a build input now and the archive layout is pinned
# by its hash, so both questions are answered before the build starts.
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

  family = "rounded";
  weights = [ "Regular" "Bold" ];

  ps = get "FAMILY_PS";
  basePs = get "BASE_FAMILY_PS";
  mergeFamily =
    let
      suffix = pins.pins.FAMILY_SUFFIX or "";
    in
    if suffix == "" then get "BASE_FAMILY_NAME" else "${get "BASE_FAMILY_NAME"} ${suffix}";

  srcLatin = weight: step "src-latin" { inherit family weight; } {
    nativeBuildInputs = [ pkgs.unzip ];
    buildCommand = ''
      mkdir -p $out unpacked
      unzip -q ${sources.perFamily.rounded."PkgTTF-IosevkaCurly.zip"} \
        ${lib.escapeShellArg (get "IOSEVKA_TTF_${lib.toUpper weight}")} -d unpacked
      cp unpacked/${lib.escapeShellArg (get "IOSEVKA_TTF_${lib.toUpper weight}")} \
        $out/IosevkaCurly-${weight}.ttf
    '';
  };

  srcCjk = weight: step "src-cjk" { inherit family region weight; } {
    nativeBuildInputs = [ pkgs.p7zip ];
    buildCommand = ''
      mkdir -p $out unpacked
      7z x ${sources.perFamily.rounded."RHR-CN.7z"} -ounpacked -y > /dev/null
      cp "$(find unpacked -type f -name ${lib.escapeShellArg (get "RHR_TTF_${lib.toUpper weight}")})" \
        $out/RHR-${weight}.ttf
    '';
  };

  # RHR ships real Regular and Bold masters, so both pins are 0 and this step
  # copies. It exists anyway: without it a later pin change would have nowhere
  # to land except back inside the merge.
  cjkPrepared = weight: step "cjk-prepared" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      ${support.emboldenOrCopy {
        strength = get "CJK_EMBOLDEN_${lib.toUpper weight}";
        src = "${srcCjk weight}/RHR-${weight}.ttf";
        dst = "$out/RHR-${weight}-prepared.ttf";
      }}
    '';
  };

  merged = weight: step "merged" { inherit family profile region weight; } {
    buildCommand = ''
      mkdir -p $out merged
      python3 ${file "rounded/scripts/merge_rounded.py"} \
        --latin-regular ${srcLatin "Regular"}/IosevkaCurly-Regular.ttf \
        --latin-bold ${srcLatin "Bold"}/IosevkaCurly-Bold.ttf \
        --cjk-regular ${cjkPrepared "Regular"}/RHR-Regular-prepared.ttf \
        --cjk-bold ${cjkPrepared "Bold"}/RHR-Bold-prepared.ttf \
        --out-dir merged \
        --en-adv ${get "EN_ADV"} \
        --cjk-adv ${get "CJK_ADV"} \
        --latin-src-adv ${get "LATIN_SRC_ADV"} \
        --latin-src-upm ${get "LATIN_SRC_UPM"} \
        --latin-target-upm ${get "LATIN_TARGET_UPM"} \
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

  out = pkgs.runCommand "rounded-out" { } ''
    mkdir -p $out/nerd
    ${lib.concatMapStringsSep "\n" (w: "cp ${merged w}/*.ttf $out/") weights}
    ${lib.concatMapStringsSep "\n" (w: "cp ${nerd w}/*.ttf $out/nerd/") weights}
    cp ${file "rounded/licenses"}/OFL-Iosevka.txt \
       ${file "rounded/licenses"}/OFL-Resource-Han-Rounded.txt $out/
  '';

  verify = pkgs.runCommand "rounded-verify"
    {
      nativeBuildInputs = [ support.pythonEnv ];
    }
    ''
      fontkit verify-2to1 \
        --expect-half ${get "EN_ADV"} --check-nerd --check-eaw ${out}/nerd/${ps}-*.ttf
      touch $out
    '';

  readme = pkgs.writeText "rounded-README.txt" ''
    ${get "FAMILY_NAME"} @version@
    Derived from Iosevka Curly (ss20) + Resource Han Rounded SC (资源圆体) under SIL OFL 1.1.
    Nerd Font icons via font-patcher ${get "NERD_FONTS_PATCHER_VERSION"} (--complete --single-width-glyphs).
    Not an official Iosevka, Resource Han Rounded, or Nerd Fonts product.

    Name recipe (inheritance in the family name):
      Iosevka = Latin base
      Curly   = ss20 Curly Style package (not Slab/NSlab)
      RHR     = Resource Han Rounded SC
      NFM     = Nerd Font Mono
      (docs nickname: ${get "PRODUCT_NAME_ZH"})

    Cell metrics: EN ${get "EN_ADV"} / CJK ${get "CJK_ADV"} (strict 2:1)
    Mono flags:   post.isFixedPitch=1, PANOSE bProportion=9
    Icons:        Nerd complete set at half-cell advance
    EAW:          N/Na/H → half, W/F → full (ambiguous left alone by default)

    Install: copy the .ttf into your OS fonts directory.
    In terminals/IDEs pick family "${get "FAMILY_NAME"}".

    Upstream pins: see font.toml in the build repository.
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
    fontDir = pkgs.runCommand "rounded-release-fonts" { } ''
      mkdir -p $out
      ${lib.concatMapStringsSep "\n" (w: "cp ${nerd w}/*.ttf $out/") weights}
    '';
    licenseDir = file "rounded/licenses";
  };
}
