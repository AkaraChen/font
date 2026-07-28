# font

Personal / project font build recipes.

## Building

The toolchain is pinned by a Nix flake; `just` is a thin alias layer over it.

```bash
just dev              # enter the pinned shell (fontforge, ttfautohint, afdko, node, python deps)
just build sans       # nix build .#sans, materialised into sans/out
just gate sans        # run the family's 2:1 / EAW / Nerd / feature gate
just release sans     # build the release zip (depends on the gate)
just verify sans      # diff the products against the committed fingerprint baseline
just --list           # everything else
```

Six of the seven families are Nix derivations, one per build step
([`nix/families/`](nix/families)) — there is no `<family>/scripts/build.sh` to
run any more, and nothing to install first. serif still runs its own shell
pipeline because it drives the upstream Sarasa toolchain; moving that into Nix
is its own piece of work. See [`docs/build-toolchain.md`](docs/build-toolchain.md).

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
just build sans
# → out/nerd/LilexSansSCNFM-{Regular,Bold}.ttf
```

Package for a GitHub Release:

```bash
just release sans
# → result-*-release/LilexSansSCNFM-0.1.0.zip
```

Upstream pins live in [`sans/font.toml`](sans/font.toml).

Details: [`sans/README.md`](sans/README.md).

## pixel/

**Coding product: FusionPixel12 NFM** — [Fusion Pixel](https://github.com/TakWolf/fusion-pixel-font) 12px mono + **pixelized** programming ligatures (`calt`) + **Nerd Font Mono** (icons not pixelized).

```bash
just build pixel
# → out/nerd/FusionPixel12NFM-Regular.ttf
```

Details: [`pixel/README.md`](pixel/README.md).

## handwriting/

**Coding product: RadonWenKai NFM** — Monaspace **Radon** Latin (handwriting mono, ligatures,
pre-patched Nerd icons) + **霞鹜文楷 LXGW WenKai** CJK, **Nerd Font Mono**, 2:1 dual width
(EN 500 / CJK 1000), CJK sheared **7.5°** to match Radon's measured lean.

```bash
just build handwriting
# → out/RadonWenKaiNFM-{Regular,Bold}.ttf
```

Monaspace parks its ligatures in `ss01`–`ss10`; the build folds them into default `calt` and
gates that with a HarfBuzz shaping test. Weight pairing and slant are measured, not guessed
(`./scripts/calibrate-stroke.sh`).

Details: [`handwriting/README.md`](handwriting/README.md).

## typewriter/

**Coding product: CourierPrimeZhuque NFM** — [Courier Prime](https://github.com/quoteunquoteapps/CourierPrime)
slab mono Latin + [朱雀仿宋 Zhuque Fangsong](https://github.com/TrionesType/zhuque) CJK + **Nerd Font Mono**,
dual-width **EN 600 / CJK 1200** (Prime UPM 2048→1000).

Name recipe (same style as `LilexSansSC NFM`): **CourierPrime** + **Zhuque** + **NFM**.

```bash
just build typewriter
# → out/nerd/CourierPrimeZhuqueNFM-{Regular,Bold}.ttf
```

CJK weights are stem-measured embolden of Zhuque Regular. Upstream Alegreya Latin inside Zhuque is dropped.

Details: [`typewriter/README.md`](typewriter/README.md).

## rounded/ （圆体）

**Coding product: IosevkaCurlyRHR NFM / 圆体** — **Iosevka Curly** (ss20 Curly Style, sans — not NSlab)
Latin + **Resource Han Rounded SC** CJK + **Nerd Font Mono**, dual-width **EN 500 / CJK 1000**.

```bash
just build rounded
# → out/nerd/IosevkaCurlyRHRNFM-{Regular,Bold}.ttf
```

Upstream pins: [`rounded/font.toml`](rounded/font.toml). Details: [`rounded/README.md`](rounded/README.md).

## casual/

**Coding product: RecursiveYozai Dual** — Recursive **Mono Casual** Latin + **Yozai 悠哉** CJK,
strict **2:1** dual width (EN 500 / CJK 1000), measured stroke match (no Nerd in v0.1).

```bash
just build casual
# → out/RecursiveYozaiDual-{Regular,Bold}.ttf
```

Upstream pins: [`casual/font.toml`](casual/font.toml). Details: [`casual/README.md`](casual/README.md).
