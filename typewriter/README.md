# typewriter — CourierPrimeZhuque NFM

Coding dual-width face: **Courier Prime** (Latin slab mono) + **朱雀仿宋 Zhuque Fangsong** (CJK) + **Nerd Font Mono**, strict **2:1** grid. Name recipe encodes sources (**CourierPrime** + **Zhuque** + **NFM**), same style as `LilexSansSC NFM`. Distinct from `serif/` (IosevkaNSlab + 新致宋).

| Component | Source | Pin |
| --- | --- | --- |
| Latin / mono | [Courier Prime](https://github.com/quoteunquoteapps/CourierPrime) slab TTF (**not** Code / Sans) | commit **7fd585a** · font **v3.018** |
| CJK | [朱雀仿宋 Zhuque Fangsong](https://github.com/TrionesType/zhuque) | **v0.212** (technical preview) |
| Icons | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) FontPatcher | **v3.4.0** (`--complete --single-width-glyphs`) |
| Grid | EN cell / CJK cell | **600 / 1200** |
| Symbol widths | EAW-correct (N/Na/H → half, W/F → full; A left alone) | `fontkit.narrow_symbol_widths` after Nerd |
| Intermediate | Regular + Bold (pre-Nerd) | `out/CourierPrimeZhuqueDual-{Regular,Bold}.ttf` |
| Product | Regular + Bold (Nerd Mono) | `out/nerd/CourierPrimeZhuqueNFM-{Regular,Bold}.ttf` |
| Family name | Source tokens + product tag | **CourierPrimeZhuque NFM** |
| Metrics gate | `fontkit.verify2to1 --expect-half 600 --check-nerd --check-eaw` | after Nerd + EAW fix |

Courier Prime ships UPM **2048** mono cell **1228**; the merge normalizes to UPM **1000** (EN **600**). Zhuque’s embedded Alegreya Latin is **dropped** — only CJK-side ranges are imported. Zhuque is single-weight; both product weights stem-match Latin verticals via embolden (`CJK_EMBOLDEN_REGULAR=8`, `CJK_EMBOLDEN_BOLD=32`, via `fontkit.embolden`) so mixed CJK/EN coding text reads at the same optical weight.

v1 does **not** add programming `calt` ligatures (Courier Prime has none). Optional later: slashed `0`, `1`/`l`/`I`/`|` tuning.

## Name recipe

| Token | Meaning |
| --- | --- |
| **CourierPrime** | Courier Prime (Latin slab mono) |
| **Zhuque** | 朱雀仿宋 Zhuque Fangsong (CJK) |
| **NFM** | Nerd Font Mono product (complete icons, single-width glyphs) |

- Intermediate family (name ID 1): `CourierPrimeZhuque Dual` (pre-Nerd only)
- Product family (name ID 1): `CourierPrimeZhuque NFM` (22 chars, Windows ≤31)
- PostScript / file stem: `CourierPrimeZhuqueNFM`
- Source-encoding label (same style as `LilexSansSC NFM`); not an official Courier Prime / Zhuque / Nerd Fonts face.

## Pins

Everything reproducible lives in [`font.toml`](font.toml):

- Courier Prime commit + TTF SHA-256
- Zhuque release tag + zip SHA-256
- Embolden strength for Bold CJK
- `EN_ADV` / `CJK_ADV` / vertical metrics / family names
- Nerd Fonts patcher tag

Do **not** bump pins casually; change them in a dedicated commit with a short rationale.

## Layout

```
typewriter/
  font.toml
  licenses/
    OFL-CourierPrime.txt
    OFL-Zhuque.txt
  scripts/
    render-sample.py       # diagnostic
  samples/
    coding-mixed.txt
    rendered/              # gitignored PNGs
  work/                    # gitignored downloads / venv / extract
  out/                     # gitignored intermediate Dual TTFs
  out/nerd/                # gitignored product NFM TTFs
  dist/                    # gitignored release zips
```

Embolden / stroke tools are shared: [`../lib/fontkit/`](../lib/fontkit/).

## Dependencies

- `bash`, `curl`, `unzip`, `zip`
- Python 3.10+ (`venv` or `uv`) → `fonttools`, `skia-pathops`, optional `Pillow`
- **FontForge** for the Nerd Font patcher (a build input; the container path was removed in KIT-277)


## Build

```bash
cd typewriter
just build typewriter
# → out/CourierPrimeZhuqueDual-{Regular,Bold}.ttf          (intermediate)
# → out/nerd/CourierPrimeZhuqueNFM-{Regular,Bold}.ttf      (product)
```

Step by step:

```bash
just steps typewriter                  # what the family is made of
just step typewriter cjk-prepared-Bold # build one step in isolation
just gate typewriter                   # hard-fail if advances / flags / EAW drift
```

### Sample render

```bash
# after build; run inside `nix develop` (Pillow, freetype-py)
python3 scripts/render-sample.py \
  --font out/nerd/CourierPrimeZhuqueNFM-Regular.ttf \
  --title "CourierPrimeZhuque NFM · EN 600 / CJK 1200"
# → samples/rendered/sample-{dark,light}.png
```

### Release package

```bash
just release typewriter
# → dist/CourierPrimeZhuqueNFM-0.1.0.zip
```

## Character policy

| Source | Role |
| --- | --- |
| **Courier Prime** (UPM→1000; cell 600) | ASCII, Latin extensions, digits, programming symbols, half-width punctuation |
| **Zhuque Fangsong** (advance → 1200, centred) | Han, CJK punctuation / symbols, fullwidth forms, kana / bopomofo |
| **Nerd Fonts** (`--single-width-glyphs`) | PUA icon sets at **half-cell** |

Not yet done (known limits):

1. Zhuque is technical preview — coverage and quality evolve; rare characters may be missing
2. No programming ligatures in v1
3. Optical size / x-height match between slab mono and fangsong is approximate
4. Italic (Latin-only) not planned for v1

## Verify

```bash
python3 -m fontkit.verify2to1 --expect-half 600 --check-nerd --check-eaw out/nerd/CourierPrimeZhuqueNFM-*.ttf
```

| Set | Expected |
| --- | ---: |
| `A` / printable ASCII | **600** |
| `中` / sample Han / fullwidth forms | **1200** (= 2× EN) |
| Nerd PUA icons | **600** (half-cell; present when `--check-nerd`) |
| `--check-eaw`: East_Asian_Width `N`/`Na`/`H` | **600** |
| `--check-eaw`: East_Asian_Width `W`/`F` | **1200** |
| `post.isFixedPitch` | **1** |
| PANOSE `bProportion` | **9** (Monospaced) |
| `OS/2.xAvgCharWidth` | **600** |

## Family / license

- **Product family:** `CourierPrimeZhuque NFM` (Regular / Bold)
- Upstream is **SIL OFL 1.1** (Courier Prime; Zhuque Fangsong)
- Nerd glyph sets follow the Nerd Fonts / individual icon-font licenses
- Keep `licenses/OFL-CourierPrime.txt` and `licenses/OFL-Zhuque.txt` with redistributions
- Build scripts in this folder: MIT (repo root) unless noted

## Upstream links

- Courier Prime: <https://github.com/quoteunquoteapps/CourierPrime>
- Zhuque Fangsong: <https://github.com/TrionesType/zhuque> · release [v0.212](https://github.com/TrionesType/zhuque/releases/tag/v0.212)
- Nerd Fonts: <https://github.com/ryanoasis/nerd-fonts>
