# Turn the artifacts declared in each font.toml into content-addressed Nix
# derivations. The manifest owns URL, hash, canonical filename and fetch kind;
# this module contains no family-specific translation table.
{ pkgs
, lib ? pkgs.lib
, root
,
}:

let
  readManifest = import ../lib/manifest.nix;
  families = lib.filter
    (name: builtins.pathExists (root + "/${name}/font.toml"))
    (lib.attrNames (builtins.readDir root));
  manifests = lib.genAttrs families (readManifest root);

  artifactsFor =
    family:
    lib.concatMap
      (source: lib.attrValues (source.artifacts or { }))
      (lib.attrValues manifests.${family}.data.sources);

  fetchedFor = family: lib.filter (artifact: (artifact.fetch or "plain") != "embedded")
    (artifactsFor family);

  specsFor =
    family:
    let
      artifacts = fetchedFor family;
      specs = lib.listToAttrs (map
        (artifact: {
          name = artifact.file;
          value = artifact;
        })
        artifacts);
    in
    assert lib.assertMsg (lib.length artifacts == lib.length (lib.attrNames specs))
      "nix/sources: ${family}/font.toml declares duplicate canonical artifact filenames";
    specs;

  mkPlain =
    file: artifact:
    pkgs.fetchurl {
      name = file;
      inherit (artifact) url sha256;
    };

  mkZipMember =
    file: artifact:
    pkgs.runCommand file
      {
        outputHashMode = "flat";
        outputHashAlgo = "sha256";
        outputHash = artifact.sha256;
        nativeBuildInputs = [
          pkgs.python3
          pkgs.curl
          pkgs.cacert
        ];
        SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
        inherit (artifact) url member;
        sha = artifact.sha256;
      }
      ''
        python3 ${root}/tools/fetch_zip_member.py \
          "$url" --member "$member" --out "$out" --sha256 "$sha"
      '';

  mkArtifact =
    file: artifact:
    if (artifact.fetch or "plain") == "plain" then
      mkPlain file artifact
    else if artifact.fetch == "zip-member" then
      mkZipMember file artifact
    else
      throw "nix/sources: unsupported fetch kind ${artifact.fetch}";

  # Sarasa is a source tree rather than a file artifact.
  sarasa = manifests.serif.data.sources.sarasa;
  sarasaSrc = pkgs.fetchFromGitHub {
    name = "Sarasa-Gothic-source";
    owner = "be5invis";
    repo = "Sarasa-Gothic";
    rev = sarasa.commit;
    inherit (sarasa) hash;
  };

  # Every family that declares [nerd] must use the exact same checkout.
  patcherUsers = lib.filter (family: manifests.${family}.data ? nerd) families;
  referenceFamily = lib.head patcherUsers;
  patcherPin = manifests.${referenceFamily}.data.nerd;
  disagreeing = lib.filter
    (family:
      let pin = manifests.${family}.data.nerd;
      in pin.commit != patcherPin.commit || pin.hash != patcherPin.hash)
    patcherUsers;

  fontPatcher =
    assert lib.assertMsg (disagreeing == [ ])
      (
        "nix/sources: font-patcher pins disagree with "
        + "${referenceFamily}/font.toml: ${lib.concatStringsSep ", " disagreeing}"
      );
    pkgs.fetchgit {
      name = "nerd-fonts-patcher";
      url = "https://github.com/ryanoasis/nerd-fonts";
      rev = patcherPin.commit;
      inherit (patcherPin) hash;
      sparseCheckout = [
        "font-patcher"
        "glyphnames.json"
        "bin/scripts/name_parser"
        "src/glyphs"
      ];
    };

  perFamily = lib.genAttrs families (
    family:
    lib.mapAttrs mkArtifact (specsFor family)
    // lib.optionalAttrs (lib.elem family patcherUsers) {
      "font-patcher" = fontPatcher;
    }
  );

  entries = lib.concatMap
    (
      family:
      lib.mapAttrsToList
        (file: artifact: {
          inherit family file;
          kind = artifact.fetch or "plain";
          inherit (artifact) sha256;
          drv = perFamily.${family}.${file};
        })
        (specsFor family)
    )
    families;

in
{
  inherit
    families
    manifests
    perFamily
    entries
    fontPatcher
    sarasaSrc
    ;
}
