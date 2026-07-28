# serif — SarasaNZSSlab NFM (Nerd Font Mono)

Coding mono: **Slab Latin (IosevkaNSlab)** + **霞鹜新致宋 Opt** + **Nerd icons**, strict **2:1** dual-width.

| Component | Source |
| --- | --- |
| Latin | Sarasa `IosevkaNSlab` (MonoSlab) |
| CJK | [LXGW Neo ZhiSong Plus](https://github.com/lxgw/LxgwNeoZhiSong) `v1.066` |
| Grid | 2:1 mono (`A=500` / `中=1000`) |
| Weight match | pathops embolden **s=7.5** (Regular) / **s=24** (Bold), stem-measured vs IosevkaNSlab |
| **Product** | **Nerd Font Mono** → `out/nerd/SarasaNZSSlabNFM-{Regular,Bold}.ttf` |
| Symbol widths | EAW-correct: half-width donor outlines from Sarasa `TermSlab` |
| Mono flags | `post.isFixedPitch=1` + PANOSE `bProportion=9` (FontForge clears these) |
| Ligatures | default `calt` **+** Iosevka `dlig` (discretionary) folded in by `expand-default-ligatures.py` |
| Metrics gate | `python3 -m fontkit.verify2to1 --profile dense --check-nerd --check-eaw` (after Nerd patch) |

Upstream is **not forked permanently**. Scripts clone a **pinned** [be5invis/Sarasa-Gothic](https://github.com/be5invis/Sarasa-Gothic) ref and apply **quilt** patches.

## Pins

See `pins.env`: Sarasa / LXGW / embolden strengths / `NERD_FONTS_TAG` + docker digest.

## Optical weight (CJK vs Latin stems)

Do **not** hand-tune embolden by eye alone. Stem widths are measured from outlines:

1. **Latin target** — IosevkaNSlab in upstream `SarasaMonoSlabSC-{Regular,Bold}.ttf` (same Latin this build uses).
2. **CJK trial** — LXGW Neo ZhiSong Plus scaled to UPM 1000, emboldened at candidate strengths.
3. **Metric** — scanline vertical-stem median on sample glyphs (`H I l n o T E` / `中 一 十 日 国 木 工`). Vertical stems dominate mixed CN/EN optical weight in a mono face; Song horizontals stay thinner by design.

```bash
./scripts/calibrate-stroke.sh
# → recommends CJK_EMBOLDEN_REGULAR / CJK_EMBOLDEN_BOLD for pins.env
```

| Face | Latin v-stem (U) | Old embolden | Measured CJK v @ old | New embolden | CJK v @ new |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | ≈78 | 14 | ≈91 (+13) | **7.5** | ≈78 (matched) |
| Bold | ≈111 | 32 | ≈127 (+16) | **24** | ≈111 (matched) |

The previous Regular **s=14** made CJK verticals noticeably heavier than Latin — matching the reported “中文比英文稍粗”.

## Layout

```
serif/
  pins.env
  patches/                 # quilt series
  scripts/
    build.sh               # one-shot → Nerd product
    01…04-*.sh             # intermediate Sarasa build
    05-nerd-patch.sh       # Nerd patch + 2:1 --check-nerd
    06-narrow-symbols.sh   # EAW-correct symbol widths + expand calt + final gate
    calibrate-stroke.sh    # measure stems → recommend CJK_EMBOLDEN_*
    package-release.sh     # zip out/nerd for GitHub Release
    expand-default-ligatures.py  # fold dlig (etc.) into default calt
    render-coding-sample.py
  samples/
  work/                    # gitignored
  out/                     # intermediate pre-Nerd TTFs (gitignored)
  out/nerd/                # **product** (gitignored)
  dist/                    # release zips (gitignored)

../lib/fontkit/            # shared with every other family, run as
                           # python3 -m fontkit.<module>:
  verify2to1.py            #   --profile dense here
  rename_nerd_family.py
  fix_terminal_metrics.py  #   --keep-bbox here, serif only
  narrow_symbol_widths.py  #   --protect-ambiguous --widen-shared skip here
  embolden.py              #   was serif/tools/embolden_cjk.py
  measure.py               #   was serif/tools/measure_stroke_width.py
```

## Dependencies

- `git`, `curl`, `quilt`, `node` (≥ 20), `npm`, `ttfautohint`, `unzip`, `zip`
- Python 3.10+ (`venv` or `uv`) → `fonttools` + `skia-pathops`
- **Nerd patch** — one of:
  1. **Docker** (preferred): image in `pins.env` (`nerdfonts/patcher@sha256:…`)
  2. **Local**: `fontforge` + FontPatcher.zip (cached under `work/`)

```bash
# Debian/Ubuntu example
sudo apt install git curl quilt nodejs npm ttfautohint python3-venv unzip zip
# docker recommended for Nerd; or: sudo apt install fontforge
```

## Build (Nerd only product)

```bash
cd serif
./scripts/build.sh
# → out/nerd/SarasaNZSSlabNFM-{Regular,Bold}.ttf
# Family name: "SarasaNZSSlab NFM"  (Windows-safe ≤31)
```

Step by step (same end product):

```bash
./scripts/01-clone-sarasa.sh
./scripts/02-apply-quilt.sh
./scripts/03-prepare-cjk.sh
./scripts/04-build.sh          # intermediate out/*.ttf
./scripts/05-nerd-patch.sh     # product + verify --check-nerd
./scripts/06-narrow-symbols.sh # EAW symbol widths + expand calt + verify --check-eaw
```

### Ligatures (calt + dlig)

Iosevka’s **default `calt`** is intentionally slim (equality, arrows, triple chaining
like `+++`/`---`, HTML comments, …). Richer programming ligations live under
**`dlig`** (discretionary: `++`/`--`/`##`/`~~`, counter-arrows, `/\` `\/`, `{|` `|}`,
`[|` `|]`, markdown checkboxes, …) and optional language packs (`JSPT`, `HSKL`, …).

Most editors only flip **`calt`** when “font ligatures” is enabled, so stock
Sarasa/Iosevka feels like ligatures are “half on”. After Nerd + metric hygiene,
`06-narrow-symbols.sh` runs:

```bash
python3 scripts/expand-default-ligatures.py out/nerd/*.ttf
# default: union dlig lookups into every calt feature
```

Repair an already-built TTF without a full rebuild:

```bash
python3 scripts/expand-default-ligatures.py SarasaNZSSlabNFM-Regular.ttf
# optional: also fold language packs (can overlap; prefer dlig-only for product)
# python3 scripts/expand-default-ligatures.py --include all font.ttf
```

Still **not** present in Iosevka at all (nothing to enable): e.g. `&&`, `**` as
Fira-style multi-ampersand ligatures. Enable **font ligatures / calt** in the
editor; no extra OpenType feature toggle is required for the expanded set.

### Patcher policy

- `--complete` + **`--single-width-glyphs`** (icons = 1 cell)
- **Never** `--mono` / `-s` — that forces *all* glyphs (incl. CJK) to 1 cell and breaks 2:1
- Pin: `NERD_FONTS_TAG` in `pins.env` (currently **v3.4.0**, current upstream latest)
- After rename: `fontkit.fix_terminal_metrics --keep-bbox` sets `OS/2.xAvgCharWidth` to the half-cell and recomputes `head` bbox from half/full glyphs only (see Troubleshooting). `--keep-bbox` is serif-only — it holds that bbox through the save

## Verify

```bash
python3 -m fontkit.verify2to1 --profile dense --check-nerd --check-eaw out/nerd/*.ttf
```

| Set | Expected |
| --- | --- |
| `A` / half ASCII, box drawing, halfwidth kana | half unit (usually 500) |
| `中` / fullwidth / CJK samples | 2× half |
| Nerd/PUA icons present | half unit |
| `--check-eaw`: every codepoint with East_Asian_Width `N`/`Na`/`H` | half unit |
| `--check-eaw`: every codepoint with East_Asian_Width `W`/`F` | 2× half |

Epsilon default **0**. Exit `1` on failure with codepoint report.

`--check-eaw` is the gate that matters for terminal alignment: a terminal sizes
each cell from Unicode's EAW table via `wcwidth()`, never from the font. If the
advance disagrees with EAW, the glyph draws into the wrong number of cells.
Documented exceptions live in `EAW_EXCEPTIONS` (multi-em dashes, vertical
presentation forms sharing an outline with a narrow codepoint).

Still non-gated by design: **ambiguous** (`EAW=A`) codepoints such as `▶ → ①`,
because terminals let the user choose 1 or 2 cells for those.

## Troubleshooting (terminal alignment / Nerd icons)

Measured on **v0.1.0** `SarasaNZSSlabNFM-Regular.ttf` (and re-checked after metric fix):

| Observation | Cause | What to do |
| --- | --- | --- |
| Nerd PUA icons (Powerline `U+E0B0`/`E0B2`, FA, Material, …) | Advances are **half** (500). `fontkit.verify2to1 --check-nerd` gates this. | Nothing — patch path is correct (`--single-width-glyphs`, not `--mono`). |
| `⏵` `▸` `✓` `⌘` `⌥` … render “fullwidth” / overlap the next column | **Real metric bug, fixed in v0.1.2.** These are `EAW=N` (neutral): a terminal gives them exactly **1** cell, with no setting to change that. Base **Mono** shipped them at advance **1000** → 1 cell of space, 2 cells of ink. Affected **1006** codepoints. | Use ≥ **v0.1.2**, or run `06-narrow-symbols.sh` / `fontkit.narrow_symbol_widths` on an existing TTF. `fontkit.verify2to1 --check-eaw` now gates this. |
| `▶` `→` `①` `×` still look fullwidth | These are `EAW=A` (**ambiguous**) — genuinely user-configurable, so the build leaves them at 2 cells for CJK users who set “ambiguous = wide”. | Set your terminal to treat ambiguous as wide, or rebuild with `fontkit.narrow_symbol_widths --include-ambiguous`. |
| `☰` `⚡` `ㆴ` sit in the left half of a 2-cell slot | Symmetric case: `EAW=W` codepoints that shipped at **half** advance. | Fixed in v0.1.2 (23 glyphs re-centred in the full cell). |
| “Nerd symbols look ugly / squashed” | `--single-width-glyphs` forces icons into **1** cell; many source icons were drawn for ~1.5–2 cells. Patcher is **v3.4.0** (not an ancient script). | Expected for NFM; try fewer glyph sets (drop `--complete`) or accept Nerd Font **Propo** only outside strict grids. |
| Terminal / editor does not list the font as **monospaced** at all | **Fixed in v0.1.3.** `post.isFixedPitch` is the flag hosts read to answer "is this mono?" (macOS Core Text `kCTFontTraitMonoSpace`, Chromium / VS Code pickers, "monospace only" filters). FontForge — and so the Nerd patcher — recomputes it from the advance histogram, sees a dual-width font and clears it to **0**, even though upstream Sarasa ships **1** on the same 2:1 grid. | Use ≥ **v0.1.3**, or run `fontkit.fix_terminal_metrics --keep-bbox` (now restores `isFixedPitch=1` and pins PANOSE `bProportion=9`). `fontkit.verify2to1` gates both. Note: **fontconfig** (Linux) derives spacing by scanning advances and will still classify any dual-width font as proportional — nothing in the font can change that. |
| Large empty band on the **right** of the terminal after selecting this font | Dual-width font: ~33k glyphs @1000 + ~18k @500 → raw `OS/2.xAvgCharWidth≈832`. Some hosts treat that average (or a huge `head.xMax` from multi-em dashes) as the monospaced cell width. v0.1.2 and earlier also shipped `post.isFixedPitch=0` (see the row above). | Rebuild with current `05-nerd-patch.sh` (runs `fontkit.fix_terminal_metrics --keep-bbox`: `xAvgCharWidth=half`, tighter head bbox). Confirm terminal uses font advances / wcwidth, not average width. |
| Mixed CN/EN column drift | Half vs full advances are intentional 2:1 (`A=500`, `中=1000`). Drift usually comes from **full-width punctuation/symbols** in the line (see non-gated set above), not from broken CJK metrics. | Use the coding sample ruler in `samples/coding-mixed.txt`; avoid fullwidth ASCII (`ＵＴＦ`) in code. |

```bash
# Repair an already-built/released TTF without a full rebuild:
python3 -m fontkit.narrow_symbol_widths SarasaNZSSlabNFM-Regular.ttf \
  --protect-ambiguous --widen-shared skip \
  --donor SarasaTermSlabSC-Regular.ttf      # donor URL: see pins.env
python3 -m fontkit.fix_terminal_metrics --keep-bbox SarasaNZSSlabNFM-Regular.ttf
python3 -m fontkit.verify2to1 --profile dense --check-nerd --check-eaw SarasaNZSSlabNFM-Regular.ttf
```

`fontkit.narrow_symbol_widths` transplants Sarasa **Term**'s properly drawn 1-cell
symbols; codepoints Term lacks are x-compressed and centred instead. Order
matters: it saves via fontTools, which recomputes `head`, so run
`fontkit.fix_terminal_metrics` **after** it.

## Release package

```bash
./scripts/package-release.sh 0.1.0
# → dist/SarasaNZSSlabNFM-0.1.0.zip  (Nerd TTFs only)
```

Then:

```bash
gh release create v0.1.0 \
  dist/SarasaNZSSlabNFM-0.1.0.zip \
  out/nerd/SarasaNZSSlabNFM-Regular.ttf \
  out/nerd/SarasaNZSSlabNFM-Bold.ttf \
  --title "SarasaNZSSlab NFM v0.1.0" \
  --notes "Nerd Font Mono coding build (2:1 SC)."
```

## Coding samples

```bash
python3 scripts/render-coding-sample.py \
  --font out/nerd/SarasaNZSSlabNFM-Regular.ttf \
  --sizes 12,14,16
```

See [`samples/`](samples/).

## Quilt workflow

```bash
export QUILT_PATCHES="$PWD/patches"
cd work/Sarasa-Gothic
quilt series   # 0001 pipeline, 0002 product config
```

Do **not** commit multi‑MiB font binaries; CJK is fetched in `03-prepare-cjk.sh`.

## Family name

- **Product:** `SarasaNZSSlab NFM` (Regular / Bold)
- Intermediate pre-Nerd names are build artifacts only.

Experimental naming; respect OFL / reserved font names if redistributing.

## License notes

- Sarasa Gothic / IosevkaN: upstream
- LXGW Neo ZhiSong: OFL
- Nerd Fonts glyphs / patcher: [ryanoasis/nerd-fonts](https://github.com/ryanoasis/nerd-fonts)
- Scripts & patches here: MIT (repo root) unless noted
