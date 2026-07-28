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

**Coding product: LilexSansSC NFM** — Lilex Latin (ligatures / OT features) + Plex Sans SC CJK + **Nerd Font Mono**, dual-width **EN 550 / CJK 1100**.

Name recipe (same style as `SarasaNZSSlab NFM`): **Lilex** + **SansSC** + **NFM**.

```bash
cd sans && ./scripts/build.sh
# → out/nerd/LilexSansSCNFM-{Regular,Bold}.ttf
```

Package for a GitHub Release:

```bash
cd sans && ./scripts/package-release.sh 0.1.0
# → dist/LilexSansSCNFM-0.1.0.zip
```

Upstream pins live in [`sans/pins.env`](sans/pins.env).

Details: [`sans/README.md`](sans/README.md).

## pixel/

**Coding product: FusionPixel12 NFM** — [Fusion Pixel](https://github.com/TakWolf/fusion-pixel-font) 12px mono + **pixelized** programming ligatures (`calt`) + **Nerd Font Mono** (icons not pixelized).

```bash
cd pixel && ./scripts/build.sh
# → out/nerd/FusionPixel12NFM-Regular.ttf
```

Details: [`pixel/README.md`](pixel/README.md).

## handwriting/

**Coding product: RadonWenKai NFM** — Monaspace **Radon** Latin (handwriting mono, ligatures,
pre-patched Nerd icons) + **霞鹜文楷 LXGW WenKai** CJK, **Nerd Font Mono**, 2:1 dual width
(EN 500 / CJK 1000), CJK sheared **7.5°** to match Radon's measured lean.

```bash
cd handwriting && ./scripts/build.sh
# → out/RadonWenKaiNFM-{Regular,Bold}.ttf
```

Monaspace parks its ligatures in `ss01`–`ss10`; the build folds them into default `calt` and
gates that with a HarfBuzz shaping test. Weight pairing and slant are measured, not guessed
(`./scripts/calibrate-stroke.sh`).

Details: [`handwriting/README.md`](handwriting/README.md).

## rounded/ （圆体）

**Coding product: IosevkaCurlyRHR NFM / 圆体** — **Iosevka Curly** (ss20 Curly Style, sans — not NSlab)
Latin + **Resource Han Rounded SC** CJK + **Nerd Font Mono**, dual-width **EN 500 / CJK 1000**.

```bash
cd rounded && ./scripts/build.sh
# → out/nerd/IosevkaCurlyRHRNFM-{Regular,Bold}.ttf
```

Upstream pins: [`rounded/pins.env`](rounded/pins.env). Details: [`rounded/README.md`](rounded/README.md).
