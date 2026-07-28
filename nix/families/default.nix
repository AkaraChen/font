# The six families that build from source in Nix.
#
# serif is not here on purpose: it runs the upstream Sarasa toolchain (clone +
# quilt stack + npm build) and moving that into a derivation is its own issue.
# Until then it keeps its shell pipeline, which is why `<family>/scripts/` still
# exists for exactly one family.
#
# Each family module returns the same four things:
#
#   steps     the per-step derivations, named by the granularity contract
#   out       the products, laid out the way <family>/out used to be — this is
#             what `just build` materialises and what the fingerprint net reads
#   verify    the family's gate, as a check rather than a build step
#   release   what `packaged` needs to build the release archive
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
      version = sources.manifests.${family}.data.naming.version;
      licenses = lib.mapAttrsToList (name: _: "--license ${rel.licenseDir}/${name}") (
        builtins.readDir rel.licenseDir
      );
    in
    support.step "packaged"
      {
        inherit (rel)
          family
          profile
          region
          weight
          ;
        format = "ttf";
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
            ${rel.fontDir}/*.ttf
        '';
      };

in
{
  inherit support;

  # The raw per-family modules, for nix/checks.nix.
  byFamily = built;

  # `nix build .#sans` → the products, in the out/ layout.
  outputs = lib.mapAttrs (_: fam: fam.out) built;

  # `nix build .#sans-release` → the zip a GitHub Release ships.
  releases = lib.mapAttrs' (family: fam: lib.nameValuePair "${family}-release" (packaged family fam.release)) built;

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

  # `nix build .#sans-verify` → the family's gate, which means building the
  # family. Deliberately not in `flake.checks`: `just check` is the seconds-long
  # gate a contributor runs before pushing, and folding six multi-hour font
  # builds into it would make everyone stop running it. CI's build matrix builds
  # these; the release step depends on them.
  verifies = lib.mapAttrs' (family: fam: lib.nameValuePair "${family}-verify" fam.verify) built;
}
