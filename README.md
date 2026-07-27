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

## radon/

**Coding product: RadonWenKai Dual / NFM** — Monaspace **Radon** Latin + 霞鹜文楷 Medium CJK, dual-width **EN 620 / CJK 1240**, coding ligatures (`calt`/`dlig`), mild CJK oblique, measured stem embolden, optional Nerd Font Mono.

```bash
cd radon && ./scripts/build.sh
# → out/RadonWenKaiDual-{Regular,Bold}.ttf
# → out/nerd/RadonWenKaiNFM-{Regular,Bold}.ttf
```

Details: [`radon/README.md`](radon/README.md).
