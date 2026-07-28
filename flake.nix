{
  description = "AKR fonts — pinned build toolchain (Phase 0: devShell only)";

  inputs = {
    # Stable channel on purpose: this is a toolchain pin, not a place to chase
    # upstream. nixos-unstable currently has an unbuilt nodejs bump, so the whole
    # devShell would compile Node from source on every cold machine and in CI.
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAllSystems (pkgs:
        let
          # Every Python dependency that was previously `pip install`-ed from one of
          # the eight scattered, unpinned call sites in */scripts/common.sh.
          # `pathops` is skia-pathops; nixpkgs already builds it (gn + ninja + Skia,
          # with darwin aarch64/x86_64 patches), so no overlay is needed here.
          pythonEnv = pkgs.python3.withPackages (ps: with ps; [
            fonttools
            brotli
            skia-pathops
            pillow
            freetype-py
            numpy
            uharfbuzz
            wcwidth
            # afdko ships otc2otf / otf2ttf as console scripts, which Sarasa's
            # verdafile.mjs calls during source prep. It was never in this repo's
            # need_cmd list — serif only ever built because the maintainer's
            # machine happened to have AFDKO installed.
            afdko
          ]);

          # nixpkgs hard-disables cairo in harfbuzz ("development purposes only"),
          # which drops hb-view — the one harfbuzz binary pixel/scripts/preview.sh
          # actually calls. Without this override the shell silently falls through
          # to whatever hb-view is on the host PATH (on the maintainer's Mac that is
          # homebrew's), which is precisely the failure mode this phase exists to
          # kill. The utilities live in the `dev` output.
          harfbuzzWithView = pkgs.harfbuzzFull.overrideAttrs (old: {
            buildInputs = (old.buildInputs or [ ]) ++ [ pkgs.cairo ];
            mesonFlags =
              (builtins.filter (f: f != (pkgs.lib.mesonEnable "cairo" false)) old.mesonFlags)
              ++ [ (pkgs.lib.mesonEnable "cairo" true) ];
          });

          # System tools. Everything here was previously discovered with `need_cmd`
          # or called bare, i.e. "whatever happened to be on the maintainer's PATH".
          systemTools = with pkgs; [
            curl
            git
            quilt
            unzip
            zip
            p7zip
            fontforge
            ttfautohint
            nodejs
            just
            jq
            harfbuzzWithView.dev # hb-view / hb-shape / hb-subset
          ];
        in
        {
          default = pkgs.mkShell {
            name = "akr-fonts";
            packages = systemTools ++ [ pythonEnv ];

            # Pin the interpreter so the family scripts skip venv creation and
            # `pip install` entirely. common.sh honours this and hard-fails if the
            # interpreter cannot import what that family needs.
            FONTKIT_PYTHON = "${pythonEnv}/bin/python3";

            # fontTools honours SOURCE_DATE_EPOCH for head.modified. fontforge's
            # output still is not byte-reproducible (it embeds its own timestamps),
            # which is exactly why the regression net fingerprints normalised
            # advance/name/feature dumps instead of TTF sha256s.
            SOURCE_DATE_EPOCH = "0";

            # fontforge is on PATH here, so the docker fallback must never be taken.
            NERD_PATCH_METHOD = "fontforge";

            # The banner goes to stderr: `nix develop --command <tool>` is used to
            # pipe tool output around, and a greeting on stdout would corrupt it.
            shellHook = ''
              export FONTKIT_REPO_ROOT="$PWD"
              {
                echo "akr-fonts devShell — $(python3 --version), $(fontforge --version 2>&1 | head -1)"
                echo "run 'just' for the recipe list"
              } >&2
            '';
          };
        });

      formatter = forAllSystems (pkgs: pkgs.nixpkgs-fmt);
    };
}
