# Every pinned upstream input in the repo, as Nix derivations.
#
# The point is not tidiness. It is that a store path is keyed by (url, hash), so
# the five families that pin the same font-patcher commit collapse onto one
# derivation and one download — instead of the current five, one per
# <family>/work/downloads/. Adding the region axis in Phase 7 multiplies the
# build matrix; it must not multiply the fetching.
#
# Three kinds of source live here:
#
#   plain       fetchurl, hash straight out of pins.env
#   zipMembers  fixed-output derivation doing HTTP-range extraction — for the
#               Monaspace 315 MiB zip, where a plain fetchurl would trade a
#               4.6 MiB download for a 315 MiB one on every cold CI run
#   sarasa      fetchFromGitHub, replacing serif's `git clone --depth 1`
{ pkgs
, lib ? pkgs.lib
, root
,
}:

let
  pinsLib = import ../lib/pins.nix { inherit lib; };
  artifacts = import ./artifacts.nix;

  families = lib.attrNames artifacts;
  familyPins = lib.genAttrs families (f: pinsLib.readFamily root f);

  # --- plain fetchurl -------------------------------------------------------

  mkPlain =
    family: file: spec:
    let
      p = familyPins.${family};
    in
    pkgs.fetchurl {
      name = file;
      url = p.get spec.url;
      sha256 = p.get spec.sha256;
    };

  # --- ranged zip member (fixed-output, has network in the sandbox) ---------

  # The pinned sha256 of the *extracted member* doubles as the FOD's output
  # hash, so this adds no hash to keep in sync: the number already in pins.env
  # is exactly the number Nix checks.
  mkZipMember =
    family: file: spec:
    let
      p = familyPins.${family};
      # Repo-level, not family-level: nothing about HTTP-range extraction is
      # specific to handwriting, and it was only under handwriting/scripts/
      # because that is the family whose upstream ships a 315 MiB zip.
      extractor = root + "/tools/fetch_zip_member.py";
    in
    pkgs.runCommand file
      {
        outputHashMode = "flat";
        outputHashAlgo = "sha256";
        outputHash = p.get spec.sha256;

        nativeBuildInputs = [
          pkgs.python3
          pkgs.curl
          pkgs.cacert
        ];
        SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";

        url = p.get spec.url;
        member = p.get spec.member;
        sha = p.get spec.sha256;
      }
      ''
        python3 ${extractor} "$url" --member "$member" --out "$out" --sha256 "$sha"
      '';

  # --- Sarasa Gothic source tree -------------------------------------------

  sarasaSrc =
    let
      p = familyPins.serif;
    in
    pkgs.fetchFromGitHub {
      name = "Sarasa-Gothic-source";
      owner = "be5invis";
      repo = "Sarasa-Gothic";
      rev = p.get "SARASA_COMMIT";
      hash = p.get "SARASA_SRC_HASH";
    };

  # --- shared: the Nerd Fonts patcher --------------------------------------
  #
  # A commit, not a release asset. `FontPatcher.zip` only exists for tagged
  # releases, and the newest is still v3.4.0 (2025-04) shipping font-patcher
  # 4.20.3 — while every product this repo has ever released from CI was patched
  # by the `nerdfonts/patcher` container, which is built from master and was
  # shipping 4.26.0. Pinning the release meant shipping one patcher and claiming
  # another; pinning the commit the container was built from is what makes the
  # claim true. See docs/build-toolchain.md.
  #
  # Sparse, because the repo is 27 GB: `patched-fonts/` holds every font Nerd
  # Fonts publishes. The four paths below are the whole patcher.
  patcherUsers = lib.filter (f: familyPins.${f}.pins ? NERD_FONTS_PATCHER_COMMIT) families;

  referenceFamily = lib.head patcherUsers;

  patcherPin =
    let
      p = familyPins.${referenceFamily};
    in
    {
      rev = p.get "NERD_FONTS_PATCHER_COMMIT";
      hash = p.get "NERD_FONTS_PATCHER_HASH";
    };

  # A family that drifts its patcher pin would silently get a second store path
  # and quietly undo the whole point. Catch it at eval time instead.
  disagreeing = lib.filter
    (
      f:
      familyPins.${f}.get "NERD_FONTS_PATCHER_COMMIT" != patcherPin.rev
      || familyPins.${f}.get "NERD_FONTS_PATCHER_HASH" != patcherPin.hash
    )
    patcherUsers;

  fontPatcher =
    assert lib.assertMsg (disagreeing == [ ])
      (
        "nix/sources: font-patcher pins disagree, so the checkout would no longer "
        + "collapse to one store path. ${lib.concatStringsSep ", " disagreeing} differ "
        + "from ${referenceFamily}/pins.env (NERD_FONTS_PATCHER_COMMIT / _HASH)."
      );
    pkgs.fetchgit {
      name = "nerd-fonts-patcher";
      url = "https://github.com/ryanoasis/nerd-fonts";
      inherit (patcherPin) rev hash;
      sparseCheckout = [
        "font-patcher"
        "glyphnames.json"
        "bin/scripts/name_parser"
        "src/glyphs"
      ];
    };

  # --- assembly -------------------------------------------------------------

  # One flat attrset per family: canonical filename -> derivation. `fontPatcher`
  # is deliberately the *same* derivation in every family that uses it.
  perFamily = lib.genAttrs families (
    family:
    let
      spec = artifacts.${family};
      plain = lib.mapAttrs (mkPlain family) (spec.plain or { });
      members = lib.mapAttrs (mkZipMember family) (spec.zipMembers or { });
      patcher = lib.optionalAttrs (lib.elem family patcherUsers) {
        "font-patcher" = fontPatcher;
      };
    in
    plain // members // patcher
  );

  # Flat list of every artifact, used to build the content-addressed cache.
  # `sha256` is the pinned hex — for `plain` and `zipMembers` alike it is the
  # sha256 of the file's bytes, which is what the build scripts look up.
  #
  # font-patcher is deliberately absent: it is a checkout, not a file, so it has
  # no file hash to be addressed by. Nothing looks it up either — the derivation
  # steps take `sources.fontPatcher` directly, and serif (the last shell
  # consumer) is handed the realised path by `just build serif`.
  entries = lib.concatMap
    (
      family:
      let
        p = familyPins.${family};
        spec = artifacts.${family};
        of =
          kind: file: s: {
            inherit family file;
            sha256 = p.get s.sha256;
            drv = perFamily.${family}.${file};
            inherit kind;
          };
      in
      lib.mapAttrsToList (of "plain") (spec.plain or { })
      ++ lib.mapAttrsToList (of "zip-member") (spec.zipMembers or { })
    )
    families;

in
{
  inherit
    families
    familyPins
    perFamily
    entries
    fontPatcher
    sarasaSrc
    ;
}
