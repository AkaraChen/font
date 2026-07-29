# font

Personal / project font build recipes.

## Building

The toolchain is pinned by a Nix flake; `just` is a thin alias layer over it.

```bash
just dev                  # enter the pinned shell (fontforge, ttfautohint, afdko, node, python deps)
just matrix               # every (family, profile, region) cell there is to build
just build sans           # nix build .#sans, materialised into sans/out
just build sans coding tc # nix build .#sans-coding-tc, one cell of the matrix
just gate sans            # run the family's 2:1 / EAW / Nerd / feature gate
just release sans coding tc  # build one cell's release zip (depends on the gate)
just notes sans coding tc    # the release notes that zip ships with
just verify sans          # diff the products against the committed fingerprint baseline
just --list               # everything else
```

All seven families are Nix derivations, one per build step
([`nix/families/`](nix/families)) — there is no `<family>/scripts/build.sh` to
run any more, and nothing to install first. serif was the last holdout because
it drives the upstream Sarasa toolchain (patched tree + npm build); that lives
in [`nix/families/serif.nix`](nix/families/serif.nix) now.
See [`docs/build-toolchain.md`](docs/build-toolchain.md).

## Naming

Every product is **`AKR <Style> <Region> <Variant> [<Weight>]`**.

| segment | values |
| --- | --- |
| `AKR` | the house name — this repository. Fixed. |
| `<Style>` | `Slab` `Sans` `Round` `Type` `Pixel` `Hand` `Casual` |
| `<Region>` | `SC` `TC` `HK` `JP` `KR` — which CJK master the face draws |
| `<Variant>` | `NFM` Nerd Font Mono coding face · `Text` reading face · `Dual` dual-width coding face with no Nerd icons |

`font.toml` stores the *segments*, never the finished string: the region is a
build axis, so `AKR Sans SC NFM` and `AKR Sans JP NFM` are one `[naming]` table
and two matrix cells.

**Three weights need name IDs 16/17.** Windows' name ID 2 understands only
`Regular` / `Italic` / `Bold` / `Bold Italic`, so a `Light` cannot live there:

| name ID | Light | Regular | Bold |
| --- | --- | --- | --- |
| 1 (family, ≤ 31 chars) | `AKR Hand SC Text Light` | `AKR Hand SC Text` | `AKR Hand SC Text` |
| 2 (subfamily) | `Regular` | `Regular` | `Bold` |
| 16 / 17 | `AKR Hand SC Text` / `Light` | … / `Regular` | … / `Bold` |

The 31-character budget is measured against the *weighted* name ID 1, which is
the longest string a matrix cell can produce, and it is checked at manifest-load
time rather than discovered in a font menu.

### Migration from pre-rename releases

Full text for release notes: [`docs/naming-migration.md`](docs/naming-migration.md).


The families were renamed in one breaking change (KIT-282). No in-font aliases
were added, so **an editor or terminal configured with an old family name will
fall back to its default until you update it.** Old release tags keep their old
products; nothing published is rewritten.

| old family | new family |
| --- | --- |
| `SarasaNZSSlab NFM` | `AKR Slab SC NFM` |
| `LilexSansSC NFM` | `AKR Sans SC NFM` |
| `IosevkaCurlyRHR NFM` | `AKR Round SC NFM` |
| `CourierPrimeZhuque NFM` | `AKR Type SC NFM` |
| `FusionPixel12 NFM` | `AKR Pixel SC NFM` |
| `RadonWenKai NFM` | `AKR Hand SC NFM` |
| `RadonWenKai Text` | `AKR Hand SC Text` |
| `RecursiveYozai Dual` | `AKR Casual SC Dual` |

The old names carried upstream **reserved font names** — Iosevka, Monaspace,
Radon, Lilex, Plex, Recursive, LXGW, Sarasa, Courier Prime, Zhuque, Fusion Pixel
— in name ID 1, which the OFL does not allow in a redistributed derivative.
Attribution moved to where it belongs: name ID 5 (version string), name ID 10
(description), each family's README, and the release notes.

## Formats

Every product ships as a **TTF**, and that is the file to install. The others
are derived from it and are not interchangeable with it:

| format | what it is | who wants it |
| --- | --- | --- |
| `.ttf` | the product: TrueType outlines, hinting intact | everyone — editors, terminals, desktop |
| `.woff2` | the **same outlines**, Brotli-compressed container. Byte-identical `glyf` data, gated as such on every build | `@font-face` on the web |
| `.otf` | PostScript/CFF outlines, converted with qu2cu: curves refit within 1 font unit, **TrueType hinting dropped**, contours reversed | print / design tools that want CFF |

Which cells ship which is `[[build.matrix]]` in each `font.toml` — `just matrix`
prints it. The defaults are `coding = ttf + woff2` and `text = ttf + woff2 +
otf`: a coding face is hinted and lives in an editor, so an unhinted CFF version
of it would be a worse file in a nicer-sounding format, while a reading face
also gets set in print.

The OTF carries **its own fingerprint baseline** for the same reason it is a
separate product rather than a repackaging. See
[`docs/build-toolchain.md`](docs/build-toolchain.md#the-format-axis-phase-8-kit-283).

## serif/

**Coding product: AKR Slab SC NFM** — MonoSlab Latin + 霞鹜新致宋 Opt CJK, **Nerd Font Mono**, 2:1 dual-width SC.

```bash
just build serif
# → out/nerd/AKRSlabSCNFM-{Regular,Bold}.{ttf,woff2}
```

Package for a GitHub Release:

```bash
just release serif coding sc
# → result-serif-release/AKRSlabSCNFM-0.1.0.zip
```

Details: [`serif/README.md`](serif/README.md).

## sans/

**Coding product: AKR Sans SC NFM** — Lilex Latin (ligatures / OT features) + Plex Sans SC CJK + **Nerd Font Mono**, dual-width **EN 550 / CJK 1100**.

Name recipe (same style as `AKR Slab SC NFM`): **Lilex** + **SansSC** + **NFM**.

```bash
just build sans
# → out/nerd/AKRSansSCNFM-{Regular,Bold}.{ttf,woff2}
```

Package for a GitHub Release:

```bash
just release sans coding sc      # …or coding tc / jp / kr
# → result-sans-release/AKRSansSCNFM-0.1.0.zip
```

Upstream pins live in [`sans/font.toml`](sans/font.toml).

Details: [`sans/README.md`](sans/README.md).

## pixel/

**Coding product: AKR Pixel SC NFM** — [Fusion Pixel](https://github.com/TakWolf/fusion-pixel-font) 12px mono + **pixelized** programming ligatures (`calt`) + **Nerd Font Mono** (icons not pixelized).

```bash
just build pixel
# → out/nerd/AKRPixelSCNFM-Regular.{ttf,woff2}
```

Details: [`pixel/README.md`](pixel/README.md).

## handwriting/

**Coding product: AKR Hand SC NFM** — Monaspace **Radon** Latin (handwriting mono, ligatures,
pre-patched Nerd icons) + **霞鹜文楷 LXGW WenKai** CJK, **Nerd Font Mono**, 2:1 dual width
(EN 500 / CJK 1000), CJK sheared **7.5°** to match Radon's measured lean.

**Text product: AKR Hand SC Text** (Light / Regular / Bold) — the same two designs as a
**reading** face. No 2:1 declaration, no Nerd icons, East_Asian_Width left alone so `…` and `—`
keep WenKai's full width, and a typographic line box. The first `text` profile in the repo
(Phase 6, KIT-281), and the first family with a Light.

```bash
just build handwriting
# → out/AKRHandSCNFM-{Regular,Bold}.{ttf,woff2}
#   out/AKRHandSCText-{Light,Regular,Bold}.{ttf,woff2,otf}
```

Monaspace parks its ligatures in `ss01`–`ss10`; the coding build folds them into default `calt`
and gates that with a HarfBuzz shaping test, while the text build leaves them opt-in. Weight
pairing and slant are measured, not guessed (`./scripts/calibrate-stroke.sh`) — which is how
Light ended up paired with WenKai *Regular* rather than WenKai Light.

Details: [`handwriting/README.md`](handwriting/README.md).

## typewriter/

**Coding product: AKR Type SC NFM** — [Courier Prime](https://github.com/quoteunquoteapps/CourierPrime)
slab mono Latin + [朱雀仿宋 Zhuque Fangsong](https://github.com/TrionesType/zhuque) CJK + **Nerd Font Mono**,
dual-width **EN 600 / CJK 1200** (Prime UPM 2048→1000).

Name recipe (same style as `AKR Sans SC NFM`): **CourierPrime** + **Zhuque** + **NFM**.

```bash
just build typewriter
# → out/nerd/AKRTypeSCNFM-{Regular,Bold}.ttf
```

CJK weights are stem-measured embolden of Zhuque Regular. Upstream Alegreya Latin inside Zhuque is dropped.

Details: [`typewriter/README.md`](typewriter/README.md).

## rounded/ （圆体）

**Coding product: AKR Round SC NFM / 圆体** — **Iosevka Curly** (ss20 Curly Style, sans — not NSlab)
Latin + **Resource Han Rounded SC** CJK + **Nerd Font Mono**, dual-width **EN 500 / CJK 1000**.

```bash
just build rounded
# → out/nerd/AKRRoundSCNFM-{Regular,Bold}.ttf
```

Upstream pins: [`rounded/font.toml`](rounded/font.toml). Details: [`rounded/README.md`](rounded/README.md).

## casual/

**Coding product: AKR Casual SC Dual** — Recursive **Mono Casual** Latin + **Yozai 悠哉** CJK,
strict **2:1** dual width (EN 500 / CJK 1000), measured stroke match (no Nerd in v0.1).

```bash
just build casual
# → out/AKRCasualSCDual-{Regular,Bold}.ttf
```

Upstream pins: [`casual/font.toml`](casual/font.toml). Details: [`casual/README.md`](casual/README.md).
