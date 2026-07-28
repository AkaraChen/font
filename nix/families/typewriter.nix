# typewriter — Courier Prime (Latin slab mono) × Zhuque Fangsong 朱雀仿宋 (CJK).
#
# Was: 01-fetch-sources.sh … 05-verify.sh / build.sh / common.sh /
#      package-release.sh (459 lines).
#
# Zhuque ships one weight. Both product faces are stroked from that single
# master at different strengths, which is why `src-cjk` is the same store path
# for Regular and Bold while `cjk-prepared` is not — the weight axis starts
# where the weight difference actually starts.
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

  family = "typewriter";
  weights = map support.weightName m.build.weights;

  ps = naming.ps;
  basePs = naming.base_ps;

  srcLatin = weight: step "src-latin" { inherit family weight; } {
    buildCommand = ''
      mkdir -p $out
      cp ${sources.perFamily.typewriter."CourierPrime-${weight}.ttf"} \
        $out/CourierPrime-${weight}.ttf
    '';
  };

  srcCjk = weight: step "src-cjk" { inherit family region weight; } {
    nativeBuildInputs = [ pkgs.unzip ];
    buildCommand = ''
      mkdir -p $out unpacked
      unzip -q ${sources.perFamily.typewriter."ZhuqueFangsong.zip"} \
        ${lib.escapeShellArg m.options.zhuque_ttf_in_zip} -d unpacked
      cp unpacked/${lib.escapeShellArg m.options.zhuque_ttf_in_zip} \
        $out/ZhuqueFangsong-Regular.ttf
    '';
  };

  cjkPrepared = weight: step "cjk-prepared" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      ${support.emboldenOrCopy {
        strength = toString m.calibration.${lib.toLower weight}.embolden;
        src = "${srcCjk weight}/ZhuqueFangsong-Regular.ttf";
        dst = "$out/ZhuqueFangsong-${weight}-prepared.ttf";
      }}
    '';
  };

  merged = weight: step "merged" { inherit family profile region weight; } {
    buildCommand = ''
      mkdir -p $out merged
      fontkit merge \
        --manifest ${manifest.file} \
        --profile ${profile} \
        --latin-regular ${srcLatin "Regular"}/CourierPrime-Regular.ttf \
        --latin-bold ${srcLatin "Bold"}/CourierPrime-Bold.ttf \
        --cjk-regular ${cjkPrepared "Regular"}/ZhuqueFangsong-Regular-prepared.ttf \
        --cjk-bold ${cjkPrepared "Bold"}/ZhuqueFangsong-Bold-prepared.ttf \
        --out-dir merged

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

  out = pkgs.runCommand "typewriter-out" { } ''
    mkdir -p $out/nerd
    ${lib.concatMapStringsSep "\n" (w: "cp ${merged w}/*.ttf $out/") weights}
    ${lib.concatMapStringsSep "\n" (w: "cp ${nerd w}/*.ttf $out/nerd/") weights}
    cp ${file "typewriter/licenses"}/OFL-CourierPrime.txt \
       ${file "typewriter/licenses"}/OFL-Zhuque.txt $out/
  '';

  verify = pkgs.runCommand "typewriter-verify"
    {
      nativeBuildInputs = [ support.pythonEnv ];
    }
    ''
      fontkit verify-2to1 \
        --expect-half ${toString grid.en_adv} --check-nerd --check-eaw ${out}/nerd/${ps}-*.ttf
      touch $out
    '';

  readme = pkgs.writeText "typewriter-README.txt" ''
    ${naming.family} @version@
    Derived from Courier Prime + Zhuque Fangsong 朱雀仿宋 (${m.sources.zhuque.version})
    under SIL OFL 1.1.
    Nerd Font icons via font-patcher ${m.nerd.version} (--complete --single-width-glyphs).
    Not an official Courier Prime, Triones Type, or Nerd Fonts product.

    Name recipe:
      CourierPrime = Courier Prime (Latin slab mono)
      Zhuque       = 朱雀仿宋 Zhuque Fangsong (CJK)
      NFM          = Nerd Font Mono

    Cell metrics: EN ${toString grid.en_adv} / CJK ${toString grid.cjk_adv} (strict 2:1)
    CJK embolden: Regular s=${toString m.calibration.regular.embolden} / Bold s=${toString m.calibration.bold.embolden}
                  (Zhuque ships one weight; both faces are stem-matched to Courier Prime)
    Mono flags:   post.isFixedPitch=1, PANOSE bProportion=9
    Icons:        Nerd complete set at half-cell advance

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
    fontDir = pkgs.runCommand "typewriter-release-fonts" { } ''
      mkdir -p $out
      ${lib.concatMapStringsSep "\n" (w: "cp ${nerd w}/*.ttf $out/") weights}
    '';
    licenseDir = file "typewriter/licenses";
  };
}
