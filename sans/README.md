# sans — KitPlex Dual (Plex Mono × Plex Sans SC)

Coding dual-width face: **IBM Plex Mono** (Latin / programming) + **IBM Plex Sans SC** (CJK), strict **2:1** grid.

| Component | Source | Pin |
| --- | --- | --- |
| Latin / mono | [IBM Plex Mono](https://github.com/IBM/plex) complete TTF | `@ibm/plex-mono@2.5.0` (font **v2.005**) |
| CJK | [IBM Plex Sans SC](https://github.com/IBM/plex) complete TTF (hinted) | `@ibm/plex-sans-sc@1.1.0` (font **v1.000**) |
| Grid | EN cell / CJK cell | **550 / 1100** |
| Product | Regular + Bold | `out/KitPlexDual-{Regular,Bold}.ttf` |
| Family name | Derivative (not official IBM) | **KitPlex Dual** |

Chosen after a three-way bake-off (`500/1000`, **`550/1100`**, `600/1200`). Mono is X-scaled ~8.3% from its native 600 cell; CJK outlines stay unscaled and are recentred into a 1100 advance.

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
  licenses/OFL-IBM-Plex.txt
  scripts/
    build.sh               # one-shot fetch → merge → verify
    01-fetch-sources.sh
    02-merge.sh
    03-verify.sh
    merge_plex.py          # core merge (Mono scale + SC import)
    verify-2to1.py
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
- Python 3.10+ (`venv`) → `fonttools`, optional `Pillow` for samples

```bash
# Debian/Ubuntu example
sudo apt install curl unzip zip python3-venv
```

## Build

```bash
cd sans
./scripts/build.sh
# → out/KitPlexDual-Regular.ttf
# → out/KitPlexDual-Bold.ttf
```

Step by step:

```bash
./scripts/01-fetch-sources.sh   # download + extract pinned zips
./scripts/02-merge.sh           # merge EN=550 / CJK=1100
./scripts/03-verify.sh          # hard-fail if advances drift
```

### Sample render

```bash
# after build; needs Pillow in work/venv
work/venv/bin/python scripts/render-sample.py \
  --font out/KitPlexDual-Regular.ttf \
  --title "Plex merge · EN 550 / CJK 1100"
# → samples/rendered/sample-{dark,light}.png
```

### Release package

```bash
./scripts/package-release.sh 0.1.0
# → dist/KitPlexDual-0.1.0.zip
```

## Character policy

| Source | Role |
| --- | --- |
| **Plex Mono** (scaled to 550) | ASCII, Latin extensions Mono ships, digits, programming symbols, half-width punctuation, Greek / Cyrillic |
| **Plex Sans SC** (advance → 1100, centred) | Han, CJK punctuation / symbols, fullwidth forms, kana / bopomofo, and any codepoint Mono lacks |

Not yet done (known limits of v0.1):

1. SC `locl` / full GSUB/GPOS merge (SC layout tables are not copied)
2. x-height / CJK face optical size match
3. Per-glyph vertical centering for brackets / equals / arrows
4. Italic (Latin-only italic planned; no CJK pseudo-oblique)
5. Nerd Font patch
6. Systematic EAW / Powerline / math symbol visual QA

## Verify

```bash
python3 scripts/verify-2to1.py --expect-half 550 out/KitPlexDual-*.ttf
```

| Set | Expected |
| --- | --- |
| `A` / printable ASCII | **550** |
| `中` / sample Han / fullwidth forms | **1100** (= 2× EN) |
| `post.isFixedPitch` | **0** (dual-width; hosts that only list classic mono may hide it) |

## Family / license

- **Product family:** `KitPlex Dual` (Regular / Bold)
- Upstream is **SIL OFL 1.1** with reserved font name **“Plex”** — the derivative **must not** be named IBM Plex / Plex Mono / Plex Sans.
- Keep `licenses/OFL-IBM-Plex.txt` (and the copy next to shipped TTFs) with redistributions.
- Build scripts in this folder: MIT (repo root) unless noted.

## Upstream links

- Mono release: <https://github.com/IBM/plex/releases/tag/%40ibm/plex-mono%402.5.0>
- Sans SC release: <https://github.com/IBM/plex/releases/tag/%40ibm/plex-sans-sc%401.1.0>
- Project home: <https://github.com/IBM/plex>
