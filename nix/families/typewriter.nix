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
, pins
,
}:

let
  inherit (support) step file profile region patcher;
  get = pins.get;

  family = "typewriter";
  weights = [ "Regular" "Bold" ];

  ps = get "FAMILY_PS";
  basePs = get "BASE_FAMILY_PS";
  mergeFamily =
    let
      suffix = pins.pins.FAMILY_SUFFIX or "";
    in
    if suffix == "" then get "BASE_FAMILY_NAME" else "${get "BASE_FAMILY_NAME"} ${suffix}";

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
        ${lib.escapeShellArg (get "ZHUQUE_TTF_IN_ZIP")} -d unpacked
      cp unpacked/${lib.escapeShellArg (get "ZHUQUE_TTF_IN_ZIP")} \
        $out/ZhuqueFangsong-Regular.ttf
    '';
  };

  cjkPrepared = weight: step "cjk-prepared" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      ${support.emboldenOrCopy {
        strength = get "CJK_EMBOLDEN_${lib.toUpper weight}";
        src = "${srcCjk weight}/ZhuqueFangsong-Regular.ttf";
        dst = "$out/ZhuqueFangsong-${weight}-prepared.ttf";
      }}
    '';
  };

  merged = weight: step "merged" { inherit family profile region weight; } {
    buildCommand = ''
      mkdir -p $out merged
      python3 ${file "typewriter/scripts/merge_typewriter.py"} \
        --latin-regular ${srcLatin "Regular"}/CourierPrime-Regular.ttf \
        --latin-bold ${srcLatin "Bold"}/CourierPrime-Bold.ttf \
        --cjk-regular ${cjkPrepared "Regular"}/ZhuqueFangsong-Regular-prepared.ttf \
        --cjk-bold ${cjkPrepared "Bold"}/ZhuqueFangsong-Bold-prepared.ttf \
        --out-dir merged \
        --en-adv ${get "EN_ADV"} \
        --cjk-adv ${get "CJK_ADV"} \
        --latin-src-adv ${get "LATIN_SRC_ADV"} \
        --latin-src-upm ${get "COURIER_PRIME_SRC_UPM"} \
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
        --expect-half ${get "EN_ADV"} --check-nerd --check-eaw ${out}/nerd/${ps}-*.ttf
      touch $out
    '';

  readme = pkgs.writeText "typewriter-README.txt" ''
    ${get "FAMILY_NAME"} @version@
    Derived from Courier Prime + Zhuque Fangsong 朱雀仿宋 (${get "ZHUQUE_RELEASE_TAG"})
    under SIL OFL 1.1.
    Nerd Font icons via ${get "NERD_FONTS_TAG"} FontPatcher (--complete --single-width-glyphs).
    Not an official Courier Prime, Triones Type, or Nerd Fonts product.

    Name recipe:
      CourierPrime = Courier Prime (Latin slab mono)
      Zhuque       = 朱雀仿宋 Zhuque Fangsong (CJK)
      NFM          = Nerd Font Mono

    Cell metrics: EN ${get "EN_ADV"} / CJK ${get "CJK_ADV"} (strict 2:1)
    CJK embolden: Regular s=${get "CJK_EMBOLDEN_REGULAR"} / Bold s=${get "CJK_EMBOLDEN_BOLD"}
                  (Zhuque ships one weight; both faces are stem-matched to Courier Prime)
    Mono flags:   post.isFixedPitch=1, PANOSE bProportion=9
    Icons:        Nerd complete set at half-cell advance

    Install: copy the .ttf into your OS fonts directory.
    In terminals/IDEs pick family "${get "FAMILY_NAME"}".

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
    fontDir = pkgs.runCommand "typewriter-release-fonts" { } ''
      mkdir -p $out
      ${lib.concatMapStringsSep "\n" (w: "cp ${nerd w}/*.ttf $out/") weights}
    '';
    licenseDir = file "typewriter/licenses";
  };
}
