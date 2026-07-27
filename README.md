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

**Coding product: LilexSansSC Dual** — Lilex Latin (ligatures / OT features) + Plex Sans SC CJK, dual-width **EN 550 / CJK 1100**.

Name recipe (same style as `SarasaNZSSlab NFM`): **Lilex** + **SansSC** + **Dual**.

```bash
cd sans && ./scripts/build.sh
# → out/LilexSansSCDual-{Regular,Bold}.ttf
```

Upstream pins (release tags + zip SHA-256) live in [`sans/pins.env`](sans/pins.env).

Details: [`sans/README.md`](sans/README.md).

## pixel/

**Coding product: FusionPixel12 NFM** — [Fusion Pixel](https://github.com/TakWolf/fusion-pixel-font) 12px mono + **pixelized** programming ligatures (`calt`) + **Nerd Font Mono** (icons not pixelized).

```bash
cd pixel && ./scripts/build.sh
# → out/nerd/FusionPixel12NFM-Regular.ttf
```

Details: [`pixel/README.md`](pixel/README.md).
