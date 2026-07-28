# pixel — Fusion Pixel 12px mono + hand-drawn ligatures + Nerd icons.
#
# Was: 01-fetch-sources.sh / 02-add-ligatures.sh / 03-narrow-ambiguous.sh /
#      04-nerd-patch.sh / 05-verify.sh / build.sh / common.sh / package-release.sh
#      (416 lines of shell, of which 130 were the docker-or-fontforge ladder).
#
# Single weight, and the Latin and CJK halves arrive in the same upstream file,
# so this family has no separate latin-prepared / cjk-prepared split — it goes
# src-cjk → merged → nerd → packaged.
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

  family = "pixel";
  weight = support.weightName (lib.head m.build.weights);

  # --- src-cjk --------------------------------------------------------------
  # The product face and the half-width donor come out of the same zip; both are
  # upstream bytes, so they belong to the same source step.
  src = step "src-cjk" { inherit family region weight; } {
    nativeBuildInputs = [ pkgs.unzip ];
    buildCommand = ''
      mkdir -p $out unpacked
      unzip -q ${sources.perFamily.pixel."fusion-pixel-12px-monospaced-ttf.zip"} -d unpacked
      cp unpacked/${m.options.fusion_ttf} $out/fusion-base.ttf
      cp unpacked/${m.options.fusion_ttf_halfwidth_donor} $out/fusion-halfwidth-donor.ttf
    '';
  };

  # --- merged ---------------------------------------------------------------
  # Ligature injection and the ambiguous-width narrowing were two scripts, but
  # they are one cache unit: nothing else consumes the un-narrowed face, and
  # the Nerd step's metric hygiene has to see final advances.
  merged = step "merged"
    {
      inherit family profile region weight;
    }
    {
      buildCommand = ''
        mkdir -p $out
        python3 ${file "pixel/scripts/build_ligatures.py"} \
          --base ${src}/fusion-base.ttf \
          --art ${file "pixel/ligatures/ligatures.txt"} \
          --out $out/${naming.base_ps}-${weight}.ttf \
          --family ${lib.escapeShellArg naming.base_family} \
          --family-ps ${naming.base_ps} \
          --half ${toString grid.en_adv} \
          --px ${toString m.options.px_unit} \
          --ascent ${toString metrics.hhea_ascent}

        # Fusion's zh_hans flavour draws “ ” ‘ ’ … · ‥ ․ ‧ at two cells with the
        # ink in the right half; the latin flavour of the same release draws
        # them at one. Transplant those before anything measures advances.
        python3 ${file "pixel/scripts/narrow_ambiguous.py"} \
          --donor ${src}/fusion-halfwidth-donor.ttf \
          $out/*.ttf
      '';
    };

  # --- nerd -----------------------------------------------------------------
  nerd = step "nerd" { inherit family region weight; } {
    nativeBuildInputs = [ support.fontforge ];
    buildCommand = ''
      export HOME=$TMPDIR
      mkdir -p $out
      fontkit nerd-patch \
        --patcher ${patcher} \
        --out $out \
        --family ${lib.escapeShellArg naming.family} \
        --family-ps ${naming.ps} \
        ${merged}/*.ttf
    '';
  };

  # --- out tree -------------------------------------------------------------
  # The same layout the shell build left in pixel/out, because that is what the
  # fingerprint baselines are keyed on (tools/fingerprint.py walks it and names
  # each product by its path relative to out/).
  out = pkgs.runCommand "pixel-out" { } ''
    mkdir -p $out/nerd
    cp ${merged}/*.ttf $out/
    cp ${nerd}/*.ttf $out/nerd/
  '';

  # --- verify ---------------------------------------------------------------
  # A check, not a build step: it reads products and writes nothing, so it has
  # no place in the granularity contract. `nix flake check` runs it; so does the
  # packaging step's dependency on it.
  verify = pkgs.runCommand "pixel-verify"
    {
      nativeBuildInputs = [ support.pythonEnv ];
    }
    ''
      python3 ${file "pixel/scripts/verify.py"} \
        --half ${toString grid.en_adv} \
        --full ${toString grid.cjk_adv} \
        --check-nerd \
        --check-ligatures \
        --check-eaw \
        ${nerd}/*.ttf
      touch $out
    '';

  readme = pkgs.writeText "pixel-README.txt" ''
    ${naming.family} @version@
    ============================================

    Family: ${naming.family}
    Grid:   Fusion Pixel 12px mono (EN ${toString grid.en_adv} / CJK ${toString grid.cjk_adv})
    Ligatures: hand-drawn pixel programming ligatures (calt)
    Icons:  Nerd Fonts complete set (single-cell), not redrawn
            font-patcher ${m.nerd.version}

    Install: copy the .ttf into your OS fonts directory.
    In terminals/IDEs pick family "${naming.family}" and enable font ligatures.

    Sources: https://github.com/AkaraChen/font (pixel/)
    Upstream: Fusion Pixel Font (OFL), Nerd Fonts glyph sets
  '';

in
{
  inherit out verify;

  # Attribute names are the contract's step names — nix/checks.nix asserts it,
  # so a family cannot invent a step of its own and be the only one that has it.
  steps = {
    "src-cjk" = src;
    inherit merged nerd;
  };

  # Everything the release archive ships, and the gate it must pass first.
  release = {
    inherit family profile region weight readme verify;
    stem = naming.stem;
    fontDir = nerd;
    licenseDir = file "pixel/licenses";
  };
}
