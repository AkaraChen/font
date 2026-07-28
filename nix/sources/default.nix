# Every pinned upstream input in the repo, as Nix derivations.
#
# The point is not tidiness. It is that a store path is keyed by (url, hash), so
# the five families that pin the same FontPatcher.zip collapse onto one
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
      extractor = root + "/${family}/scripts/fetch_zip_member.py";
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

  patcherUsers = lib.filter (f: familyPins.${f}.pins ? NERD_FONTS_PATCHER_URL) families;

  referenceFamily = lib.head patcherUsers;

  patcherPin =
    let
      p = familyPins.${referenceFamily};
    in
    {
      url = p.get "NERD_FONTS_PATCHER_URL";
      sha256 = p.get "NERD_FONTS_PATCHER_SHA256";
    };

  # A family that drifts its patcher pin would silently get a second store path
  # and quietly undo the whole point. Catch it at eval time instead.
  disagreeing = lib.filter
    (
      f:
      familyPins.${f}.get "NERD_FONTS_PATCHER_URL" != patcherPin.url
      || familyPins.${f}.get "NERD_FONTS_PATCHER_SHA256" != patcherPin.sha256
    )
    patcherUsers;

  fontPatcher =
    assert lib.assertMsg (disagreeing == [ ])
      (
        "nix/sources: FontPatcher pins disagree, so the zip would no longer collapse "
        + "to one store path. ${lib.concatStringsSep ", " disagreeing} differ from "
        + "${referenceFamily}/pins.env (NERD_FONTS_PATCHER_URL / _SHA256)."
      );
    pkgs.fetchurl {
      name = "FontPatcher.zip";
      inherit (patcherPin) url sha256;
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
        "FontPatcher.zip" = fontPatcher;
      };
    in
    plain // members // patcher
  );

  # Flat list of every artifact, used to build the content-addressed cache.
  # `sha256` is the pinned hex — for `plain` and `zipMembers` alike it is the
  # sha256 of the file's bytes, which is what the build scripts look up.
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
      ++ lib.optional (lib.elem family patcherUsers) {
        inherit family;
        file = "FontPatcher.zip";
        sha256 = patcherPin.sha256;
        drv = fontPatcher;
        kind = "shared";
      }
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
