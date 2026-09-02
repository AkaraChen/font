# work — CaskaydiaCove Nerd Font Mono (Latin + icons) × Alibaba PuHuiTi 3.0 (CJK).
#
# Pre-patched Nerd donor, three weights, no second font-patcher pass. The Latin
# cell is Cascadia's 1200/2048 scaled onto 500/1000; CJK stems are matched per
# weight (Bold takes PuHuiTi SemiBold, measured).
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
  naming = support.namingFor m profile region;

  family = "work";
  weights = map support.weightName m.build.weights;

  ps = naming.ps;

  cjkFor = weight: {
    master = m.calibration.${lib.toLower weight}.source_weight;
    inherit (m.calibration.${lib.toLower weight}) embolden;
  };

  latinFile = weight: m.sources.cascadia.artifacts.${lib.toLower weight}.file;
  cjkFile = weight: m.sources.puhuiti.artifacts.${(cjkFor weight).master}.file;

  srcLatin = weight: step "src-latin" { inherit family profile weight; } {
    buildCommand = ''
      mkdir -p $out
      cp ${sources.perFamily.work.${latinFile weight}} $out/${latinFile weight}
    '';
  };

  srcCjk = weight: step "src-cjk" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      cp ${sources.perFamily.work.${cjkFile weight}} $out/${cjkFile weight}
    '';
  };

  latinPrepared = weight: step "latin-prepared" { inherit family profile weight; } {
    buildCommand = ''
      mkdir -p $out
      python3 ${file "work/scripts/prepare_latin.py"} \
        ${srcLatin weight}/${latinFile weight} \
        $out/CascadiaLatin-${weight}.ttf \
        --upm ${toString grid.upm} \
        --en-adv ${toString grid.en_adv}
    '';
  };

  cjkPrepared = weight: step "cjk-prepared" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      fontkit prepare-cjk \
        ${srcCjk weight}/${cjkFile weight} \
        $out/PuHuiTiPrepared-${weight}.ttf \
        --embolden ${toString (cjkFor weight).embolden} \
        --slant-deg 0 \
        --pivot-y 375
    '';
  };

  merged = weight: step "merged" { inherit family profile region weight; } {
    buildCommand = ''
      mkdir -p $out merged
      fontkit merge \
        --manifest ${manifest.file} \
        --profile ${profile} \
        --weight ${weight} \
        --latin ${latinPrepared weight}/CascadiaLatin-${weight}.ttf \
        --cjk ${cjkPrepared weight}/PuHuiTiPrepared-${weight}.ttf \
        --out-dir merged

      cp merged/${ps}-${weight}.ttf $out/
    '';
  };

  declaredFormats = (lib.head (support.cellsOf m)).formats;
  formats = support.extraFormats declaredFormats;
  converted = weight: format: support.convert {
    inherit family profile region weight format;
    src = merged weight;
  };
  copyFormats = weight: dest:
    lib.concatMapStringsSep "\n"
      (format: "cp ${converted weight format}/*.${format} ${dest}")
      formats;

  out = pkgs.runCommand "work-out" { } ''
    mkdir -p $out
    ${lib.concatMapStringsSep "\n" (w: ''
      cp ${merged w}/*.ttf $out/
      ${copyFormats w "$out/"}
    '') weights}
    cp ${file "work/licenses"}/OFL-CascadiaCode.txt \
       ${file "work/licenses"}/Alibaba-PuHuiTi.txt $out/
  '';

  verify = pkgs.runCommand "work-verify"
    {
      nativeBuildInputs = [ support.pythonEnv ];
    }
    ''
      fontkit verify-2to1 --profile dense --expect-half ${toString grid.en_adv} \
        --check-nerd --check-eaw ${out}/${ps}-*.ttf
      python3 ${file "work/scripts/verify-product.py"} \
        --expect-half ${toString grid.en_adv} ${out}/${ps}-*.ttf
      fontkit verify-formats ${out}
      touch $out
    '';

  readme = pkgs.writeText "work-README.txt" ''
    ${naming.family} @version@
    Latin / icons: CaskaydiaCove Nerd Font Mono (Nerd Fonts ${m.sources.cascadia.version}),
    SIL OFL 1.1, derived from Cascadia Code.
    CJK: Alibaba PuHuiTi 3.0 (${m.sources.puhuiti.version}), Alibaba's own legal
    notice — not OFL. See Alibaba-PuHuiTi.txt.
    Not an official Microsoft Cascadia, Nerd Fonts, or Alibaba product.

    Name recipe:
      Work  = Cascadia Code Latin × 阿里巴巴普惠体 CJK
      SC    = Simplified Chinese, Level 1+2
      NFM   = Nerd Font Mono (icons from the pre-patched zip, one cell each)

    Cell metrics: EN ${toString grid.en_adv} / CJK ${toString grid.cjk_adv} (strict 2:1)
    CJK pairing:  Light  PuHuiTi Light s=${toString m.calibration.light.embolden}
                  Regular PuHuiTi Regular s=${toString m.calibration.regular.embolden}
                  Bold    PuHuiTi SemiBold s=${toString m.calibration.bold.embolden}
    Weights:      Light, Regular, Bold
    Formats:      TTF and WOFF2

    Upstream pins: see work/font.toml in the build repository.
  '';

in
{
  inherit out verify;

  cells."${profile}-${region}" = out;

  steps = lib.listToAttrs (
    lib.concatMap
      (weight: [
        { name = "src-latin-${weight}"; value = srcLatin weight; }
        { name = "src-cjk-${weight}"; value = srcCjk weight; }
        { name = "latin-prepared-${weight}"; value = latinPrepared weight; }
        { name = "cjk-prepared-${weight}"; value = cjkPrepared weight; }
        { name = "merged-${weight}"; value = merged weight; }
      ]
      ++ map
        (format: { name = "packaged-${weight}-${format}"; value = converted weight format; })
        formats)
      weights
  );

  release = {
    inherit family profile region readme verify;
    formats = declaredFormats;
    weight = "Regular";
    stem = naming.stem;
    fontDir = out;
    licenseDir = file "work/licenses";
  };
}
