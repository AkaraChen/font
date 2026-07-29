# sans — AKR Sans SC NFM

Coding dual-width face: **Lilex** (Latin / programming ligatures) + **IBM Plex Sans SC** (CJK) + **Nerd Font Mono**, strict **2:1** grid.

| Component | Source | Pin |
| --- | --- | --- |
| Latin / mono | [Lilex](https://github.com/mishamyrt/Lilex) static TTF | **2.700** |
| CJK | [IBM Plex Sans SC](https://github.com/IBM/plex) complete TTF (hinted) | `@ibm/plex-sans-sc@1.1.0` (font **v1.000**) |
| Icons | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) FontPatcher | **v3.4.0** (`--complete --single-width-glyphs`) |
| Grid | EN cell / CJK cell | **550 / 1100** |
| Weight match | pathops embolden on SC (measured vs Lilex) | **s=5** Regular / **s=4** Bold |
| Symbol widths | EAW-correct (N/Na/H → half, W/F → full; A left alone) | `fontkit.narrow_symbol_widths` after Nerd |
| Intermediate | Regular + Bold (pre-Nerd) | `out/AKRSansSCDual-{Regular,Bold}.ttf` |
| Product | Regular + Bold (Nerd Mono) | `out/nerd/AKRSansSCNFM-{Regular,Bold}.ttf` |
| Family name | Source-encoding (see below) | **AKR Sans SC NFM** |
| Metrics gate | `fontkit.verify2to1 --expect-half 550 --check-nerd --check-eaw` | after Nerd + EAW fix |

Lilex is an extended face on IBM Plex Mono with programming ligatures and OpenType features. The merge keeps Lilex **GSUB / GPOS / GDEF** (so `calt` ligatures, stylistic sets, character variants, and mark attach survive), X-scales the mono cell from native **600 → 550**, emboldens SC full-cell outlines for optical weight, and imports SC for CJK. The Nerd step patches the complete icon set at half-cell width and restores mono host flags that FontForge clears on dual-width faces.

## Optical weight (CJK vs Latin stems)

Unifying advance (**550 / 1100**) does **not** unify perceived weight. Plex Sans SC vertical stems run lighter than Lilex once Latin is X-scaled for the product grid — the common “中文比英文细” look on mixed lines.

Do **not** hand-tune embolden by eye alone. Stem widths are measured from outlines (same tools as `serif/`):

1. **Latin target** — Lilex X-scaled **600 → EN_ADV** (same scale the merge engine applies).
2. **CJK trial** — IBM Plex Sans SC emboldened at candidate strengths (`fontkit.embolden`).
3. **Metric** — scanline vertical-stem median on sample glyphs (`H I l n o T E` / `中 一 十 日 国 木 工`). Use `stem_max_ratio=0.40` so Lilex Bold stems are not filtered out.

```bash
./scripts/calibrate-stroke.sh   # realises the source steps it needs
# → recommends calibration.regular.embolden / calibration.bold.embolden for font.toml
```

| Face | Latin v-stem (U, product scale) | CJK v @ s=0 | Embolden | CJK v @ pin |
| --- | ---: | ---: | ---: | ---: |
| Regular | ≈77 | ≈65.8 (−11) | **s=5** | ≈78.3 (+1) |
| Bold | ≈138 | ≈130 (−8) | **s=4** | ≈138 (matched) |

Embolden runs in the `cjk-prepared` step **before** the merge (full-cell SC only; advances stay source widths and are recentred to `CJK_ADV` by the merge engine). Shared tools: `fontkit.measure`, `fontkit.embolden`.

## Name recipe

`AKR <Style> <Region> <Variant>` — see the naming section of the root
[`README.md`](../README.md). The family name carries **no upstream reserved
name**: the OFL does not allow a derivative to keep its donors' reserved names,
so Lilex and Plex are credited in name ID 5 and name ID 10 instead.

| Token | Meaning |
| --- | --- |
| **AKR** | this repository's house name |
| **Sans** | Lilex Latin (programming glyphs, ligatures, OT features) on a sans CJK |
| **SC / TC / JP / KR** | which IBM Plex Sans master the face draws |
| **NFM** | Nerd Font Mono product (complete icons, single-width glyphs) |

- Intermediate family (name ID 1): `AKR Sans SC Dual` (pre-Nerd merge only)
- Product family (name ID 1): `AKR Sans SC NFM` (15 chars, Windows ≤31)
- PostScript / file stem: `AKRSansSCNFM`
- Not an official Lilex, IBM, or Nerd Fonts face.
- Was `LilexSansSC NFM` before KIT-282 — see
  [`../docs/naming-migration.md`](../docs/naming-migration.md).

## Regions

Four CJK masters at one pinned Plex commit, and **one** Latin build shared by all
four (`nix/granularity.nix` refuses to give `src-latin` a region axis):

| region | CJK master | product |
| --- | --- | --- |
| `sc` | IBM Plex Sans SC | `AKR Sans SC NFM` |
| `tc` | IBM Plex Sans TC | `AKR Sans TC NFM` |
| `jp` | IBM Plex Sans JP | `AKR Sans JP NFM` |
| `kr` | IBM Plex Sans KR | `AKR Sans KR NFM` |

`hk` is declared impossible rather than left out: Plex has no Hong Kong master,
and HKSCS forms are not a relabelling of TC (`[[build.unsupported]]` in
[`font.toml`](font.toml)).

```bash
just build sans             # all four regions, into sans/out
just build sans coding jp   # one cell, into sans/out-coding-jp
```

## Pins

Everything reproducible lives in [`font.toml`](font.toml):

- GitHub release tags + download URLs
- SHA-256 of Lilex zip and of the two Plex Sans SC TTFs (individual files; not the ~500 MB full zip)
- Paths / commit for SC TTFs
- `EN_ADV` / `CJK_ADV` / vertical metrics / family names
- `CJK_EMBOLDEN_REGULAR` / `CJK_EMBOLDEN_BOLD` (optical weight)
- Nerd Fonts patcher tag

Do **not** bump pins casually; change them in a dedicated commit with a short rationale.

## Layout

```
sans/
  font.toml                # sources + grid + naming + metrics + calibration + matrix
  licenses/
    OFL-Lilex.txt
    OFL-IBM-Plex.txt
  scripts/
    verify-features.py     # Lilex calt / ligature gate
    calibrate-stroke.sh    # diagnostic: measure stems → recommend CJK_EMBOLDEN_*
    render-sample.py       # diagnostic
  samples/
    coding-mixed.txt
    rendered/              # gitignored PNGs
  work/                    # gitignored downloads / venv / extract / stage
  out/                     # gitignored intermediate Dual TTFs
  out/nerd/                # gitignored product NFM TTFs
  dist/                    # gitignored release zips
```

Shared, not duplicated: [`../lib/fontkit/`](../lib/fontkit/) (`fontkit.measure`,
`fontkit.embolden`).

## Dependencies

- `bash`, `curl`, `unzip`, `zip`
- Python 3.10+ (`venv` or `uv`) → `fonttools`, `skia-pathops` (CJK embolden), optional `Pillow` for samples
- **FontForge** for the Nerd Font patcher (a build input; the container path was removed in KIT-277)


## Build

```bash
cd sans
just build sans
# → out/AKRSansSCDual-{Regular,Bold}.ttf          (intermediate)
# → out/nerd/AKRSansSCNFM-{Regular,Bold}.ttf      (product)
```

Step by step:

```bash
just steps sans                 # src-latin / src-cjk / cjk-prepared / merged / nerd / packaged
just step sans merged-Bold      # build one step in isolation
just gate sans                  # hard-fail if advances / flags / EAW / features drift
```

### Sample render

```bash
# after build; run inside `nix develop` (Pillow, freetype-py)
python3 scripts/render-sample.py \
  --font out/nerd/AKRSansSCNFM-Regular.ttf \
  --title "AKR Sans SC NFM · EN 550 / CJK 1100 · weight s=5"
# → samples/rendered/sample-{dark,light}.png
```

### Release package

```bash
just release sans coding sc
# → dist/AKRSansSCNFM-0.1.0.zip
```

## Character policy

| Source | Role |
| --- | --- |
| **Lilex** (scaled to 550; OT tables kept) | ASCII, Latin extensions, digits, programming symbols, half-width punctuation, Greek / Cyrillic, **programming ligatures** (`calt`), stylistic sets / character variants |
| **Plex Sans SC** (emboldened per pins; advance → 1100, centred) | Han, CJK punctuation / symbols, fullwidth forms, kana / bopomofo, and any codepoint Lilex lacks |
| **Nerd Fonts** (`--single-width-glyphs`) | PUA icon sets at **half-cell** (Powerline, FA, Material, …) |

Not yet done (known limits):

1. SC `locl` / full GSUB/GPOS merge (SC layout tables are not copied)
2. x-height / CJK face optical size match (stem weight is matched; overall face size may still differ)
3. Italic (Latin-only italic planned; no CJK pseudo-oblique)
4. Pure visual QA of every math / symbol beyond the EAW metric gate

**Won’t do (not needed):**

- Per-glyph vertical centering for coding brackets / operators (`()[]{}` `=` `+` arrows, …). Trial y-shifts (KIT-260) were only **sub-pixel** at normal coding sizes (~0.2–0.7 px at 16 px), so there is no perceptible gain for mutating dozens of outlines. Upstream placement is left as-is.

## Verify

```bash
python3 -m fontkit.verify2to1 --expect-half 550 --check-nerd --check-eaw out/nerd/AKRSansSCNFM-*.ttf
python3 scripts/verify-features.py out/nerd/AKRSansSCNFM-*.ttf
```

| Set | Expected |
| --- | --- |
| `A` / printable ASCII | **550** |
| `中` / sample Han / fullwidth forms | **1100** (= 2× EN) |
| Nerd PUA icons | **550** (half-cell; present when `--check-nerd`) |
| `--check-eaw`: East_Asian_Width `N`/`Na`/`H` | **550** |
| `--check-eaw`: East_Asian_Width `W`/`F` | **1100** |
| `post.isFixedPitch` | **1** (dual-width 2:1 still advertises mono; hosts use this flag) |
| PANOSE `bProportion` | **9** (Monospaced) |
| `OS/2.xAvgCharWidth` | **550** (half-cell; avoids wide empty band on some hosts) |
| GSUB `calt` + `.liga` glyphs | present (Lilex coding ligatures) |

### East_Asian_Width policy

A terminal sizes each cell from Unicode’s EAW table via `wcwidth()`, never from
the font. If the advance disagrees with EAW, the glyph draws into the wrong
number of cells (overlap or empty half-cell).

| EAW class | Terminal cells | Product advance | Build policy |
| --- | ---: | ---: | --- |
| `N` / `Na` / `H` (neutral / narrow / halfwidth) | **1** (not configurable) | half (**550**) | **Hard gate** — `fontkit.narrow_symbol_widths` recentres / fits; `verify --check-eaw` fails otherwise |
| `W` / `F` (wide / fullwidth) | **2** | full (**1100**) | **Hard gate** — re-centre in the full cell (never scale up). If the outline is shared with a Nerd PUA icon, the W/F codepoint is **forked** to a private full-width glyph so icons stay half-cell |
| `A` (ambiguous: `▶` `→` `①` `×` …) | 1 or 2 (user setting) | usually half (from Lilex) or full (from SC) | **Left alone by default** — CJK users who set “ambiguous = wide” keep 2-cell glyphs; rebuild with `fontkit.narrow_symbol_widths --include-ambiguous` to force half |

Documented exceptions (multi-em dashes, a few vertical presentation forms) live in
`EAW_EXCEPTIONS` inside `fontkit.verify2to1` (one set, shared with serif).

Re-run the fix on an existing product TTF:

```bash
python3 -m fontkit.narrow_symbol_widths --no-donor out/nerd/AKRSansSCNFM-*.ttf
python3 -m fontkit.fix_terminal_metrics out/nerd/AKRSansSCNFM-*.ttf
python3 -m fontkit.verify2to1 --expect-half 550 --check-nerd --check-eaw out/nerd/AKRSansSCNFM-*.ttf
```

| Symptom | Cause | Fix |
| --- | --- | --- |
| `⁝` / rare symbols overflow the next column | `EAW=N` at full advance | `fontkit.narrow_symbol_widths` (build step) |
| `⚡` / some radicals sit in the left half of a 2-cell slot | `EAW=W` at half advance | same step (widen / fork) |
| `▶` `→` still look “fullwidth” | `EAW=A` (ambiguous) — intentional | set terminal “ambiguous = wide”, or `--include-ambiguous` |

> **Why terminals used to hide this face:** early builds set `post.isFixedPitch=0`
> because dual-width is not single-cell classic mono. That is the flag macOS Core
> Text (`kCTFontTraitMonoSpace`), Chromium/VS Code pickers, and most terminals'
> "monospace only" filters read — so the font never appeared. The Nerd patcher
> (FontForge) also clears the flag on dual-width bases; `fontkit.fix_terminal_metrics`
> restores it after patch. **fontconfig** (Linux) still classifies any dual-width
> font as proportional by scanning advances; nothing in the font can change that.

## Family / license

- **Product family:** `AKR Sans SC NFM` (Regular / Bold)
- Upstream is **SIL OFL 1.1** (Lilex RFN **“Lilex”**; Plex RFN **“Plex”**)
- Nerd glyph sets follow the Nerd Fonts / individual icon-font licenses (see patcher)
- Keep `licenses/OFL-Lilex.txt` and `licenses/OFL-IBM-Plex.txt` (and copies next to shipped TTFs) with redistributions
- Build scripts in this folder: MIT (repo root) unless noted

## Upstream links

- Lilex release: <https://github.com/mishamyrt/Lilex/releases/tag/2.700>
- Lilex project: <https://github.com/mishamyrt/Lilex> · <https://lilex.myrt.co>
- Sans SC release: <https://github.com/IBM/plex/releases/tag/%40ibm/plex-sans-sc%401.1.0>
- Plex project: <https://github.com/IBM/plex>
- Nerd Fonts: <https://github.com/ryanoasis/nerd-fonts>
