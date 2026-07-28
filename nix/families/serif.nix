# serif — Sarasa MonoSlab (Iosevka N Slab Latin) × LXGW Neo ZhiSong (CJK),
# built by the *upstream* Sarasa toolchain, then Nerd-patched.
#
# Was: 01-clone-sarasa.sh / 02-apply-quilt.sh / 03-prepare-cjk.sh / 04-build.sh /
#      05-nerd-patch.sh / 06-narrow-symbols.sh / build.sh / common.sh /
#      package-release.sh, plus tools/src-cache.sh, which existed for this one
#      family after Phase 3 moved the other six into derivations.
#
# The one genuinely different family: it does not download a finished face and
# post-process it, it runs Sarasa's own verda build with two quilt patches and a
# CJK master swapped into sources/shs. That is why it was left out of Phase 3
# and why it is the whole of Phase 5 (KIT-280).
#
# Three things the shell path did that a derivation gets for free, and which are
# the actual reason to move it:
#
#   * `git clone --depth 1` on every cold run, verified by commit id — i.e. by
#     asking the server to confirm the name of what it just served. The tree is
#     `fetchFromGitHub` now: hash-pinned bytes, fetched once per pin.
#   * `npm install` into a working tree, with node_modules manually moved out
#     and back around the `rm -rf` as a speed hack. `buildNpmPackage` +
#     `npmDepsHash` makes the dependency set an input, and the store caches it.
#   * quilt: a patch stack applied imperatively, with `.pc` state to reset each
#     run. stdenv's `patches` applies the same series declaratively — the series
#     file is still the source of truth for the order, read below.
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

  family = "serif";
  weights = map support.weightName m.build.weights;

  ps = naming.ps;
  version = lib.removePrefix "v" m.sources.sarasa.ref;

  # Upstream's own product names, before ours are stamped on: config.json
  # renames the *family*, not the file stem, so the verda build still writes
  # SarasaMonoSlabSC-<weight>.ttf.
  upstreamStem = "SarasaMonoSlabSC";
  intermediateStem = "SarasaMonoSlabNeoZhiSongSC-Opt";

  emboldenFor = weight: toString m.calibration.${lib.toLower weight}.embolden;

  # --- sources --------------------------------------------------------------

  # One CJK master for both weights: Neo ZhiSong ships a single Regular and the
  # Bold is made by emboldening it (see cjkPrepared), so this step has no real
  # weight axis. The contract requires one, and pinning it to Regular is the
  # honest spelling — a second identical derivation under a Bold name would
  # claim a distinction that does not exist.
  srcCjk = step "src-cjk"
    {
      inherit family region;
      weight = "Regular";
    }
    {
      buildCommand = ''
        mkdir -p $out
        cp ${sources.perFamily.serif.${m.options.lxgw_asset}} \
          $out/${m.options.lxgw_asset}
      '';
    };

  # Neo ZhiSong is drawn on 2048 and the product grid is 1000, so the scale
  # comes first and the calibrated embolden strengths (which are in product
  # units — serif/scripts/calibrate-stroke.sh measures there) apply after it.
  #
  # Song-style CJK is optically lighter than Iosevka's slab stems at the same
  # nominal weight; both weights are emboldened from the same Regular master,
  # Bold considerably harder, because upstream has no Bold to pair with.
  cjkPrepared = weight: step "cjk-prepared" { inherit family region weight; } {
    buildCommand = ''
      mkdir -p $out
      fontkit scale-upem ${srcCjk}/${m.options.lxgw_asset} scaled.ttf \
        --upem ${toString grid.upm}
      ${support.emboldenOrCopy {
        strength = emboldenFor weight;
        src = "scaled.ttf";
        dst = "$out/LXGWNeoZhiSongSC-${weight}.ttf";
      }}
    '';
  };

  # --- the upstream build ---------------------------------------------------

  # The quilt series, in series order. Reading the file rather than listing the
  # patches here keeps one source of truth: `quilt push -a` and this derivation
  # cannot disagree about the order, which is the thing a hand-maintained list
  # would eventually get wrong.
  patchSeries = lib.filter
    (line: line != "" && !(lib.hasPrefix "#" line))
    (lib.splitString "\n" (builtins.readFile (file "serif/patches/series")));

  # Sarasa's own build, with our two patches and our CJK master.
  #
  # NOT a granularity step, and deliberately so: `npm run build ttf-unhinted`
  # emits every style in config.json in one verda run, so a per-weight
  # derivation would run the whole multi-hour build twice to throw half of each
  # away. The contract's `merged` step below is the per-weight face, extracted
  # from here — cheap, correctly keyed, and it keeps `nix build .#serif-merged-Bold`
  # meaning what it means for every other family.
  sarasaBuild = pkgs.buildNpmPackage {
    pname = "sarasa-neozhisong";
    inherit version;
    src = sources.sarasaSrc;
    npmDepsHash = "sha256-78e/UFeXBzrXD3Q6j1iH3zZM7H9VF+l2U8JvkG597+k=";

    patches = map (patch: file "serif/patches/${patch}") patchSeries;

    # afdko provides otc2otf / otf2ttf, which verdafile.mjs shells out to during
    # source prep (L200 / L220 / L235). It was never in this repo's need_cmd
    # list — serif only ever built because the maintainer's machine happened to
    # have AFDKO installed, and Sarasa's own check-env.mjs merely console.errors
    # when it is missing. Patch 0001 means the drop-in TTF path skips both
    # binaries for *this* config, but the declaration is the point: the build
    # may not depend on what a host happens to have.
    #
    # ttfautohint is only consumed by the hinted targets and we build
    # ttf-unhinted, so it is not on the critical path. Declared for the same
    # reason: `CheckTtfAutoHintExists` is an oracle that degrades quietly.
    # afdko is a Python distribution, not a top-level package: `python3Packages`
    # is where the otc2otf / otf2ttf console scripts come from, the same
    # attribute the devShell's pythonEnv pulls in.
    nativeBuildInputs = [
      pkgs.python3Packages.afdko
      pkgs.ttfautohint
    ];

    # The CJK swap that patch 0002 points config.json at. `sources/shs` is where
    # Sarasa expects its Han masters; 03-prepare-cjk.sh wrote the same two files
    # into a mutable checkout.
    postPatch = ''
      mkdir -p sources/shs
      cp ${cjkPrepared "Regular"}/LXGWNeoZhiSongSC-Regular.ttf sources/shs/
      cp ${cjkPrepared "Bold"}/LXGWNeoZhiSongSC-Bold.ttf sources/shs/
    '';

    # `npm run build <target>`, not npmBuildScript: the target is a verda phony
    # and has to reach verda as an argument.
    dontNpmBuild = true;
    buildPhase = ''
      runHook preBuild
      npm run build ${m.options.build_target}
      runHook postBuild
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p $out
      ${lib.concatMapStringsSep "\n"
        (weight: "cp out/TTF-Unhinted/${upstreamStem}-${weight}.ttf $out/")
        weights}
      runHook postInstall
    '';

    meta = {
      description = "Sarasa Mono Slab with LXGW Neo ZhiSong as the CJK master";
      license = lib.licenses.ofl;
    };
  };

  # --- the contract steps ---------------------------------------------------

  # serif has no `latin-prepared`: its Latin is Iosevka N Slab *inside* the
  # Sarasa tree and is never a standalone artifact. The merge is upstream's, so
  # this step is the extraction — one face, under the name 04-build.sh gave it,
  # which is the name the fingerprint baseline holds.
  merged = weight: step "merged" { inherit family profile region weight; } {
    buildCommand = ''
      mkdir -p $out
      cp ${sarasaBuild}/${upstreamStem}-${weight}.ttf \
        $out/${intermediateStem}-${weight}.ttf
    '';
  };

  # Sarasa Term draws the EAW-narrow symbols (⏵ ✓ ⌘ ↑ …) on one cell, where
  # Sarasa *Mono* draws them on two and overflows the terminal cell. It is the
  # donor for the narrow pass — the only family that has one, which is why the
  # other six fit geometrically instead.
  donor = pkgs.runCommand "serif-term-donor"
    {
      nativeBuildInputs = [ pkgs.p7zip ];
    }
    ''
      mkdir -p $out
      7z x -y -o$out ${sources.perFamily.serif."SarasaTermSlabSC-TTF-Unhinted.7z"} \
        ${lib.escapeShellArg m.options.sarasa_term_regular} \
        ${lib.escapeShellArg m.options.sarasa_term_bold} >/dev/null
    '';

  donorFor = weight: "${donor}/${m.options.${"sarasa_term_${lib.toLower weight}"}}";

  # 05-nerd-patch.sh + 06-narrow-symbols.sh, in one step and in their order.
  # `--no-nerd-widths` is not an oversight: serif's patcher output is already
  # half-cell and the old scripts never ran that pass, so running it now would
  # move a fingerprint for no product reason.
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
        --no-nerd-widths \
        --narrow-symbols \
        --donor ${donorFor weight} \
        --protect-ambiguous \
        --widen-shared skip \
        --expand-ligatures \
        ${merged weight}/*.ttf
    '';
  };

  out = pkgs.runCommand "serif-out" { } ''
    mkdir -p $out/nerd
    ${lib.concatMapStringsSep "\n" (w: "cp ${merged w}/*.ttf $out/") weights}
    ${lib.concatMapStringsSep "\n" (w: "cp ${nerd w}/*.ttf $out/nerd/") weights}
  '';

  verify = pkgs.runCommand "serif-verify"
    {
      nativeBuildInputs = [ support.verifyEnv ];
    }
    ''
      fontkit verify-2to1 \
        --profile dense --check-nerd --check-eaw ${out}/nerd/${ps}-*.ttf
      touch $out
    '';

  readme = pkgs.writeText "serif-README.txt" ''
    ${naming.family} @version@

    Family: ${naming.family}
    Styles: ${lib.concatStringsSep ", " weights}
    Grid:   2:1 dual-width mono (Latin ${toString grid.en_adv} / CJK ${toString grid.cjk_adv})
    Icons:  Nerd Fonts complete set (single-cell), font-patcher ${m.nerd.version}
    Widths: advances match Unicode East_Asian_Width, so terminals that size
            cells with wcwidth() line up (neutral symbols like U+23F5 are
            half-width). Ambiguous-width symbols stay full-width by design.

    Built from Sarasa Gothic ${m.sources.sarasa.ref} (Iosevka N Slab Latin) with
    LXGW Neo ZhiSong ${m.sources.lxgw.version} as the CJK master.

    Install: copy the .ttf files into your OS fonts directory, or use a
    font manager. In terminals/IDEs pick family "${naming.family}".

    Sources: https://github.com/AkaraChen/font (serif/)
    Licenses: Sarasa / IosevkaN / LXGW Neo ZhiSong / Nerd Fonts glyph sets —
    see upstream and repo LICENSE notes.

    Upstream pins: see font.toml in the build repository.
  '';

in
{
  inherit out verify;

  steps = lib.listToAttrs (
    [ { name = "src-cjk-Regular"; value = srcCjk; } ]
    ++ lib.concatMap
      (weight: [
        { name = "cjk-prepared-${weight}"; value = cjkPrepared weight; }
        { name = "merged-${weight}"; value = merged weight; }
        { name = "nerd-${weight}"; value = nerd weight; }
      ])
      weights
  );

  # The upstream build, exposed so `nix build .#serif-sarasa` can be bisected on
  # its own — it is the expensive half of this family and the half most likely
  # to break on an upstream pin bump.
  extras.sarasa = sarasaBuild;

  release = {
    inherit family profile region readme verify;
    weight = "Regular";
    stem = ps;
    fontDir = pkgs.runCommand "serif-release-fonts" { } ''
      mkdir -p $out
      ${lib.concatMapStringsSep "\n" (w: "cp ${nerd w}/*.ttf $out/") weights}
    '';
    # serif redistributes no licence files of its own: package-release.sh
    # shipped the README note above and nothing else, and inventing a licences
    # directory here would be a product change wearing a refactor's clothes.
    licenseDir = null;
  };
}
