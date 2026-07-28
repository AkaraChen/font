# handwriting — Monaspace Radon NF (Latin) × LXGW WenKai 霞鹜文楷 (CJK).
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

  family = "handwriting";
  weights = [ "Regular" "Bold" ];

  ps = get "FAMILY_PS";
  familyName =
    let
      suffix = pins.pins.FAMILY_SUFFIX or "";
    in
    if suffix == "" then get "FAMILY_NAME" else "${get "FAMILY_NAME"} ${suffix}";

  cjkFor = {
    Regular = {
      master = get "WENKAI_FOR_REGULAR";
      embolden = get "CJK_EMBOLDEN_REGULAR";
    };
    Bold = {
      master = get "WENKAI_FOR_BOLD";
      embolden = get "CJK_EMBOLDEN_BOLD";
    };
  };

  srcLatin = weight: step "src-latin" { inherit family weight; } {
    buildCommand = ''
      mkdir -p $out
      cp ${sources.perFamily.handwriting."MonaspaceRadonNF-${weight}.otf"} \
        $out/MonaspaceRadonNF-${weight}.otf
    '';
  };

  # WenKai has no Bold; Medium backs both product faces (measured — see pins).
  srcCjk = weight: step "src-cjk" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      cp ${sources.perFamily.handwriting."LXGWWenKai-${cjkFor.${weight}.master}.ttf"} \
        $out/LXGWWenKai-${cjkFor.${weight}.master}.ttf
    '';
  };

  # Radon's 1240/2000 cell → narrow to 1111 (x only) → 90 % uniform → 500/1000.
  latinPrepared = weight: step "latin-prepared" { inherit family profile weight; } {
    buildCommand = ''
      mkdir -p $out
      python3 ${file "handwriting/scripts/prepare_latin.py"} \
        ${srcLatin weight}/MonaspaceRadonNF-${weight}.otf \
        $out/RadonLatin-${weight}.ttf \
        --src-upm ${get "SRC_UPM"} \
        --upm ${get "UPM"} \
        --src-adv ${get "LATIN_SRC_ADV"} \
        --narrow-adv ${get "LATIN_NARROW_ADV"} \
        --uniform-scale ${get "LATIN_UNIFORM_SCALE"} \
        --en-adv ${get "EN_ADV"}
    '';
  };

  cjkPrepared = weight: step "cjk-prepared" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      fontkit prepare-cjk \
        ${srcCjk weight}/LXGWWenKai-${cjkFor.${weight}.master}.ttf \
        $out/WenKaiSlanted-${weight}.ttf \
        --embolden ${cjkFor.${weight}.embolden} \
        --slant-deg ${get "CJK_SLANT_DEG"} \
        --pivot-y ${get "CJK_SLANT_PIVOT_Y"}
    '';
  };

  # Merge, then fold Monaspace's stylistic sets into default `calt`. Radon parks
  # essentially every coding ligature behind ss01–ss10, so an editor that only
  # flips `calt` shows none of them; 05-expand-ligatures.sh existed for that and
  # is one flag of the merge step now, not a script that reached into serif/.
  merged = weight: step "merged" { inherit family profile region weight; } {
    buildCommand = ''
      mkdir -p $out merged
      fontkit merge \
        --latin-regular ${latinPrepared "Regular"}/RadonLatin-Regular.ttf \
        --latin-bold ${latinPrepared "Bold"}/RadonLatin-Bold.ttf \
        --cjk-regular ${cjkPrepared "Regular"}/WenKaiSlanted-Regular.ttf \
        --cjk-bold ${cjkPrepared "Bold"}/WenKaiSlanted-Bold.ttf \
        --out-dir merged \
        --en-adv ${get "EN_ADV"} \
        --cjk-adv ${get "CJK_ADV"} \
        --family ${lib.escapeShellArg familyName} \
        --family-ps ${ps} \
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
      fontkit expand-ligatures --include ${get "LIGATURE_SETS"} $out/${ps}-${weight}.ttf
    '';
  };

  out = pkgs.runCommand "handwriting-out" { } ''
    mkdir -p $out
    ${lib.concatMapStringsSep "\n" (w: "cp ${merged w}/*.ttf $out/") weights}
    cp ${file "handwriting/licenses"}/OFL-Monaspace.txt \
       ${file "handwriting/licenses"}/OFL-LXGWWenKai.txt $out/
  '';

  # verify-features.py needs a real shaper to prove the ligatures fire, so this
  # runs on verifyEnv (uharfbuzz) rather than the build interpreter.
  verify = pkgs.runCommand "handwriting-verify"
    {
      nativeBuildInputs = [ support.verifyEnv ];
    }
    ''
      fontkit verify-2to1 --profile dense --check-nerd --check-eaw ${out}/${ps}-*.ttf
      python3 ${file "handwriting/scripts/verify-features.py"} \
        --expect-half ${get "EN_ADV"} ${out}/${ps}-*.ttf
      for font in ${out}/${ps}-*.ttf; do
        fontkit measure --font "$font" | tail -20
      done
      touch $out
    '';

  readme = pkgs.writeText "handwriting-README.txt" ''
    ${get "FAMILY_NAME"} @version@
    Derived from Monaspace Radon NF (${get "MONASPACE_RELEASE_TAG"}) and
    LXGW WenKai 霞鹜文楷 (${get "WENKAI_RELEASE_TAG"}) under SIL OFL 1.1.
    Not an official Monaspace / GitHub Next or LXGW product.

    Name recipe (same style as SarasaNZSSlab NFM):
      Radon    = Monaspace Radon (Latin, ligatures + OpenType features)
      WenKai   = 霞鹜文楷 (CJK, sheared ${get "CJK_SLANT_DEG"}° to Radon's lean)
      NFM      = Nerd Font Mono product (icons at one cell)

    Cell metrics: EN ${get "EN_ADV"} / CJK ${get "CJK_ADV"} (strict 2:1)
    Nerd icons:   from the upstream Monaspace Radon NF build, one cell each
    Ligatures:    Radon liga + calt (on by default), plus ss01–ss10 / cv** opt-in
    Upstream pins: see handwriting/pins.env in the build repository.
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
    licenseDir = file "handwriting/licenses";
  };
}
