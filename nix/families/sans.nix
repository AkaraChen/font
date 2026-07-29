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
, manifest
,
}:

let
  inherit (support) step file profile region patcher;
  m = manifest.data;
  inherit (m) grid naming;

  family = "sans";
  weights = map support.weightName m.build.weights;

  ps = naming.ps;
  basePs = naming.base_ps;

  emboldenFor = weight: toString m.calibration.${lib.toLower weight}.embolden;

  srcLatin = weight: step "src-latin" { inherit family profile weight; } {
    nativeBuildInputs = [ pkgs.unzip ];
    buildCommand = ''
      mkdir -p $out unpacked
      unzip -q ${sources.perFamily.sans."Lilex.zip"} \
        ${lib.escapeShellArg m.options.${"lilex_ttf_${lib.toLower weight}"}} -d unpacked
      cp unpacked/${lib.escapeShellArg m.options.${"lilex_ttf_${lib.toLower weight}"}} \
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

  # Latin scaling happens inside the merge engine, so sans has no latin-prepared
  # step of its own. Phase 5 replaced sans/scripts/merge_plex.py with
  # `fontkit merge`: every number below used to be a command-line flag repeated
  # in four families' Nix and four families' argparse, and is a [merge] /
  # [grid] / [metrics.<profile>] field read straight from font.toml now.
  merged = weight: step "merged" { inherit family profile region weight; } {
    buildCommand = ''
      mkdir -p $out merged
      fontkit merge \
        --manifest ${manifest.file} \
        --profile ${profile} \
        --latin-regular ${srcLatin "Regular"}/Lilex-Regular.ttf \
        --latin-bold ${srcLatin "Bold"}/Lilex-Bold.ttf \
        --cjk-regular ${cjkPrepared "Regular"}/IBMPlexSansSC-Regular-weight.ttf \
        --cjk-bold ${cjkPrepared "Bold"}/IBMPlexSansSC-Bold-weight.ttf \
        --out-dir merged

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
        --family ${lib.escapeShellArg naming.family} \
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
        --expect-half ${toString grid.en_adv} --check-nerd --check-eaw ${out}/nerd/${ps}-*.ttf
      python3 ${file "sans/scripts/verify-features.py"} ${out}/nerd/${ps}-*.ttf

      # Informational, and deliberately still allowed to fail: it confirms Latin
      # and CJK ended up at the same optical weight after the embolden, but it
      # is a report, not a gate — 04-verify.sh ran it under `|| true` with a
      # per-glyph `except: continue` inside.
      #
      # It is not hypothetical. `fontkit measure` raises on
      # LilexSansSCNFM-Bold.ttf: measure.py:111 assumes every `qCurveTo`
      # argument is a point, and TrueType's all-off-curve contour passes a
      # trailing `None` for the implied on-curve point. That is a pre-existing
      # defect in the measuring code, not in the font and not in this phase —
      # the old inline script swallowed it one glyph at a time. Worth its own
      # issue; folding a fix into a phase whose completion criterion is
      # "fingerprints do not move" is how two changes become impossible to tell
      # apart later.
      for font in ${out}/nerd/${ps}-*.ttf; do
        echo "==> $(basename "$font")"
        fontkit measure --font "$font" | tail -20 || true
      done
      touch $out
    '';

  readme = pkgs.writeText "sans-README.txt" ''
    ${naming.family} @version@
    Derived from Lilex + IBM Plex Sans SC under SIL OFL 1.1.
    Nerd Font icons via font-patcher ${m.nerd.version} (--complete --single-width-glyphs).
    Not an official Lilex, IBM, or Nerd Fonts product.

    Name recipe (same style as SarasaNZSSlab NFM):
      Lilex  = Lilex Latin / programming (ligatures + OT features preserved)
      SansSC = Plex Sans SC CJK
      NFM    = Nerd Font Mono

    Cell metrics: EN ${toString grid.en_adv} / CJK ${toString grid.cjk_adv} (strict 2:1)
    Mono flags:   post.isFixedPitch=1, PANOSE bProportion=9
    Icons:        Nerd complete set at half-cell advance
    EAW:          N/Na/H → half, W/F → full (ambiguous left alone by default)

    Install: copy the .ttf into your OS fonts directory.
    In terminals/IDEs pick family "${naming.family}" and enable font ligatures.

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
    fontDir = pkgs.runCommand "sans-release-fonts" { } ''
      mkdir -p $out
      ${lib.concatMapStringsSep "\n" (w: "cp ${nerd w}/*.ttf $out/") weights}
    '';
    licenseDir = file "sans/licenses";
  };
}
