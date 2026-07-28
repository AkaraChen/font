# sans — LilexSansSC NFM

Coding dual-width face: **Lilex** (Latin / programming ligatures) + **IBM Plex Sans SC** (CJK) + **Nerd Font Mono**, strict **2:1** grid.

| Component | Source | Pin |
| --- | --- | --- |
| Latin / mono | [Lilex](https://github.com/mishamyrt/Lilex) static TTF | **2.700** |
| CJK | [IBM Plex Sans SC](https://github.com/IBM/plex) complete TTF (hinted) | `@ibm/plex-sans-sc@1.1.0` (font **v1.000**) |
| Icons | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) FontPatcher | **v3.4.0** (`--complete --single-width-glyphs`) |
| Grid | EN cell / CJK cell | **550 / 1100** |
| Symbol widths | EAW-correct (N/Na/H → half, W/F → full; A left alone) | `narrow-symbol-widths.py` after Nerd |
| Intermediate | Regular + Bold (pre-Nerd) | `out/LilexSansSCDual-{Regular,Bold}.ttf` |
| Product | Regular + Bold (Nerd Mono) | `out/nerd/LilexSansSCNFM-{Regular,Bold}.ttf` |
| Family name | Source-encoding (see below) | **LilexSansSC NFM** |
| Metrics gate | `verify-2to1.py --expect-half 550 --check-nerd --check-eaw` | after Nerd + EAW fix |

Lilex is an extended face on IBM Plex Mono with programming ligatures and OpenType features. The merge keeps Lilex **GSUB / GPOS / GDEF** (so `calt` ligatures, stylistic sets, character variants, and mark attach survive), X-scales the mono cell from native **600 → 550**, and imports SC for CJK. The Nerd step patches the complete icon set at half-cell width and restores mono host flags that FontForge clears on dual-width faces.

## Name recipe

Same style as serif’s `SarasaNZSSlab NFM` — long, concatenated sources + product tag:

| Token | Meaning |
| --- | --- |
| **Lilex** | Lilex (Latin / programming glyphs + ligatures / OT features) |
| **SansSC** | IBM Plex Sans SC (Simplified Chinese CJK) |
| **NFM** | Nerd Font Mono product (complete icons, single-width glyphs) |

- Intermediate family (name ID 1): `LilexSansSC Dual` (pre-Nerd merge only)
- Product family (name ID 1): `LilexSansSC NFM` (15 chars, Windows ≤31)
- PostScript / file stem: `LilexSansSCNFM`
- Not an official Lilex, IBM, or Nerd Fonts face. Upstream OFLs list reserved font names **“Lilex”** and **“Plex”** — treat this compound as a project source-label; review RFN before public OFL redistribution if that matters for your release.

## Pins

Everything reproducible lives in [`pins.env`](pins.env):

- GitHub release tags + download URLs
- SHA-256 of Lilex zip and of the two Plex Sans SC TTFs (individual files; not the ~500 MB full zip)
- Paths / commit for SC TTFs
- `EN_ADV` / `CJK_ADV` / vertical metrics / family names
- Nerd Fonts patcher tag + docker image digest

Do **not** bump pins casually; change them in a dedicated commit with a short rationale.

## Layout

```
sans/
  pins.env                 # upstream refs + product metrics + Nerd pins
  licenses/
    OFL-Lilex.txt
    OFL-IBM-Plex.txt
  scripts/
    build.sh               # one-shot fetch → merge → nerd → verify
    01-fetch-sources.sh
    02-merge.sh            # Lilex + SC → Dual intermediate
    03-nerd-patch.sh       # Nerd complete + rename + EAW widths + metric hygiene
    04-verify.sh           # 2:1 + mono flags + nerd + EAW + features
    merge_plex.py
    rename_nerd_family.py
    fix-nerd-widths.py
    narrow-symbol-widths.py  # EAW N/Na/H ↔ half, W/F ↔ full
    fix-terminal-metrics.py
    verify-2to1.py
    verify-features.py
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

## Dependencies

- `bash`, `curl`, `unzip`, `zip`
- Python 3.10+ (`venv` or `uv`) → `fonttools`, optional `Pillow` for samples
- **Docker** (preferred) or **FontForge** for the Nerd Font patcher

```bash
# Debian/Ubuntu example
sudo apt install curl unzip zip python3-venv
# plus Docker, or: sudo apt install fontforge
```

## Build

```bash
cd sans
./scripts/build.sh
# → out/LilexSansSCDual-{Regular,Bold}.ttf          (intermediate)
# → out/nerd/LilexSansSCNFM-{Regular,Bold}.ttf      (product)
```

Step by step:

```bash
./scripts/01-fetch-sources.sh   # download + extract pinned sources
./scripts/02-merge.sh           # merge EN=550 / CJK=1100 (preserve Lilex GSUB)
./scripts/03-nerd-patch.sh      # Nerd complete + half-cell icons + EAW widths + mono flags
./scripts/04-verify.sh          # hard-fail if advances / flags / EAW / features drift
```

Force patcher backend: `NERD_PATCH_METHOD=docker|fontforge ./scripts/03-nerd-patch.sh`

### Sample render

```bash
# after build; needs Pillow in work/venv
work/venv/bin/python scripts/render-sample.py \
  --font out/nerd/LilexSansSCNFM-Regular.ttf \
  --title "LilexSansSC NFM · EN 550 / CJK 1100"
# → samples/rendered/sample-{dark,light}.png
```

### Release package

```bash
./scripts/package-release.sh 0.1.0
# → dist/LilexSansSCNFM-0.1.0.zip
```

## Character policy

| Source | Role |
| --- | --- |
| **Lilex** (scaled to 550; OT tables kept) | ASCII, Latin extensions, digits, programming symbols, half-width punctuation, Greek / Cyrillic, **programming ligatures** (`calt`), stylistic sets / character variants |
| **Plex Sans SC** (advance → 1100, centred) | Han, CJK punctuation / symbols, fullwidth forms, kana / bopomofo, and any codepoint Lilex lacks |
| **Nerd Fonts** (`--single-width-glyphs`) | PUA icon sets at **half-cell** (Powerline, FA, Material, …) |

Not yet done (known limits):

1. SC `locl` / full GSUB/GPOS merge (SC layout tables are not copied)
2. x-height / CJK face optical size match (optical weight: follow-up)
3. Per-glyph vertical centering for brackets / equals / arrows
4. Italic (Latin-only italic planned; no CJK pseudo-oblique)
5. Pure visual QA of every math / symbol beyond the EAW metric gate

## Verify

```bash
python3 scripts/verify-2to1.py --expect-half 550 --check-nerd --check-eaw out/nerd/LilexSansSCNFM-*.ttf
python3 scripts/verify-features.py out/nerd/LilexSansSCNFM-*.ttf
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
| `N` / `Na` / `H` (neutral / narrow / halfwidth) | **1** (not configurable) | half (**550**) | **Hard gate** — `narrow-symbol-widths.py` recentres / fits; `verify --check-eaw` fails otherwise |
| `W` / `F` (wide / fullwidth) | **2** | full (**1100**) | **Hard gate** — re-centre in the full cell (never scale up). If the outline is shared with a Nerd PUA icon, the W/F codepoint is **forked** to a private full-width glyph so icons stay half-cell |
| `A` (ambiguous: `▶` `→` `①` `×` …) | 1 or 2 (user setting) | usually half (from Lilex) or full (from SC) | **Left alone by default** — CJK users who set “ambiguous = wide” keep 2-cell glyphs; rebuild with `narrow-symbol-widths.py --include-ambiguous` to force half |

Documented exceptions (multi-em dashes, a few vertical presentation forms) live in
`EAW_EXCEPTIONS` inside `verify-2to1.py` (same set as serif).

Re-run the fix on an existing product TTF:

```bash
python3 scripts/narrow-symbol-widths.py --no-donor out/nerd/LilexSansSCNFM-*.ttf
python3 scripts/fix-terminal-metrics.py out/nerd/LilexSansSCNFM-*.ttf
python3 scripts/verify-2to1.py --expect-half 550 --check-nerd --check-eaw out/nerd/LilexSansSCNFM-*.ttf
```

| Symptom | Cause | Fix |
| --- | --- | --- |
| `⁝` / rare symbols overflow the next column | `EAW=N` at full advance | `narrow-symbol-widths.py` (build step) |
| `⚡` / some radicals sit in the left half of a 2-cell slot | `EAW=W` at half advance | same step (widen / fork) |
| `▶` `→` still look “fullwidth” | `EAW=A` (ambiguous) — intentional | set terminal “ambiguous = wide”, or `--include-ambiguous` |

> **Why terminals used to hide this face:** early builds set `post.isFixedPitch=0`
> because dual-width is not single-cell classic mono. That is the flag macOS Core
> Text (`kCTFontTraitMonoSpace`), Chromium/VS Code pickers, and most terminals'
> "monospace only" filters read — so the font never appeared. The Nerd patcher
> (FontForge) also clears the flag on dual-width bases; `fix-terminal-metrics.py`
> restores it after patch. **fontconfig** (Linux) still classifies any dual-width
> font as proportional by scanning advances; nothing in the font can change that.

## Family / license

- **Product family:** `LilexSansSC NFM` (Regular / Bold)
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
