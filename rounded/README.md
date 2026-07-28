# rounded — 圆体 / IosevkaCurlyRHR NFM

Coding dual-width face: **Iosevka Curly** (Latin, ss20 Curly Style) + **Resource Han Rounded SC** (资源圆体 CJK) + **Nerd Font Mono**, strict **2:1** grid.

中文产品名 **圆体**：路径 / 绘图气质 — Latin 圆角端点 + CJK 转角圆角，与 `serif/`（Slab 宋）/`sans/`（几何黑）/`handwriting/`（楷）/`pixel/`（像素）切开。

| Component | Source | Pin |
| --- | --- | --- |
| Latin / mono | [Iosevka Curly](https://github.com/be5invis/Iosevka) **sans** package（**not** Slab / NSlab） | **v34.8.0** · Curly = **ss20 Curly Style** |
| CJK | [Resource Han Rounded](https://github.com/CyanoHao/Resource-Han-Rounded) CN | **v0.990** Regular + Bold |
| Icons | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) FontPatcher | **v3.4.0** (`--complete --single-width-glyphs`) |
| Grid | EN cell / CJK cell | **500 / 1000** |
| Intermediate | Regular + Bold (pre-Nerd) | `out/IosevkaCurlyRHRDual-{Regular,Bold}.ttf` |
| Product | Regular + Bold (Nerd Mono) | `out/nerd/IosevkaCurlyRHRNFM-{Regular,Bold}.ttf` |
| Family name | Source-encoding (see RFN) | **IosevkaCurlyRHR NFM**（方向绰号：圆体） |
| Metrics gate | `fontkit.verify2to1 --expect-half 500 --check-nerd --check-eaw` | after Nerd + EAW fix |

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

Same source-encoding style as `LilexSansSC NFM` / `SarasaNZSSlab NFM` — **inheritance is in the family name**:

| Token | Meaning |
| --- | --- |
| **Iosevka** | Latin base (Iosevka mono) |
| **Curly** | ss20 Curly Style prebuilt (rounded terminals; not Slab) |
| **RHR** | Resource Han Rounded SC (CJK) |
| **Dual** | Intermediate pre-Nerd merge only |
| **NFM** | Nerd Font Mono product (complete icons, single-width glyphs) |

- Intermediate family (name ID 1): `IosevkaCurlyRHR Dual`
- Product family (name ID 1): `IosevkaCurlyRHR NFM` (19 chars, Windows ≤31)
- PostScript / file stem: `IosevkaCurlyRHRNFM`
- Docs shorthand **圆体** = product direction; install/picker name is **IosevkaCurlyRHR NFM**
- Not an official Iosevka / Resource Han Rounded / Nerd Fonts face. Upstream OFLs reserve **Iosevka** (and Source Han RFNs may apply to the RHR lineage). Compound is a project source-label — review RFN before public OFL redistribution.

## Pins

Everything reproducible lives in [`font.toml`](font.toml):

- Iosevka Curly release tag + zip SHA-256
- RHR-CN 7z SHA-256 + Regular/Bold TTF names
- `EN_ADV` / `CJK_ADV` / vertical metrics / family names
- Optional `CJK_EMBOLDEN_*` (default 0 — RHR has real Bold)
- Nerd Fonts patcher tag

Do **not** bump pins casually; change them in a dedicated commit with a short rationale.

## Layout

```
rounded/
  font.toml
  licenses/
    OFL-Iosevka.txt
    OFL-Resource-Han-Rounded.txt
  scripts/
    merge_rounded.py       # the merge engine; everything else is lib/fontkit
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

- `bash`, `curl`, `unzip`, `zip`, `7z` (for RHR `.7z`)
- Python 3.10+ (`venv` or `uv`) → `fonttools`, `skia-pathops` (optional embolden), optional `Pillow`
- **FontForge** for the Nerd Font patcher (a build input; the container path was removed in KIT-277)

## Build

```bash
cd rounded
just build rounded
# → out/IosevkaCurlyRHRDual-{Regular,Bold}.ttf
# → out/nerd/IosevkaCurlyRHRNFM-{Regular,Bold}.ttf
```

Step by step:

```bash
just steps rounded                  # what the family is made of
just step rounded cjk-prepared-Bold # build one step
just gate rounded                   # 2:1 / mono flags / EAW / Nerd cells
```

### Sample render

```bash
python3 scripts/render-sample.py \
  --font out/nerd/IosevkaCurlyRHRNFM-Regular.ttf \
  --title "圆体 IosevkaCurlyRHR NFM · EN 500 / CJK 1000 · Iosevka Curly × RHR"
# → samples/rendered/sample-{dark,light}.png
```

### Release package

```bash
just release rounded
# → dist/IosevkaCurlyRHRNFM-0.1.0.zip
```

## Character policy

| Source | Role |
| --- | --- |
| **Iosevka Curly** (scaled to EN_ADV; OT tables kept) | ASCII, Latin extensions, digits, programming symbols, ligatures when present |
| **Resource Han Rounded SC** (optional embolden; advance → CJK_ADV) | Han, CJK punctuation, fullwidth forms |
| **Nerd Fonts** (`--single-width-glyphs`) | PUA icons at half-cell |

## Verify

```bash
python3 -m fontkit.verify2to1 --expect-half 500 --check-nerd --check-eaw out/nerd/IosevkaCurlyRHRNFM-*.ttf
```

| Set | Expected |
| --- | ---: |
| `A` / printable ASCII | **500** |
| `中` / sample Han / fullwidth | **1000** |
| Nerd PUA icons | **500** |
| `post.isFixedPitch` | **1** |

## Family / license

- **Product family:** `IosevkaCurlyRHR NFM` (Regular / Bold；方向绰号 圆体)
- Upstream **SIL OFL 1.1** (Iosevka RFN **Iosevka**; keep RHR OFL with redistributions)
- Nerd glyph sets follow Nerd Fonts / icon-font licenses
- Keep `licenses/OFL-Iosevka.txt` and `licenses/OFL-Resource-Han-Rounded.txt` with redistributions

## Upstream links

- Iosevka Curly: <https://github.com/be5invis/Iosevka/releases>
- Iosevka styles: <https://typeof.net/Iosevka/>
- Resource Han Rounded: <https://github.com/CyanoHao/Resource-Han-Rounded>
- Nerd Fonts: <https://github.com/ryanoasis/nerd-fonts>
