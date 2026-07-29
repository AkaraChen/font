# sans — Lilex (Latin) × IBM Plex Sans SC/TC/JP/KR (CJK) + Nerd Font Mono.
#
# Was: 01-fetch-sources.sh / 02-merge.sh / 03-nerd-patch.sh / 04-verify.sh /
#      build.sh / common.sh / package-release.sh (532 lines).
#
# 02-merge.sh had the worst of the cross-family reaches: `04-verify.sh:48` did
# `sys.path.insert(0, os.environ["SERIF_TOOLS"])` to borrow serif's measuring
# code, so a change under serif/ could move this product's stroke report without
# anyone touching sans/. Phase 2 made that `fontkit.measure`; this step can no
# longer see serif at all.
#
# Phase 7 (KIT-282) made this the first family with a real region axis, and it
# is the family the axis was designed around: Plex ships four masters at one
# pinned commit, so the only thing that varies is the CJK donor. Everything
# below the merge — `src-latin`, and the scaling the merge engine does to it —
# is byte-identical across all four, which is `nix/granularity.nix`'s ★ claim
# collecting on its promise. Four regions cost four merges and four Nerd
# patches, not four Latin builds.
{ pkgs
, lib
, support
, sources
, manifest
,
}:

let
  inherit (support) step file profile patcher;
  m = manifest.data;
  inherit (m) grid;

  family = "sans";
  weights = map support.weightName m.build.weights;

  cells = support.cellsOf m;
  regions = lib.unique (map (cell: cell.region) cells);

  naming = region: support.namingFor m profile region;

  # Plex's own spelling of a region: `IBMPlexSansTC-Bold.ttf`.
  plex = region: weight: "IBMPlexSans${lib.toUpper region}-${weight}.ttf";

  # Region belongs in a step's attribute name exactly when the family varies on
  # it, the same rule handwriting follows for `profile`. Five sc-only families
  # keep the names their fingerprints were taken under.
  tag = region: lib.optionalString (lib.length regions > 1) "-${region}";

  emboldenFor = weight: toString m.calibration.${lib.toLower weight}.embolden;

  # The 2:1 gate asks "are these characters present, at the full cell". Which
  # characters is a property of the script, not of the family: the built-in
  # sample is Simplified, and `sc` therefore declares nothing and keeps it.
  gateSample =
    region:
    let key = "gate_cjk_sample_${region}"; in
    lib.optionalString (m.options ? ${key})
      "--cjk-sample ${lib.escapeShellArg m.options.${key}}";

  # ★ No region axis, and `nix/granularity.nix` refuses to let one be added by
  # accident: a Japanese build asks for these exact bytes.
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

  srcCjk = region: weight: step "src-cjk" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      cp ${sources.perFamily.sans.${plex region weight}} $out/${plex region weight}
    '';
  };

  # Plex Sans masters read light next to Lilex once the Latin is compressed to
  # the 550 cell; the embolden closes that gap without swapping weight masters.
  # Strengths are measured — sans/scripts/calibrate-stroke.sh — and are shared
  # across regions: the four masters are one design at one optical weight, so
  # re-measuring per region would be measuring noise.
  cjkPrepared = region: weight: step "cjk-prepared" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      ${support.emboldenOrCopy {
        strength = emboldenFor weight;
        src = "${srcCjk region weight}/${plex region weight}";
        dst = "$out/${plex region weight}";
      }}
    '';
  };

  # Latin scaling happens inside the merge engine, so sans has no latin-prepared
  # step of its own. Phase 5 replaced sans/scripts/merge_plex.py with
  # `fontkit merge`: every number below used to be a command-line flag repeated
  # in four families' Nix and four families' argparse, and is a [merge] /
  # [grid] / [metrics.<profile>] field read straight from font.toml now.
  merged = region: weight:
    let basePs = (naming region).base_ps; in
    step "merged" { inherit family profile region weight; } {
      buildCommand = ''
        mkdir -p $out merged
        fontkit merge \
          --manifest ${manifest.file} \
          --profile ${profile} \
          --region ${region} \
          --latin-regular ${srcLatin "Regular"}/Lilex-Regular.ttf \
          --latin-bold ${srcLatin "Bold"}/Lilex-Bold.ttf \
          --cjk-regular ${cjkPrepared region "Regular"}/${plex region "Regular"} \
          --cjk-bold ${cjkPrepared region "Bold"}/${plex region "Bold"} \
          --out-dir merged

        cp merged/${basePs}-${weight}.ttf $out/
        # Terminals size cells from Unicode EAW, not from font metrics. Geometric
        # fit — there is no Sarasa Term donor on this 550 grid.
        fontkit narrow-symbol-widths --no-donor $out/${basePs}-${weight}.ttf
        fontkit fix-terminal-metrics $out/${basePs}-${weight}.ttf
      '';
    };

  nerd = region: weight: step "nerd" { inherit family region weight; } {
    nativeBuildInputs = [ support.fontforge ];
    buildCommand = ''
      export HOME=$TMPDIR
      mkdir -p $out
      fontkit nerd-patch \
        --patcher ${patcher} \
        --out $out \
        --family ${lib.escapeShellArg (naming region).family} \
        --family-ps ${(naming region).ps} \
        --narrow-symbols \
        ${merged region weight}/*.ttf
    '';
  };

  # --- packaged -------------------------------------------------------------
  # The formats a cell declares beyond the TTF the Nerd step produced
  # (KIT-283). Every region declares the same list — a format is a property of
  # the scene, not of the script — but it is read per cell rather than assumed,
  # because `[[build.matrix]]` is allowed to disagree with that.
  declaredFormats = (lib.head cells).formats;
  formats = support.extraFormats declaredFormats;
  converted = region: weight: format: support.convert {
    inherit family profile region weight format;
    src = nerd region weight;
  };
  copyFormats = region: weight: dest:
    lib.concatMapStringsSep "\n"
      (format: "cp ${converted region weight format}/*.${format} ${dest}")
      formats;

  # One region's products, in the layout `<family>/out` has always had. Product
  # stems carry the region (`AKRSansTCNFM-Bold.ttf`), so four of these unpack
  # into one directory without colliding.
  cellOut = region: pkgs.runCommand "sans-${profile}-${region}" { } ''
    mkdir -p $out/nerd
    ${lib.concatMapStringsSep "\n" (w: "cp ${merged region w}/*.ttf $out/") weights}
    ${lib.concatMapStringsSep "\n" (w: ''
      cp ${nerd region w}/*.ttf $out/nerd/
      ${copyFormats region w "$out/nerd/"}
    '') weights}
  '';

  out = pkgs.runCommand "sans-out" { } ''
    mkdir -p $out/nerd
    ${lib.concatMapStringsSep "\n" (r: "cp -R ${cellOut r}/. $out/") regions}
    cp ${file "sans/licenses"}/OFL-Lilex.txt ${file "sans/licenses"}/OFL-IBM-Plex.txt $out/
  '';

  verify = pkgs.runCommand "sans-verify"
    {
      nativeBuildInputs = [ support.verifyEnv ];
    }
    ''
      ${lib.concatMapStringsSep "\n" (region: ''
        echo "==> ${region}"
        fontkit verify-2to1 \
          --expect-half ${toString grid.en_adv} --check-nerd --check-eaw \
          ${gateSample region} \
          ${out}/nerd/${(naming region).ps}-*.ttf
        python3 ${file "sans/scripts/verify-features.py"} ${out}/nerd/${(naming region).ps}-*.ttf
      '') regions}

      # Informational, and deliberately still allowed to fail: it confirms Latin
      # and CJK ended up at the same optical weight after the embolden, but it
      # is a report, not a gate — 04-verify.sh ran it under `|| true` with a
      # per-glyph `except: continue` inside.
      #
      # It is not hypothetical. `fontkit measure` raises on the Bold products:
      # measure.py:111 assumes every `qCurveTo` argument is a point, and
      # TrueType's all-off-curve contour passes a trailing `None` for the
      # implied on-curve point. That is a pre-existing defect in the measuring
      # code, not in the font and not in this phase — the old inline script
      # swallowed it one glyph at a time. Worth its own issue.
      for font in ${out}/nerd/*.ttf; do
        echo "==> $(basename "$font")"
        fontkit measure --font "$font" | tail -20 || true
      done

      # Every converted format against the TTF it was made from (KIT-283).
      fontkit verify-formats ${out}
      touch $out
    '';

  readme = region: pkgs.writeText "sans-${region}-README.txt" (
    let names = naming region; in
    ''
      ${names.family} @version@
      Derived from Lilex + IBM Plex Sans ${lib.toUpper region} under SIL OFL 1.1.
      Nerd Font icons via font-patcher ${m.nerd.version} (--complete --single-width-glyphs).
      Not an official Lilex, IBM, or Nerd Fonts product.

      Name recipe (AKR <Style> <Region> <Variant>):
        AKR    = this repository's house name; no upstream reserved name is
                 carried in the family name. Donors are named in name ID 5.
        Sans   = Lilex Latin (ligatures + OT features preserved) on a sans CJK
        ${lib.toUpper region}     = IBM Plex Sans ${lib.toUpper region} CJK master
        NFM    = Nerd Font Mono

      Cell metrics: EN ${toString grid.en_adv} / CJK ${toString grid.cjk_adv} (strict 2:1)
      Mono flags:   post.isFixedPitch=1, PANOSE bProportion=9
      Icons:        Nerd complete set at half-cell advance
      EAW:          N/Na/H → half, W/F → full (ambiguous left alone by default)

      Install: copy the .ttf into your OS fonts directory.
      In terminals/IDEs pick family "${names.family}" and enable font ligatures.

      Upstream pins: see font.toml in the build repository.
    ''
  );

  releaseFor = region: {
    inherit family profile region verify;
    formats = declaredFormats;
    readme = readme region;
    weight = "Regular";
    stem = (naming region).ps;
    fontDir = pkgs.runCommand "sans-${region}-release-fonts" { } ''
      mkdir -p $out
      ${lib.concatMapStringsSep "\n" (w: ''
        cp ${nerd region w}/*.ttf $out/
        ${copyFormats region w "$out/"}
      '') weights}
    '';
    licenseDir = file "sans/licenses";
  };

in
{
  inherit out verify;

  # `nix build .#sans-coding-tc` → one (profile, region) cell's products.
  cells = lib.listToAttrs (
    map (region: lib.nameValuePair "${profile}-${region}" (cellOut region)) regions
  );

  steps = lib.listToAttrs (
    lib.concatMap (weight: [{ name = "src-latin-${weight}"; value = srcLatin weight; }]) weights
    ++ lib.concatMap
      (region: lib.concatMap
        (weight: [
          { name = "src-cjk${tag region}-${weight}"; value = srcCjk region weight; }
          { name = "cjk-prepared${tag region}-${weight}"; value = cjkPrepared region weight; }
          { name = "merged${tag region}-${weight}"; value = merged region weight; }
          { name = "nerd${tag region}-${weight}"; value = nerd region weight; }
        ]
        ++ map
          (format: {
            name = "packaged${tag region}-${weight}-${format}";
            value = converted region weight format;
          })
          formats)
        weights)
      regions
  );

  # `.#sans-release` stays the Simplified archive it has always been; the other
  # three are their own products with their own family names, so they are their
  # own archives rather than extra files in one zip.
  release = releaseFor (lib.head regions);
  extraReleases = lib.listToAttrs (
    map (region: lib.nameValuePair region (releaseFor region)) (lib.tail regions)
  );
}
