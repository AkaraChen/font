{
  description = "AKR fonts — pinned toolchain, pinned sources, shared fontkit build steps";

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

      granularity = import ./nix/granularity.nix { inherit (nixpkgs) lib; };
      sourcesFor = pkgs: import ./nix/sources { inherit pkgs; root = ./.; };
      fontkitFor = pkgs: pkgs.python3.pkgs.callPackage ./nix/fontkit.nix { };
    in
    {
      # The derivation-granularity contract (nix/granularity.nix). Exported as a
      # flake output because Phase 3 builds against it from outside this file,
      # and because `nix eval .#granularity.steps` is how you answer "what makes
      # this step rebuild?" without reading Nix.
      lib = { inherit granularity; };

      packages = forAllSystems (pkgs:
        let
          sources = sourcesFor pkgs;
        in
        {
          # The shared build steps, as a buildPythonPackage. The per-step
          # derivations in Phase 3 depend on this rather than on a checkout.
          fontkit = fontkitFor pkgs;

          # Every pinned upstream input, content-addressed. This is the GC root
          # CI keeps: one `nix build .#source-cache` materialises the whole
          # source layer, and tools/src-cache.sh serves every family out of it.
          source-cache = import ./nix/source-cache.nix { inherit pkgs sources; };

          # The single shared patcher — five families, one download.
          font-patcher = sources.fontPatcher;

          # serif's Sarasa tree, replacing `git clone --depth 1`. 304 MiB; the
          # largest input in the repo and the reason docs/caching.md splits the
          # CI cache into layers.
          sarasa-src = sources.sarasaSrc;
        }
        # Per-family source sets, for `nix build .#sources-sans`.
        // nixpkgs.lib.mapAttrs'
          (family: drvs:
            nixpkgs.lib.nameValuePair "sources-${family}"
              (pkgs.linkFarm "sources-${family}"
                (nixpkgs.lib.mapAttrsToList (name: path: { inherit name path; }) drvs)))
          sources.perFamily);

      # `just check` (nix flake check) builds fontkit, which runs its pytest
      # suite — the only automated gate on the shared build steps that does not
      # need a multi-hour font build first — alongside the pure-eval caching
      # checks in nix/checks.nix.
      checks = forAllSystems (pkgs:
        {
          fontkit = fontkitFor pkgs;
        }
        // import ./nix/checks.nix {
          inherit pkgs granularity;
          sources = sourcesFor pkgs;
        });

      devShells = forAllSystems (pkgs:
        let
          # The five build steps every family shares, formerly 17 near-identical
          # files under <family>/scripts/. Packaged so a bare `nix develop` can
          # run `python3 -m fontkit.<step>` and so Phase 1's per-step
          # derivations can depend on it without a repo checkout.
          fontkit = fontkitFor pkgs;

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
            # `just test` runs lib/tests against the working copy.
            pytest
            # afdko ships otc2otf / otf2ttf as console scripts, which Sarasa's
            # verdafile.mjs calls during source prep. It was never in this repo's
            # need_cmd list — serif only ever built because the maintainer's
            # machine happened to have AFDKO installed.
            afdko
          ] ++ [ fontkit ]);

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
