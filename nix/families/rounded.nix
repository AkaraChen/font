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
, manifest
,
}:

let
  inherit (support) step file profile region patcher;
  m = manifest.data;
  inherit (m) grid naming;
  metrics = m.metrics.coding;

  family = "rounded";
  weights = map support.weightName m.build.weights;

  ps = naming.ps;
  basePs = naming.base_ps;
  mergeFamily =
    if naming.suffix == "" then naming.base_family else "${naming.base_family} ${naming.suffix}";

  srcLatin = weight: step "src-latin" { inherit family weight; } {
    nativeBuildInputs = [ pkgs.unzip ];
    buildCommand = ''
      mkdir -p $out unpacked
      unzip -q ${sources.perFamily.rounded."PkgTTF-IosevkaCurly.zip"} \
        ${lib.escapeShellArg m.options.${"iosevka_ttf_${lib.toLower weight}"}} -d unpacked
      cp unpacked/${lib.escapeShellArg m.options.${"iosevka_ttf_${lib.toLower weight}"}} \
        $out/IosevkaCurly-${weight}.ttf
    '';
  };

  srcCjk = weight: step "src-cjk" { inherit family region weight; } {
    nativeBuildInputs = [ pkgs.p7zip ];
    buildCommand = ''
      mkdir -p $out unpacked
      7z x ${sources.perFamily.rounded."RHR-CN.7z"} -ounpacked -y > /dev/null
      cp "$(find unpacked -type f -name ${lib.escapeShellArg m.options.${"rhr_ttf_${lib.toLower weight}"}})" \
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
        strength = toString m.calibration.${lib.toLower weight}.embolden;
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
        --en-adv ${toString grid.en_adv} \
        --cjk-adv ${toString grid.cjk_adv} \
        --latin-src-adv ${toString grid.latin_src_adv} \
        --latin-src-upm ${toString grid.latin_src_upm} \
        --latin-target-upm ${toString grid.latin_target_upm} \
        --family ${lib.escapeShellArg mergeFamily} \
        --family-ps ${basePs} \
        --hhea-ascent ${toString metrics.hhea_ascent} \
        --hhea-descent ${toString metrics.hhea_descent} \
        --hhea-line-gap ${toString metrics.hhea_line_gap} \
        --os2-typo-ascender ${toString metrics.os2_typo_ascender} \
        --os2-typo-descender ${toString metrics.os2_typo_descender} \
        --os2-typo-line-gap ${toString metrics.os2_typo_line_gap} \
        --os2-win-ascent ${toString metrics.os2_win_ascent} \
        --os2-win-descent ${toString metrics.os2_win_descent}

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
        --family ${lib.escapeShellArg naming.family} \
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
        --expect-half ${toString grid.en_adv} --check-nerd --check-eaw ${out}/nerd/${ps}-*.ttf
      touch $out
    '';

  readme = pkgs.writeText "rounded-README.txt" ''
    ${naming.family} @version@
    Derived from Iosevka Curly (ss20) + Resource Han Rounded SC (资源圆体) under SIL OFL 1.1.
    Nerd Font icons via font-patcher ${m.nerd.version} (--complete --single-width-glyphs).
    Not an official Iosevka, Resource Han Rounded, or Nerd Fonts product.

    Name recipe (inheritance in the family name):
      Iosevka = Latin base
      Curly   = ss20 Curly Style package (not Slab/NSlab)
      RHR     = Resource Han Rounded SC
      NFM     = Nerd Font Mono
      (docs nickname: ${naming.product_name_zh})

    Cell metrics: EN ${toString grid.en_adv} / CJK ${toString grid.cjk_adv} (strict 2:1)
    Mono flags:   post.isFixedPitch=1, PANOSE bProportion=9
    Icons:        Nerd complete set at half-cell advance
    EAW:          N/Na/H → half, W/F → full (ambiguous left alone by default)

    Install: copy the .ttf into your OS fonts directory.
    In terminals/IDEs pick family "${naming.family}".

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
