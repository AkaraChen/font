# rounded — 圆体 / YuanTi NFM

Coding dual-width face: **Iosevka Curly** (Latin, ss20 Curly Style) + **Resource Han Rounded SC** (资源圆体 CJK) + **Nerd Font Mono**, strict **2:1** grid.

中文产品名 **圆体**：路径 / 绘图气质 — Latin 圆角端点 + CJK 转角圆角，与 `serif/`（Slab 宋）/`sans/`（几何黑）/`handwriting/`（楷）/`pixel/`（像素）切开。

| Component | Source | Pin |
| --- | --- | --- |
| Latin / mono | [Iosevka Curly](https://github.com/be5invis/Iosevka) **sans** package（**not** Slab / NSlab） | **v34.8.0** · Curly = **ss20 Curly Style** |
| CJK | [Resource Han Rounded](https://github.com/CyanoHao/Resource-Han-Rounded) CN | **v0.990** Regular + Bold |
| Icons | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) FontPatcher | **v3.4.0** (`--complete --single-width-glyphs`) |
| Grid | EN cell / CJK cell | **500 / 1000** |
| Intermediate | Regular + Bold (pre-Nerd) | `out/YuanTiDual-{Regular,Bold}.ttf` |
| Product | Regular + Bold (Nerd Mono) | `out/nerd/YuanTiNFM-{Regular,Bold}.ttf` |
| Family name | Project product (see RFN) | **YuanTi NFM** / 圆体 |
| Metrics gate | `verify-2to1.py --expect-half 500 --check-nerd --check-eaw` | after Nerd + EAW fix |

## Why Iosevka Curly (ss20), not other inherits

Iosevka stylistic inherits are pre-packaged “looks like font X” recipes. For **圆体 + Resource Han Rounded** the Latin should share **rounded terminals / soft corners**, not slab or pure DIN hardness.

| Inherit | Package / OT | Fit for 圆体 | Note |
| --- | --- | --- | --- |
| **ss20 Curly Style** | **Iosevka Curly** (this pin) | **Best** | Curly hooks / rounded terminals pair with RHR corner radius; matches product name |
| ss17 Recursive Mono | Iosevka SS17 | Good soft modern | Soft but less “path radius” narrative than Curly |
| ss14 JetBrains Mono | Iosevka SS14 | OK coding | Slightly soft; still more “product UI mono” than plotter |
| ss15 IBM Plex Mono | Iosevka SS15 | Industrial | Closer to technical lettering; corners harder vs RHR |
| ss05 Fira / ss09 Source Code Pro | SS05 / SS09 | Geometric | Clean, less rounded-path |
| ss01–ss13, ss16, ss18 | various | Weak | System / classic mono clones; not rounded |
| Default Iosevka (no ss) | Iosevka | Weak | Angular vs RHR soft corners |
| **Slab / NSlab / CurlySlab** | — | **Reject** | Collides with `serif/` MonoSlab story |

**Decision:** pin **Iosevka Curly (ss20 Curly Style, sans)**. Do not use NSlab. Future private-build-plans may bake extra cv (toothless-rounded, etc.) on top of Curly.

## Name recipe

| Token | Meaning |
| --- | --- |
| **YuanTi / 圆体** | Product family (rounded-path coding dual-width) |
| **Dual** | Intermediate pre-Nerd merge only |
| **NFM** | Nerd Font Mono product (complete icons, single-width glyphs) |

- Intermediate family (name ID 1): `YuanTi Dual`
- Product family (name ID 1): `YuanTi NFM` (10 chars, Windows ≤31)
- PostScript / file stem: `YuanTiNFM`
- Not an official Iosevka, Resource Han Rounded, or Nerd Fonts face. Upstream OFLs reserve **Iosevka** (and related Source Han names may apply to RHR lineage). **YuanTi** is a project label — rename review before public OFL redistribution.

## Pins

Everything reproducible lives in [`pins.env`](pins.env):

- Iosevka Curly release tag + zip SHA-256
- RHR-CN 7z SHA-256 + Regular/Bold TTF names
- `EN_ADV` / `CJK_ADV` / vertical metrics / family names
- Optional `CJK_EMBOLDEN_*` (default 0 — RHR has real Bold)
- Nerd Fonts patcher tag + docker image digest

Do **not** bump pins casually; change them in a dedicated commit with a short rationale.

## Layout

```
rounded/
  pins.env
  licenses/
    OFL-Iosevka.txt
    OFL-Resource-Han-Rounded.txt
  scripts/
    build.sh               # one-shot fetch → prepare → merge → nerd → verify
    01-fetch-sources.sh
    02-prepare-cjk.sh      # optional embolden (pins)
    03-merge.sh            # Curly + RHR → Dual intermediate
    04-nerd-patch.sh
    05-verify.sh
    merge_rounded.py
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

- `bash`, `curl`, `unzip`, `zip`, `7z` (for RHR `.7z`)
- Python 3.10+ (`venv` or `uv`) → `fonttools`, `skia-pathops` (optional embolden), optional `Pillow`
- **Docker** (preferred) or **FontForge** for the Nerd Font patcher

## Build

```bash
cd rounded
./scripts/build.sh
# → out/YuanTiDual-{Regular,Bold}.ttf
# → out/nerd/YuanTiNFM-{Regular,Bold}.ttf
```

Step by step:

```bash
./scripts/01-fetch-sources.sh
./scripts/02-prepare-cjk.sh
./scripts/03-merge.sh
./scripts/04-nerd-patch.sh
./scripts/05-verify.sh
```

### Sample render

```bash
work/venv/bin/python scripts/render-sample.py \
  --font out/nerd/YuanTiNFM-Regular.ttf \
  --title "圆体 YuanTi NFM · EN 500 / CJK 1000 · Iosevka Curly × RHR"
# → samples/rendered/sample-{dark,light}.png
```

### Release package

```bash
./scripts/package-release.sh 0.1.0
# → dist/YuanTiNFM-0.1.0.zip
```

## Character policy

| Source | Role |
| --- | --- |
| **Iosevka Curly** (scaled to EN_ADV; OT tables kept) | ASCII, Latin extensions, digits, programming symbols, ligatures when present |
| **Resource Han Rounded SC** (optional embolden; advance → CJK_ADV) | Han, CJK punctuation, fullwidth forms |
| **Nerd Fonts** (`--single-width-glyphs`) | PUA icons at half-cell |

## Verify

```bash
python3 scripts/verify-2to1.py --expect-half 500 --check-nerd --check-eaw out/nerd/YuanTiNFM-*.ttf
```

| Set | Expected |
| --- | ---: |
| `A` / printable ASCII | **500** |
| `中` / sample Han / fullwidth | **1000** |
| Nerd PUA icons | **500** |
| `post.isFixedPitch` | **1** |

## Family / license

- **Product family:** `YuanTi NFM` / 圆体 (Regular / Bold)
- Upstream **SIL OFL 1.1** (Iosevka RFN **Iosevka**; keep RHR OFL with redistributions)
- Nerd glyph sets follow Nerd Fonts / icon-font licenses
- Keep `licenses/OFL-Iosevka.txt` and `licenses/OFL-Resource-Han-Rounded.txt` with redistributions

## Upstream links

- Iosevka Curly: <https://github.com/be5invis/Iosevka/releases>
- Iosevka styles: <https://typeof.net/Iosevka/>
- Resource Han Rounded: <https://github.com/CyanoHao/Resource-Han-Rounded>
- Nerd Fonts: <https://github.com/ryanoasis/nerd-fonts>
