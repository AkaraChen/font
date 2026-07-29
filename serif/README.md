# serif — AKR Slab SC NFM (Nerd Font Mono)

Coding mono: **Slab Latin (IosevkaNSlab)** + **霞鹜新致宋 Opt** + **Nerd icons**, strict **2:1** dual-width.

| Component | Source |
| --- | --- |
| Latin | Sarasa `IosevkaNSlab` (MonoSlab) |
| CJK | [LXGW Neo ZhiSong Plus](https://github.com/lxgw/LxgwNeoZhiSong) `v1.066` |
| Grid | 2:1 mono (`A=500` / `中=1000`) |
| Weight match | pathops embolden **s=7.5** (Regular) / **s=24** (Bold), stem-measured vs IosevkaNSlab |
| **Product** | **Nerd Font Mono** → `out/nerd/AKRSlabSCNFM-{Regular,Bold}.ttf` |
| Symbol widths | EAW-correct: half-width donor outlines from Sarasa `TermSlab` |
| Mono flags | `post.isFixedPitch=1` + PANOSE `bProportion=9` (FontForge clears these) |
| Ligatures | default `calt` **+** Iosevka `dlig` (discretionary) folded in by `fontkit expand-ligatures` |
| Metrics gate | `python3 -m fontkit.verify2to1 --profile dense --check-nerd --check-eaw` (after Nerd patch) |

Upstream is **not forked permanently**. The build takes a **pinned**
[be5invis/Sarasa-Gothic](https://github.com/be5invis/Sarasa-Gothic) tree
(`fetchFromGitHub` at `sources.sarasa.commit`) and applies the patch stack in
`patches/series`. Since KIT-280 that is a derivation, not a shell pipeline —
see [`nix/families/serif.nix`](../nix/families/serif.nix).

## Pins

See `font.toml`: Sarasa / LXGW / embolden strengths / `nerd.commit`.

## Optical weight (CJK vs Latin stems)

Do **not** hand-tune embolden by eye alone. Stem widths are measured from outlines:

1. **Latin target** — IosevkaNSlab as it comes out of this build's own `merged` step (`AKRSlabSCDual-{Regular,Bold}.ttf`); no second copy to drift.
2. **CJK trial** — LXGW Neo ZhiSong Plus scaled to UPM 1000, emboldened at candidate strengths.
3. **Metric** — scanline vertical-stem median on sample glyphs (`H I l n o T E` / `中 一 十 日 国 木 工`). Vertical stems dominate mixed CN/EN optical weight in a mono face; Song horizontals stay thinner by design.

```bash
nix develop --command serif/scripts/calibrate-stroke.sh
# → recommends calibration.regular.embolden / calibration.bold.embolden for font.toml
```

| Face | Latin v-stem (U) | Old embolden | Measured CJK v @ old | New embolden | CJK v @ new |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | ≈78 | 14 | ≈91 (+13) | **7.5** | ≈78 (matched) |
| Bold | ≈111 | 32 | ≈127 (+16) | **24** | ≈111 (matched) |

The previous Regular **s=14** made CJK verticals noticeably heavier than Latin — matching the reported “中文比英文稍粗”.

## Layout

```
serif/
  font.toml
  patches/                 # applied by stdenv, in series order
  scripts/                 # diagnostics only — the build is nix/families/serif.nix
    calibrate-stroke.sh    # measure stems → recommend calibration.*.embolden
    render-coding-sample.py
  samples/
  out/                     # `just build serif` materialises here (gitignored)
  out/nerd/                # **product** (gitignored)

../nix/families/serif.nix  # the build: src-cjk → cjk-prepared → (Sarasa) →
                           # merged → nerd → packaged
../lib/fontkit/            # shared with every other family, run as `fontkit <step>`:
  scale_upem.py            #   2048 Neo ZhiSong → the 1000 product grid
  embolden.py              #   was serif/tools/embolden_cjk.py
  nerd_patch.py            #   --no-nerd-widths --donor … --expand-ligatures here
  narrow_symbol_widths.py  #   --protect-ambiguous --widen-shared skip here
  verify2to1.py            #   --profile dense here
  measure.py               #   was serif/tools/measure_stroke_width.py
```

## Dependencies

Nothing to install: `flake.nix` pins the toolchain and every step declares its
own inputs. Notably `afdko` (Sarasa's `verdafile.mjs` calls `otc2otf` / `otf2ttf`
during source prep) and `ttfautohint` are build inputs of the Sarasa derivation
rather than things the host is assumed to have — both upstream checks for them
only log and carry on.

The container path was removed in KIT-277 along with the other five families':
it was selected at runtime depending on what happened to be installed, so two
machines could produce two different fonts silently.

## Build (Nerd only product)

```bash
# From the repository root:
just build serif
# → out/nerd/AKRSlabSCNFM-{Regular,Bold}.ttf
# Family name: "AKR Slab SC NFM"  (Windows-safe ≤31)
```

Step by step — each of these is a derivation, and building one builds only what
it needs:

```bash
nix build .#serif-src-cjk-Regular       # LXGW Neo ZhiSong Plus, pinned
nix build .#serif-cjk-prepared-Bold     # UPM 2048 → 1000, then embolden
nix build .#serif-sarasa                # upstream verda build (patched tree)
nix build .#serif-merged-Bold           # one intermediate pre-Nerd face
nix build .#serif-nerd-Bold             # Nerd patch → rename → EAW → metrics → calt
nix build .#serif-verify                # the 2:1 / Nerd / EAW gate
nix build .#serif-release               # the zip (depends on the gate)
```

### Ligatures (calt + dlig)

Iosevka’s **default `calt`** is intentionally slim (equality, arrows, triple chaining
like `+++`/`---`, HTML comments, …). Richer programming ligations live under
**`dlig`** (discretionary: `++`/`--`/`##`/`~~`, counter-arrows, `/\` `\/`, `{|` `|}`,
`[|` `|]`, markdown checkboxes, …) and optional language packs (`JSPT`, `HSKL`, …).

Most editors only flip **`calt`** when “font ligatures” is enabled, so stock
Sarasa/Iosevka feels like ligatures are “half on”. The `nerd` step's last pass
(`fontkit nerd-patch --expand-ligatures`) unions the dlig lookups into every
calt feature.

Repair an already-built TTF without a full rebuild:

```bash
fontkit expand-ligatures AKRSlabSCNFM-Regular.ttf
# optional: also fold language packs (can overlap; prefer dlig-only for product)
# fontkit expand-ligatures --include all font.ttf
```

Still **not** present in Iosevka at all (nothing to enable): e.g. `&&`, `**` as
Fira-style multi-ampersand ligatures. Enable **font ligatures / calt** in the
editor; no extra OpenType feature toggle is required for the expanded set.

### Patcher policy

- `--complete` + **`--single-width-glyphs`** (icons = 1 cell)
- **Never** `--mono` / `-s` — that forces *all* glyphs (incl. CJK) to 1 cell and breaks 2:1
- Pin: `nerd.commit` in `font.toml` (font-patcher **4.26.0**, master — the newest *release*, v3.4.0, carries 4.20.3)
- After rename: `fontkit.fix_terminal_metrics` restores `post.isFixedPitch=1`, pins PANOSE `bProportion=9` and sets `OS/2.xAvgCharWidth` to the half-cell — the three things hosts read to decide the font is monospaced (see Troubleshooting)

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

Measured on **v0.1.0** `AKRSlabSCNFM-Regular.ttf` (and re-checked after metric fix):

| Observation | Cause | What to do |
| --- | --- | --- |
| Nerd PUA icons (Powerline `U+E0B0`/`E0B2`, FA, Material, …) | Advances are **half** (500). `fontkit.verify2to1 --check-nerd` gates this. | Nothing — patch path is correct (`--single-width-glyphs`, not `--mono`). |
| `⏵` `▸` `✓` `⌘` `⌥` … render “fullwidth” / overlap the next column | **Real metric bug, fixed in v0.1.2.** These are `EAW=N` (neutral): a terminal gives them exactly **1** cell, with no setting to change that. Base **Mono** shipped them at advance **1000** → 1 cell of space, 2 cells of ink. Affected **1006** codepoints. | Use ≥ **v0.1.2**, or run `fontkit narrow-symbol-widths` on an existing TTF. `fontkit.verify2to1 --check-eaw` now gates this. |
| `▶` `→` `①` `×` still look fullwidth | These are `EAW=A` (**ambiguous**) — genuinely user-configurable, so the build leaves them at 2 cells for CJK users who set “ambiguous = wide”. | Set your terminal to treat ambiguous as wide, or rebuild with `fontkit.narrow_symbol_widths --include-ambiguous`. |
| `☰` `⚡` `ㆴ` sit in the left half of a 2-cell slot | Symmetric case: `EAW=W` codepoints that shipped at **half** advance. | Fixed in v0.1.2 (23 glyphs re-centred in the full cell). |
| “Nerd symbols look ugly / squashed” | `--single-width-glyphs` forces icons into **1** cell; many source icons were drawn for ~1.5–2 cells. Patcher is **v3.4.0** (not an ancient script). | Expected for NFM; try fewer glyph sets (drop `--complete`) or accept Nerd Font **Propo** only outside strict grids. |
| Terminal / editor does not list the font as **monospaced** at all | **Fixed in v0.1.3.** `post.isFixedPitch` is the flag hosts read to answer "is this mono?" (macOS Core Text `kCTFontTraitMonoSpace`, Chromium / VS Code pickers, "monospace only" filters). FontForge — and so the Nerd patcher — recomputes it from the advance histogram, sees a dual-width font and clears it to **0**, even though upstream Sarasa ships **1** on the same 2:1 grid. | Use ≥ **v0.1.3**, or run `fontkit.fix_terminal_metrics` (restores `isFixedPitch=1` and pins PANOSE `bProportion=9`). `fontkit.verify2to1` gates both. Note: **fontconfig** (Linux) derives spacing by scanning advances and will still classify any dual-width font as proportional — nothing in the font can change that. |
| Large empty band on the **right** of the terminal after selecting this font | **Not a font bug.** This was originally diagnosed as hosts reading `OS/2.xAvgCharWidth` (~832 on a dual-width font) or a huge `head.xMax` as the monospaced cell width, and v0.1.2–v0.1.x shipped a tightened `head` bbox to work around it. It turned out to be a terminal bug; the non-conformant bbox was removed in KIT-284. `xAvgCharWidth=half` stays, because that is what a mono font is expected to advertise. | Update the terminal. If you can reproduce a band that moves with the *font*, reopen with the host and version — do not reintroduce the bbox hack without one. |
| Mixed CN/EN column drift | Half vs full advances are intentional 2:1 (`A=500`, `中=1000`). Drift usually comes from **full-width punctuation/symbols** in the line (see non-gated set above), not from broken CJK metrics. | Use the coding sample ruler in `samples/coding-mixed.txt`; avoid fullwidth ASCII (`ＵＴＦ`) in code. |

```bash
# Repair an already-built/released TTF without a full rebuild:
python3 -m fontkit.narrow_symbol_widths AKRSlabSCNFM-Regular.ttf \
  --protect-ambiguous --widen-shared skip \
  --donor SarasaTermSlabSC-Regular.ttf      # donor URL: see font.toml
python3 -m fontkit.fix_terminal_metrics AKRSlabSCNFM-Regular.ttf
python3 -m fontkit.verify2to1 --profile dense --check-nerd --check-eaw AKRSlabSCNFM-Regular.ttf
```

`fontkit.narrow_symbol_widths` transplants Sarasa **Term**'s properly drawn 1-cell
symbols; codepoints Term lacks are x-compressed and centred instead. Order
matters: it saves via fontTools, which recomputes `head`, so run
`fontkit.fix_terminal_metrics` **after** it.

## Release package

```bash
just release serif coding sc
# → result-serif-release/AKRSlabSCNFM-0.1.0.zip  (Nerd TTFs only)
```

The zip is gated: `packaged` depends on `serif-verify`, so a red gate is a build
failure rather than an archive nobody checked. Then:

```bash
gh release create v0.1.0 \
  result-serif-release/AKRSlabSCNFM-0.1.0.zip \
  out/nerd/AKRSlabSCNFM-Regular.ttf \
  out/nerd/AKRSlabSCNFM-Bold.ttf \
  --title "AKR Slab SC NFM v0.1.0" \
  --notes "Nerd Font Mono coding build (2:1 SC)."
```

## Coding samples

```bash
python3 scripts/render-coding-sample.py \
  --font out/nerd/AKRSlabSCNFM-Regular.ttf \
  --sizes 12,14,16
```

See [`samples/`](samples/).

## Editing the patch stack

`patches/series` lists the stack in order (`0001` pipeline, `0002` product
config) and is read by both `quilt` and the derivation, so they cannot disagree.
To re-roll a patch, work in a scratch copy of the pinned tree — `quilt` is no
longer in the devShell, since nothing in the build drives it:

```bash
src=$(nix build --no-link --print-out-paths .#sarasa-src)
cp -R "$src" /tmp/sarasa && chmod -R u+w /tmp/sarasa
cd /tmp/sarasa && QUILT_PATCHES=$OLDPWD/serif/patches quilt push -a
```

Bumping the Sarasa pin also moves `package-lock.json`, so re-derive
`npmDepsHash` in `nix/families/serif.nix`:

```bash
nix run nixpkgs#prefetch-npm-deps -- "$src/package-lock.json"
```

Do **not** commit multi-MiB font binaries; the CJK master is a pinned fetch.

## Family name

- **Product:** `AKR Slab SC NFM` (Regular / Bold) — 15 chars, Windows ≤ 31
- **Intermediate:** `AKR Slab SC Dual`, a build artifact that nevertheless ships
  in `out/`, which is why KIT-282 renamed it too: it used to be
  `SarasaMonoSlabNeoZhiSongSC-Opt`, three upstream reserved names in one stem.

The family name carries no upstream reserved name — the OFL does not allow a
derivative to keep its donors' reserved names. Sarasa, Iosevka N Slab and LXGW
Neo ZhiSong are credited in name ID 5 (version string) and name ID 10
(description). Was `SarasaNZSSlab NFM`; see
[`../docs/naming-migration.md`](../docs/naming-migration.md).

## License notes

- Sarasa Gothic / IosevkaN: upstream
- LXGW Neo ZhiSong: OFL
- Nerd Fonts glyphs / patcher: [ryanoasis/nerd-fonts](https://github.com/ryanoasis/nerd-fonts)
- Scripts & patches here: MIT (repo root) unless noted
