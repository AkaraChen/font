# pixel — Fusion Pixel 12px mono + hand-drawn ligatures + Nerd icons.
#
# Was: 01-fetch-sources.sh / 02-add-ligatures.sh / 03-narrow-ambiguous.sh /
#      04-nerd-patch.sh / 05-verify.sh / build.sh / common.sh / package-release.sh
#      (416 lines of shell, of which 130 were the docker-or-fontforge ladder).
#
# Single weight, and the Latin and CJK halves arrive in the same upstream file,
# so this family has no separate latin-prepared / cjk-prepared split — it goes
# src-cjk → merged → nerd → packaged.
#
# Phase 7 (KIT-282) added the region axis, and pixel is where it is cheapest:
# zh_hans / zh_hant / ja / ko are four members of the *same* pinned archive, so
# four regions cost no extra bytes in the source layer at all.
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
  metrics = m.metrics.coding;

  family = "pixel";
  weight = support.weightName (lib.head m.build.weights);

  regions = lib.unique (map (cell: cell.region) (support.cellsOf m));
  naming = region: support.namingFor m profile region;
  tag = region: lib.optionalString (lib.length regions > 1) "-${region}";

  # --- src-cjk --------------------------------------------------------------
  # The product face and the half-width donor come out of the same zip; both are
  # upstream bytes, so they belong to the same source step. The donor has no
  # regional variant — it is the `latin` flavour and is the same file for all
  # four — but it is unpacked per region anyway, because splitting it out would
  # mean a second derivation over the same archive to save one copy.
  src = region: step "src-cjk" { inherit family region weight; } {
    nativeBuildInputs = [ pkgs.unzip ];
    buildCommand = ''
      mkdir -p $out unpacked
      unzip -q ${sources.perFamily.pixel."fusion-pixel-12px-monospaced-ttf.zip"} -d unpacked
      cp unpacked/${m.options.${"fusion_ttf_${region}"}} $out/fusion-base.ttf
      cp unpacked/${m.options.fusion_ttf_halfwidth_donor} $out/fusion-halfwidth-donor.ttf
    '';
  };

  # --- merged ---------------------------------------------------------------
  # Ligature injection and the ambiguous-width narrowing were two scripts, but
  # they are one cache unit: nothing else consumes the un-narrowed face, and
  # the Nerd step's metric hygiene has to see final advances.
  merged = region:
    let names = naming region; in
    step "merged" { inherit family profile region weight; } {
      buildCommand = ''
        mkdir -p $out
        python3 ${file "pixel/scripts/build_ligatures.py"} \
          --base ${src region}/fusion-base.ttf \
          --art ${file "pixel/ligatures/ligatures.txt"} \
          --out $out/${names.base_ps}-${weight}.ttf \
          --family ${lib.escapeShellArg names.base_family} \
          --family-ps ${names.base_ps} \
          --half ${toString grid.en_adv} \
          --px ${toString m.options.px_unit} \
          --ascent ${toString metrics.hhea_ascent}

        # Fusion's CJK flavours draw “ ” ‘ ’ … · ‥ ․ ‧ at two cells with the ink
        # in the right half; the latin flavour of the same release draws them at
        # one. Transplant those before anything measures advances.
        python3 ${file "pixel/scripts/narrow_ambiguous.py"} \
          --donor ${src region}/fusion-halfwidth-donor.ttf \
          $out/*.ttf
      '';
    };

  # --- nerd -----------------------------------------------------------------
  nerd = region: step "nerd" { inherit family region weight; } {
    nativeBuildInputs = [ support.fontforge ];
    buildCommand = ''
      export HOME=$TMPDIR
      mkdir -p $out
      fontkit nerd-patch \
        --patcher ${patcher} \
        --out $out \
        --family ${lib.escapeShellArg (naming region).family} \
        --family-ps ${(naming region).ps} \
        ${merged region}/*.ttf
    '';
  };

  # --- packaged -------------------------------------------------------------
  # The formats a cell declares beyond the TTF the Nerd step produced
  # (KIT-283). pixel is single-weight, so this is one conversion per region.
  declaredFormats = (lib.head (support.cellsOf m)).formats;
  formats = support.extraFormats declaredFormats;
  converted = region: format: support.convert {
    inherit family profile region weight format;
    src = nerd region;
  };
  copyFormats = region: dest:
    lib.concatMapStringsSep "\n"
      (format: "cp ${converted region format}/*.${format} ${dest}")
      formats;

  # --- out tree -------------------------------------------------------------
  # The same layout the shell build left in pixel/out, because that is what the
  # fingerprint baselines are keyed on (tools/fingerprint.py walks it and names
  # each product by its path relative to out/).
  cellOut = region: pkgs.runCommand "pixel-${profile}-${region}" { } ''
    mkdir -p $out/nerd
    cp ${merged region}/*.ttf $out/
    cp ${nerd region}/*.ttf $out/nerd/
    ${copyFormats region "$out/nerd/"}
  '';

  out = pkgs.runCommand "pixel-out" { } ''
    mkdir -p $out/nerd
    ${lib.concatMapStringsSep "\n" (r: "cp -R ${cellOut r}/. $out/") regions}
  '';

  # --- verify ---------------------------------------------------------------
  # A check, not a build step: it reads products and writes nothing, so it has
  # no place in the granularity contract. Per-region so the CI matrix can gate
  # one cell without realising the other three (KIT-305).
  verifyRegion = region:
    let products = cellOut region; in
    pkgs.runCommand "pixel-verify-${region}"
      {
        nativeBuildInputs = [ support.pythonEnv ];
      }
      ''
        echo "==> ${region}"
        python3 ${file "pixel/scripts/verify.py"} \
          --half ${toString grid.en_adv} \
          --full ${toString grid.cjk_adv} \
          --check-nerd \
          --check-ligatures \
          --check-eaw \
          ${nerd region}/*.ttf
        fontkit verify-formats ${products}
        touch $out
      '';

  verify = pkgs.runCommand "pixel-verify" { } ''
    ${lib.concatMapStringsSep "\n" (region: "test -e ${verifyRegion region}") regions}
    touch $out
  '';

  readme = region: pkgs.writeText "pixel-${region}-README.txt" (
    let names = naming region; in
    ''
      ${names.family} @version@
      ============================================

      Family: ${names.family}
      Grid:   Fusion Pixel 12px mono (EN ${toString grid.en_adv} / CJK ${toString grid.cjk_adv})
              The 12px design size is a property of the outlines, not of the
              family name — this face is legible at its design size on a snapped
              pixel grid and nowhere else.
      Region: ${m.options.${"fusion_ttf_${region}"}}
      Ligatures: hand-drawn pixel programming ligatures (calt)
      Icons:  Nerd Fonts complete set (single-cell), not redrawn
              font-patcher ${m.nerd.version}

      Install: copy the .ttf into your OS fonts directory.
      In terminals/IDEs pick family "${names.family}" and enable font ligatures.

      Sources: https://github.com/AkaraChen/font (pixel/)
      Upstream: Fusion Pixel Font (OFL), Nerd Fonts glyph sets
    ''
  );

  releaseFor = region: {
    inherit family profile region weight verify;
    formats = declaredFormats;
    readme = readme region;
    stem = (naming region).ps;
    fontDir = pkgs.runCommand "pixel-${region}-release-fonts" { } ''
      mkdir -p $out
      cp ${nerd region}/*.ttf $out/
      ${copyFormats region "$out/"}
    '';
    licenseDir = file "pixel/licenses";
  };

in
{
  inherit out verify;

  # `nix build .#pixel-coding-ja`.
  cells = lib.listToAttrs (
    map (region: lib.nameValuePair "${profile}-${region}" (cellOut region)) regions
  );

  cellVerifies = lib.listToAttrs (
    map
      (region: lib.nameValuePair "${profile}-${region}" (verifyRegion region))
      regions
  );

  # Attribute names are the contract's step names — nix/checks.nix asserts it,
  # so a family cannot invent a step of its own and be the only one that has it.
  steps = lib.listToAttrs (
    lib.concatMap
      (region: [
        { name = "src-cjk${tag region}"; value = src region; }
        { name = "merged${tag region}"; value = merged region; }
        { name = "nerd${tag region}"; value = nerd region; }
      ]
      ++ map
        (format: {
          name = "packaged${tag region}-${format}";
          value = converted region format;
        })
        formats)
      regions
  );

  # Everything the release archive ships, and the gate it must pass first.
  release = releaseFor (lib.head regions);
  extraReleases = lib.listToAttrs (
    map (region: lib.nameValuePair region (releaseFor region)) (lib.tail regions)
  );
}
