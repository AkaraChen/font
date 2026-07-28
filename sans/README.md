# sans — LilexSansSC Dual

Coding dual-width face: **Lilex** (Latin / programming ligatures) + **IBM Plex Sans SC** (CJK), strict **2:1** grid.

| Component | Source | Pin |
| --- | --- | --- |
| Latin / mono | [Lilex](https://github.com/mishamyrt/Lilex) static TTF | **2.700** |
| CJK | [IBM Plex Sans SC](https://github.com/IBM/plex) complete TTF (hinted) | `@ibm/plex-sans-sc@1.1.0` (font **v1.000**) |
| Grid | EN cell / CJK cell | **550 / 1100** |
| Product | Regular + Bold | `out/LilexSansSCDual-{Regular,Bold}.ttf` |
| Family name | Source-encoding (see below) | **LilexSansSC Dual** |

Lilex is an extended face on IBM Plex Mono with programming ligatures and OpenType features. The merge keeps Lilex **GSUB / GPOS / GDEF** (so `calt` ligatures, stylistic sets, character variants, and mark attach survive), X-scales the mono cell from native **600 → 550**, and imports SC for CJK.

## Name recipe

Same style as serif’s `SarasaNZSSlab NFM` — long, concatenated sources + product tag:

| Token | Meaning |
| --- | --- |
| **Lilex** | Lilex (Latin / programming glyphs + ligatures / OT features) |
| **SansSC** | IBM Plex Sans SC (Simplified Chinese CJK) |
| **Dual** | dual-width 2:1 coding product (EN cell + CJK cell) |

- Family (name ID 1): `LilexSansSC Dual` (16 chars, Windows ≤31)
- PostScript / file stem: `LilexSansSCDual`
- Not an official Lilex or IBM face. Upstream OFLs list reserved font names **“Lilex”** and **“Plex”** — treat this compound as a project source-label; review RFN before public OFL redistribution if that matters for your release.

## Pins

Everything reproducible lives in [`pins.env`](pins.env):

- GitHub release tags + zip URLs
- SHA-256 of the release zips
- Paths inside each zip
- `EN_ADV` / `CJK_ADV` / vertical metrics / family names

Do **not** bump pins casually; change them in a dedicated commit with a short rationale.

## Layout

```
sans/
  pins.env                 # upstream refs + product metrics
  licenses/
    OFL-Lilex.txt
    OFL-IBM-Plex.txt
  scripts/
    build.sh               # one-shot fetch → merge → verify
    01-fetch-sources.sh
    02-merge.sh
    03-verify.sh
    merge_plex.py          # core merge (Lilex scale + SC import; keeps OT)
    verify-2to1.py
    verify-features.py     # calt / ligatures / zero-width marks
    render-sample.py
    package-release.sh
  samples/
    coding-mixed.txt
    rendered/              # gitignored PNGs
  work/                    # gitignored downloads / venv / extract
  out/                     # gitignored product TTFs
  dist/                    # gitignored release zips
```

This tree is intentionally **simpler** than `serif/` (no quilt / Sarasa / Nerd patcher). Merge is a single Python step over two OFL TTFs.

## Dependencies

- `bash`, `curl`, `unzip`, `zip`
- Python 3.10+ (`venv` or `uv`) → `fonttools`, optional `Pillow` for samples

```bash
# Debian/Ubuntu example
sudo apt install curl unzip zip python3-venv
```

## Build

```bash
cd sans
./scripts/build.sh
# → out/LilexSansSCDual-Regular.ttf
# → out/LilexSansSCDual-Bold.ttf
```

Step by step:

```bash
./scripts/01-fetch-sources.sh   # download + extract pinned zips
./scripts/02-merge.sh           # merge EN=550 / CJK=1100 (preserve Lilex GSUB)
./scripts/03-verify.sh          # hard-fail if advances or features drift
```

### Sample render

```bash
# after build; needs Pillow in work/venv
work/venv/bin/python scripts/render-sample.py \
  --font out/LilexSansSCDual-Regular.ttf \
  --title "LilexSansSC Dual · EN 550 / CJK 1100"
# → samples/rendered/sample-{dark,light}.png
```

### Release package

```bash
./scripts/package-release.sh 0.1.0
# → dist/LilexSansSCDual-0.1.0.zip
```

## Character policy

| Source | Role |
| --- | --- |
| **Lilex** (scaled to 550; OT tables kept) | ASCII, Latin extensions, digits, programming symbols, half-width punctuation, Greek / Cyrillic, **programming ligatures** (`calt`), stylistic sets / character variants |
| **Plex Sans SC** (advance → 1100, centred) | Han, CJK punctuation / symbols, fullwidth forms, kana / bopomofo, and any codepoint Lilex lacks |

Not yet done (known limits of v0.1):

1. SC `locl` / full GSUB/GPOS merge (SC layout tables are not copied)
2. x-height / CJK face optical size match
3. Per-glyph vertical centering for brackets / equals / arrows
4. Italic (Latin-only italic planned; no CJK pseudo-oblique)
5. Nerd Font patch
6. Systematic EAW / Powerline / math symbol visual QA

## Verify

```bash
python3 scripts/verify-2to1.py --expect-half 550 out/LilexSansSCDual-*.ttf
python3 scripts/verify-features.py out/LilexSansSCDual-*.ttf
```

| Set | Expected |
| --- | --- |
| `A` / printable ASCII | **550** |
| `中` / sample Han / fullwidth forms | **1100** (= 2× EN) |
| `post.isFixedPitch` | **1** (dual-width 2:1 still advertises mono; hosts use this flag) |
| PANOSE `bProportion` | **9** (Monospaced) |
| `OS/2.xAvgCharWidth` | **550** (half-cell; avoids wide empty band on some hosts) |
| GSUB `calt` + `.liga` glyphs | present (Lilex coding ligatures) |

> **Why terminals used to hide this face:** early builds set `post.isFixedPitch=0`
> because dual-width is not single-cell classic mono. That is the flag macOS Core
> Text (`kCTFontTraitMonoSpace`), Chromium/VS Code pickers, and most terminals'
> "monospace only" filters read — so the font never appeared. Sibling products
> (`serif` / `pixel` / `handwriting`) already ship `isFixedPitch=1` + PANOSE 9
> for the same 2:1 grid. **fontconfig** (Linux) still classifies any dual-width
> font as proportional by scanning advances; nothing in the font can change that.

## Family / license

- **Product family:** `LilexSansSC Dual` (Regular / Bold)
- Upstream is **SIL OFL 1.1** (Lilex RFN **“Lilex”**; Plex RFN **“Plex”**)
- Keep `licenses/OFL-Lilex.txt` and `licenses/OFL-IBM-Plex.txt` (and copies next to shipped TTFs) with redistributions
- Build scripts in this folder: MIT (repo root) unless noted

## Upstream links

- Lilex release: <https://github.com/mishamyrt/Lilex/releases/tag/2.700>
- Lilex project: <https://github.com/mishamyrt/Lilex> · <https://lilex.myrt.co>
- Sans SC release: <https://github.com/IBM/plex/releases/tag/%40ibm/plex-sans-sc%401.1.0>
- Plex project: <https://github.com/IBM/plex>
