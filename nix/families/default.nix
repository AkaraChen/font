# The seven families, all of them building from source in Nix.
#
# serif joined last (KIT-280): it runs the upstream Sarasa toolchain — quilt
# stack, npm build, its own CJK master swapped into sources/shs — and that took
# a phase of its own. With it here, no family has a shell pipeline any more and
# `<family>/scripts/` holds only hand-run diagnostics.
#
# Each family module returns the same four things:
#
#   steps     the per-step derivations, named by the granularity contract
#   out       the products, laid out the way <family>/out used to be — this is
#             what `just build` materialises and what the fingerprint net reads
#   verify    the family's gate, as a check rather than a build step
#   release   what `packaged` needs to build the release archive
#
# …and optionally `extras`: derivations that are real build inputs but not steps
# of the granularity contract. serif's upstream Sarasa build is the only one —
# see the comment on it for why a per-weight derivation would be wrong.
{ pkgs
, lib
, granularity
, sources
, fontkit
, root
,
}:

let
  support = import ./support.nix {
    inherit
      pkgs
      lib
      granularity
      sources
      fontkit
      root
      ;
  };

  families = {
    casual = ./casual.nix;
    handwriting = ./handwriting.nix;
    pixel = ./pixel.nix;
    rounded = ./rounded.nix;
    sans = ./sans.nix;
    serif = ./serif.nix;
    typewriter = ./typewriter.nix;
  };

  built = lib.mapAttrs
    (
      family: module:
        import module {
          inherit pkgs lib support sources;
          manifest = sources.manifests.${family};
        }
    )
    families;

  # --- packaged -------------------------------------------------------------
  #
  # The last step in the granularity contract, and the only one with a `format`
  # axis. It is generic because packaging is: the six package-release.sh scripts
  # differed only in which licence files they copied and what their README
  # heredoc said, and both of those are data now.
  packaged =
    family: rel:
    let
      version = sources.manifests.${family}.data.naming.version or "0.1.0";
      # A family may redistribute no licence files of its own (serif ships an
      # upstream-pointer note instead), so `licenseDir = null` is a real answer
      # rather than an empty directory nobody would notice was empty.
      licenses =
        if rel.licenseDir == null then
          [ ]
        else
          lib.mapAttrsToList (name: _: "--license ${rel.licenseDir}/${name}") (
            builtins.readDir rel.licenseDir
          );
      # An archive ships every format its matrix entry declares, so the `format`
      # axis names them all rather than naming one and quietly shipping two.
      # Six families declare only `ttf` and their derivation names do not move.
      formats = rel.formats or [ "ttf" ];
      globs = lib.concatMapStringsSep " " (f: "${rel.fontDir}/*.${f}") formats;
    in
    support.step "packaged"
      {
        inherit (rel)
          family
          profile
          region
          weight
          ;
        format = lib.concatStringsSep "-" formats;
      }
      {
        buildCommand = ''
          mkdir -p $out

          # The gate is a build input, not a re-run: ${rel.verify} only exists
          # if this family's products passed it, so a red gate is a build
          # failure upstream of here rather than a check nobody remembered to
          # invoke before uploading a release.
          test -e ${rel.verify}

          sed 's/@version@/${version}/' ${rel.readme} > README.txt
          fontkit package \
            --stem ${rel.stem} \
            --version ${version} \
            --out $out \
            --readme README.txt \
            ${lib.concatStringsSep " \\\n            " licenses} \
            ${globs}
        '';
      };

in
{
  inherit support;

  # The raw per-family modules, for nix/checks.nix.
  byFamily = built;

  # `nix build .#sans` → the products, in the out/ layout.
  outputs = lib.mapAttrs (_: fam: fam.out) built;

  # `nix build .#sans-release`           → the zip a GitHub Release ships.
  # `nix build .#handwriting-text-release` → a second profile's zip.
  #
  # Two profiles are two products, so they are two archives: they have different
  # family names, different weight sets and different formats, and a reader
  # downloading a reading face should not also get 4000 Nerd icons.
  releases =
    lib.mapAttrs'
      (family: fam: lib.nameValuePair "${family}-release" (packaged family fam.release))
      built
    // lib.listToAttrs (
      lib.concatLists (
        lib.mapAttrsToList
          (family: fam:
            lib.mapAttrsToList
              (name: rel: lib.nameValuePair "${family}-${name}-release" (packaged family rel))
              (fam.extraReleases or { }))
          built
      )
    );

  # `nix build .#sans-merged-Bold` → one step, for bisecting a fingerprint diff
  # or feeding a calibration run.
  steps = lib.listToAttrs (
    lib.concatLists (
      lib.mapAttrsToList
        (
          family: fam:
            lib.mapAttrsToList (name: drv: lib.nameValuePair "${family}-${name}" drv) fam.steps
        )
        built
    )
  );

  # `nix build .#serif-sarasa` → a family's non-contract build inputs, for
  # bisecting them without building the family around them.
  extras = lib.listToAttrs (
    lib.concatLists (
      lib.mapAttrsToList
        (
          family: fam:
            lib.mapAttrsToList (name: drv: lib.nameValuePair "${family}-${name}" drv)
              (fam.extras or { })
        )
        built
    )
  );

  # `nix build .#sans-verify` → the family's gate, which means building the
  # family. Deliberately not in `flake.checks`: `just check` is the seconds-long
  # gate a contributor runs before pushing, and folding six multi-hour font
  # builds into it would make everyone stop running it. CI's build matrix builds
  # these; the release step depends on them.
  verifies = lib.mapAttrs' (family: fam: lib.nameValuePair "${family}-verify" fam.verify) built;
}
