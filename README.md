# font

Personal / project font build recipes.

## serif/

**Coding product: SarasaNZSSlab NFM** — MonoSlab Latin + 霞鹜新致宋 Opt CJK, **Nerd Font Mono**, 2:1 dual-width SC.

```bash
cd serif && ./scripts/build.sh
# → out/nerd/SarasaNZSSlabNFM-{Regular,Bold}.ttf
```

Package for a GitHub Release:

```bash
cd serif && ./scripts/package-release.sh 0.1.0
# → dist/SarasaNZSSlabNFM-0.1.0.zip
```

Details: [`serif/README.md`](serif/README.md).

## sans/

**Coding product: KitPlex Dual** — IBM Plex Mono + IBM Plex Sans SC, dual-width **EN 550 / CJK 1100**.

```bash
cd sans && ./scripts/build.sh
# → out/KitPlexDual-{Regular,Bold}.ttf
```

Upstream pins (release tags + zip SHA-256) live in [`sans/pins.env`](sans/pins.env).

Details: [`sans/README.md`](sans/README.md).
