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

## kai/

**Coding product: RadonWenKai NFM** — Monaspace **Radon** Latin (handwriting mono, ligatures,
pre-patched Nerd icons) + **霞鹜文楷 LXGW WenKai** CJK, **Nerd Font Mono**, 2:1 dual width
(EN 500 / CJK 1000), CJK sheared **7.5°** to match Radon's measured lean.

```bash
cd kai && ./scripts/build.sh
# → out/RadonWenKaiNFM-{Regular,Bold}.ttf
```

Monaspace parks its ligatures in `ss01`–`ss10`; the build folds them into default `calt` and
gates that with a HarfBuzz shaping test. Weight pairing and slant are measured, not guessed
(`./scripts/calibrate-stroke.sh`).

Details: [`kai/README.md`](kai/README.md).
