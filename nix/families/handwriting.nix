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
, manifest
,
}:

let
  inherit (support) step file profile region;
  m = manifest.data;
  inherit (m) grid naming;
  metrics = m.metrics.coding;

  family = "handwriting";
  weights = map support.weightName m.build.weights;

  ps = naming.ps;
  familyName =
    if (naming.suffix or "") == "" then
      naming.family
    else
      "${naming.family} ${naming.suffix}";

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
        ${srcCjk weight}/LXGWWenKai-${cjkFor.${weight}.master}.ttf \
        $out/WenKaiSlanted-${weight}.ttf \
        --embolden ${toString cjkFor.${weight}.embolden} \
        --slant-deg ${toString m.calibration.regular.slant_deg} \
        --pivot-y ${toString m.calibration.regular.slant_pivot_y}
    '';
  };

  # Merge, then fold Monaspace's stylistic sets into default `calt`. Radon parks
  # essentially every coding ligature behind ss01–ss10, so an editor that only
  # flips `calt` shows none of them; 05-expand-ligatures.sh existed for that and
  # is one flag of the merge step now, not a script that reached into serif/.
  merged = weight: step "merged" { inherit family profile region weight; } {
    buildCommand = ''
      mkdir -p $out merged
      fontkit merge-radon-wenkai \
        --latin-regular ${latinPrepared "Regular"}/RadonLatin-Regular.ttf \
        --latin-bold ${latinPrepared "Bold"}/RadonLatin-Bold.ttf \
        --cjk-regular ${cjkPrepared "Regular"}/WenKaiSlanted-Regular.ttf \
        --cjk-bold ${cjkPrepared "Bold"}/WenKaiSlanted-Bold.ttf \
        --out-dir merged \
        --en-adv ${toString grid.en_adv} \
        --cjk-adv ${toString grid.cjk_adv} \
        --family ${lib.escapeShellArg familyName} \
        --family-ps ${ps} \
        --slant-deg ${toString m.calibration.regular.slant_deg} \
        --hhea-ascent ${toString metrics.hhea_ascent} \
        --hhea-descent ${toString metrics.hhea_descent} \
        --hhea-line-gap ${toString metrics.hhea_line_gap} \
        --os2-typo-ascender ${toString metrics.os2_typo_ascender} \
        --os2-typo-descender ${toString metrics.os2_typo_descender} \
        --os2-typo-line-gap ${toString metrics.os2_typo_line_gap} \
        --os2-win-ascent ${toString metrics.os2_win_ascent} \
        --os2-win-descent ${toString metrics.os2_win_descent}

      cp merged/${ps}-${weight}.ttf $out/
      fontkit expand-ligatures \
        --include ${lib.concatStringsSep "," m.options.ligature_sets} \
        $out/${ps}-${weight}.ttf
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
        --expect-half ${toString grid.en_adv} ${out}/${ps}-*.ttf
      # Informational, like sans'. See the note there about measure.py and
      # all-off-curve contours.
      for font in ${out}/${ps}-*.ttf; do
        fontkit measure --font "$font" | tail -20 || true
      done
      touch $out
    '';

  readme = pkgs.writeText "handwriting-README.txt" ''
    ${naming.family} @version@
    Derived from Monaspace Radon NF (${m.sources.monaspace.version}) and
    LXGW WenKai 霞鹜文楷 (${m.sources.wenkai.version}) under SIL OFL 1.1.
    Not an official Monaspace / GitHub Next or LXGW product.

    Name recipe (same style as SarasaNZSSlab NFM):
      Radon    = Monaspace Radon (Latin, ligatures + OpenType features)
      WenKai   = 霞鹜文楷 (CJK, sheared ${toString m.calibration.regular.slant_deg}° to Radon's lean)
      NFM      = Nerd Font Mono product (icons at one cell)

    Cell metrics: EN ${toString grid.en_adv} / CJK ${toString grid.cjk_adv} (strict 2:1)
    Nerd icons:   from the upstream Monaspace Radon NF build, one cell each
    Ligatures:    Radon liga + calt (on by default), plus ss01–ss10 / cv** opt-in
    Upstream pins: see handwriting/font.toml in the build repository.
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
    stem = naming.stem;
    fontDir = out;
    licenseDir = file "handwriting/licenses";
  };
}
