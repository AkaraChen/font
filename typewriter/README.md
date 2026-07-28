# typewriter — TypewriterMono NFM

Coding dual-width face: **Courier Prime** (Latin slab mono) + **朱雀仿宋 Zhuque Fangsong** (CJK) + **Nerd Font Mono**, strict **2:1** grid. Typewriter / archive / technical-manual vibe — distinct from `serif/` (IosevkaNSlab + 新致宋).

| Component | Source | Pin |
| --- | --- | --- |
| Latin / mono | [Courier Prime](https://github.com/quoteunquoteapps/CourierPrime) slab TTF (**not** Code / Sans) | commit **7fd585a** · font **v3.018** |
| CJK | [朱雀仿宋 Zhuque Fangsong](https://github.com/TrionesType/zhuque) | **v0.212** (technical preview) |
| Icons | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) FontPatcher | **v3.4.0** (`--complete --single-width-glyphs`) |
| Grid | EN cell / CJK cell | **600 / 1200** |
| Symbol widths | EAW-correct (N/Na/H → half, W/F → full; A left alone) | `narrow-symbol-widths.py` after Nerd |
| Intermediate | Regular + Bold (pre-Nerd) | `out/TypewriterMonoDual-{Regular,Bold}.ttf` |
| Product | Regular + Bold (Nerd Mono) | `out/nerd/TypewriterMonoNFM-{Regular,Bold}.ttf` |
| Family name | Project product name (not upstream RFN) | **TypewriterMono NFM** |
| Metrics gate | `verify-2to1.py --expect-half 600 --check-nerd --check-eaw` | after Nerd + EAW fix |

Courier Prime ships UPM **2048** mono cell **1228**; the merge normalizes to UPM **1000** (EN **600**). Zhuque’s embedded Alegreya Latin is **dropped** — only CJK-side ranges are imported. Zhuque is single-weight; both product weights stem-match Latin verticals via embolden (`CJK_EMBOLDEN_REGULAR=8`, `CJK_EMBOLDEN_BOLD=32`, via `serif/tools/embolden_cjk.py`) so mixed CJK/EN coding text reads at the same optical weight.

v1 does **not** add programming `calt` ligatures (Courier Prime has none). Optional later: slashed `0`, `1`/`l`/`I`/`|` tuning.

## Name recipe

| Token | Meaning |
| --- | --- |
| **TypewriterMono** | Product family (typewriter / archive coding dual-width) |
| **Dual** | Intermediate pre-Nerd merge only |
| **NFM** | Nerd Font Mono product (complete icons, single-width glyphs) |

- Intermediate family (name ID 1): `TypewriterMono Dual`
- Product family (name ID 1): `TypewriterMono NFM` (18 chars, Windows ≤31)
- PostScript / file stem: `TypewriterMonoNFM`
- Not an official Courier Prime, Zhuque, or Nerd Fonts face. Upstream OFLs may reserve names — this product uses a distinct family name.

## Pins

Everything reproducible lives in [`pins.env`](pins.env):

- Courier Prime commit + TTF SHA-256
- Zhuque release tag + zip SHA-256
- Embolden strength for Bold CJK
- `EN_ADV` / `CJK_ADV` / vertical metrics / family names
- Nerd Fonts patcher tag + docker image digest

Do **not** bump pins casually; change them in a dedicated commit with a short rationale.

## Layout

```
typewriter/
  pins.env
  licenses/
    OFL-CourierPrime.txt
    OFL-Zhuque.txt
  scripts/
    build.sh               # one-shot fetch → prepare → merge → nerd → verify
    01-fetch-sources.sh
    02-prepare-cjk.sh      # Bold embolden (stem-matched)
    03-merge.sh            # Prime + Zhuque → Dual intermediate
    04-nerd-patch.sh
    05-verify.sh
    merge_typewriter.py
    rename_nerd_family.py
    fix-nerd-widths.py
    narrow-symbol-widths.py
    fix-terminal-metrics.py
    verify-2to1.py
    render-sample.py
    package-release.sh
  samples/
    coding-mixed.txt
    rendered/              # gitignored PNGs
  work/                    # gitignored downloads / venv / extract
  out/                     # gitignored intermediate Dual TTFs
  out/nerd/                # gitignored product NFM TTFs
  dist/                    # gitignored release zips
```

Embolden / stroke tools are reused from [`../serif/tools/`](../serif/tools/).

## Dependencies

- `bash`, `curl`, `unzip`, `zip`
- Python 3.10+ (`venv` or `uv`) → `fonttools`, `skia-pathops`, optional `Pillow`
- **Docker** (preferred) or **FontForge** for the Nerd Font patcher

```bash
# Debian/Ubuntu example
sudo apt install curl unzip zip python3-venv
# plus Docker, or: sudo apt install fontforge
```

## Build

```bash
cd typewriter
./scripts/build.sh
# → out/TypewriterMonoDual-{Regular,Bold}.ttf          (intermediate)
# → out/nerd/TypewriterMonoNFM-{Regular,Bold}.ttf      (product)
```

Step by step:

```bash
./scripts/01-fetch-sources.sh   # download pinned sources
./scripts/02-prepare-cjk.sh     # Regular+Bold CJK embolden (stem-matched)
./scripts/03-merge.sh           # merge EN=600 / CJK=1200
./scripts/04-nerd-patch.sh      # Nerd complete + half-cell icons + EAW
./scripts/05-verify.sh          # hard-fail if advances / flags / EAW drift
```

Force patcher backend: `NERD_PATCH_METHOD=docker|fontforge ./scripts/04-nerd-patch.sh`

### Sample render

```bash
# after build; needs Pillow in work/venv
work/venv/bin/python scripts/render-sample.py \
  --font out/nerd/TypewriterMonoNFM-Regular.ttf \
  --title "TypewriterMono NFM · EN 600 / CJK 1200"
# → samples/rendered/sample-{dark,light}.png
```

### Release package

```bash
./scripts/package-release.sh 0.1.0
# → dist/TypewriterMonoNFM-0.1.0.zip
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
python3 scripts/verify-2to1.py --expect-half 600 --check-nerd --check-eaw out/nerd/TypewriterMonoNFM-*.ttf
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

- **Product family:** `TypewriterMono NFM` (Regular / Bold)
- Upstream is **SIL OFL 1.1** (Courier Prime; Zhuque Fangsong)
- Nerd glyph sets follow the Nerd Fonts / individual icon-font licenses
- Keep `licenses/OFL-CourierPrime.txt` and `licenses/OFL-Zhuque.txt` with redistributions
- Build scripts in this folder: MIT (repo root) unless noted

## Upstream links

- Courier Prime: <https://github.com/quoteunquoteapps/CourierPrime>
- Zhuque Fangsong: <https://github.com/TrionesType/zhuque> · release [v0.212](https://github.com/TrionesType/zhuque/releases/tag/v0.212)
- Nerd Fonts: <https://github.com/ryanoasis/nerd-fonts>
