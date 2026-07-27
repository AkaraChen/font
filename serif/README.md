# serif — MonoSlab × 霞鹜新致宋 Opt

Stable rebuild of the **KIT-234** experiment, plus **coding** gates (**KIT-236**):

| Component | Source |
| --- | --- |
| Latin | Sarasa `IosevkaNSlab` (MonoSlab) |
| CJK | [LXGW Neo ZhiSong Plus](https://github.com/lxgw/LxgwNeoZhiSong) `v1.066` |
| Grid | 2:1 mono (`A=500` / `中=1000` after merge) |
| Weight match | pathops embolden **s=14** (Regular) / **s=32** (Bold) |
| Output | Unhinted TTF SC Regular + Bold |
| Nerd (optional) | Secondary patch via Nerd Fonts `font-patcher` → `out/nerd/` |
| Metrics gate | `scripts/verify-2to1.py` (strict advance check, CI-friendly) |

Upstream tree is **not forked permanently**. Build scripts clone a **pinned ref** of [be5invis/Sarasa-Gothic](https://github.com/be5invis/Sarasa-Gothic) and apply **quilt** patches from `patches/`.

## Pins

See `pins.env`:

- `SARASA_REF=v1.0.40` / `SARASA_COMMIT=4b908c7…`
- `LXGW_TAG=v1.066`
- embolden strengths
- `NERD_FONTS_TAG=v3.4.0` (FontPatcher.zip) / docker image tag

## Layout

```
serif/
  pins.env                 # version pins
  patches/
    series                 # quilt series
    0001-verdafile-….patch # ttf-unhinted + directTtf CJK drop-in
    0002-config-….patch    # MonoSlab × SC × NeoZhiSong Opt naming
  tools/
    embolden_cjk.py        # pathops stroke embolden
  scripts/
    build.sh               # one-shot (NERD=1 enables Nerd step)
    01-clone-sarasa.sh
    02-apply-quilt.sh
    03-prepare-cjk.sh
    04-build.sh            # build + strict 2:1 verify
    05-nerd-patch.sh       # Nerd Font patch + re-verify --check-nerd
    verify-2to1.py         # advance-width gate
    render-coding-sample.py
  samples/                 # coding text + optional PNG renders
  work/                    # gitignored build tree
  out/                     # gitignored products
  out/nerd/                # gitignored Nerd-patched products
```

## Dependencies

### Base build

- `git`, `curl`, `quilt`, `node` (≥ 20), `npm`
- `ttfautohint` (Sarasa latin prep)
- Python 3.10+ (`python3 -m venv` **or** `uv`) for `fonttools` + `skia-pathops`

AFDKO `otc2otf` is **not** required for this drop-in TTF path.

```bash
# Debian/Ubuntu example
sudo apt install git curl quilt nodejs npm ttfautohint python3-venv unzip
# or: brew install quilt node ttfautohint
```

### Nerd patch (optional)

Pick **one**:

1. **Docker** (preferred): `docker` + image `nerdfonts/patcher` (see `pins.env`)
2. **Local**: `fontforge` + downloaded `FontPatcher.zip` (script caches under `work/`)

```bash
# Debian/Ubuntu local patcher
sudo apt install fontforge
```

## Build

```bash
cd serif
./scripts/build.sh
# → out/SarasaMonoSlabNeoZhiSongSC-Opt-{Regular,Bold}.ttf
# 04-build.sh runs verify-2to1.py automatically (exit ≠ 0 on metric failure)
```

With Nerd icons:

```bash
NERD=1 ./scripts/build.sh
# or after a normal build:
./scripts/05-nerd-patch.sh
# → out/nerd/SarasaNZSSlabNFM-{Regular,Bold}.ttf
#    (patcher full set + --single-width-glyphs; family shortened for Windows ≤31)
```

Step by step:

```bash
./scripts/01-clone-sarasa.sh   # clone pinned Sarasa
./scripts/02-apply-quilt.sh    # quilt push -a
./scripts/03-prepare-cjk.sh    # download LXGW, scale UPM, embolden
./scripts/04-build.sh          # npm run build ttf-unhinted + 2:1 verify
./scripts/05-nerd-patch.sh     # optional Nerd + 2:1 --check-nerd
```

## Strict 2:1 verification

```bash
# needs fontTools (build venv under work/venv, or any env with fonttools)
python3 scripts/verify-2to1.py out/*.ttf
python3 scripts/verify-2to1.py --check-nerd out/nerd/*.ttf
```

| Set | Expected advance |
| --- | --- |
| Reference | `A` = half unit (usually 500 @ UPM 1000); `中` = 2× half |
| Half | ASCII `0x20–0x7E`, box/block `0x2500–0x259F`, halfwidth kana |
| Full | fullwidth forms, common CJK punct, CJK ideograph samples |
| Nerd (`--check-nerd`) | present Nerd/PUA icons = **half** (1 cell) |

**Epsilon** defaults to **0** (exact). Failures print codepoint, expected, and actual advances; process exits `1`.

### Known exceptions (not hard-gated)

- Geometric shapes / arrows / misc symbols may mix half and full in CJK mono; only the sets above are gated.
- Do **not** pass font-patcher `--mono` / `-s` on this family: it rewrites **all** glyph advances to one cell and **breaks CJK 2:1**. Use `--single-width-glyphs` only (what `05-nerd-patch.sh` does).

### Nerd strategy decision

| Question | Choice here |
| --- | --- |
| Build integration | **Secondary** step on `out/*.ttf` (not inlined into Sarasa Verda graph) |
| Icon width | **Single-cell** (`--single-width-glyphs`) |
| Glyph set | `--complete` (full Nerd set); subset by editing `PATCH_ARGS` in `05-nerd-patch.sh` |
| Publish name | Coexist: base Opt family + short `SarasaNZSSlab NFM` (post-rename) |
## Coding samples

See [`samples/`](samples/) for CN/EN code snippets and how to render 12–16px PNGs:

```bash
python3 scripts/render-coding-sample.py \
  --font out/SarasaMonoSlabNeoZhiSongSC-Opt-Regular.ttf \
  --sizes 12,14,16
```

## Quilt workflow (edit patches)

```bash
export QUILT_PATCHES="$PWD/patches"
cd work/Sarasa-Gothic          # after 01+02

quilt series
quilt pop -a                   # or push -a
# edit files, then:
quilt add path/to/file
# …edit…
quilt refresh                  # rewrite current patch under patches/
```

Keep patches **small and ordered**:

1. `0001` — pipeline capability (`verdafile.mjs`)
2. `0002` — product config (`config.json`)

Do **not** put multi‑MiB font binaries in git; CJK is fetched in `03-prepare-cjk.sh`.

## Family name

- English: `Sarasa Mono Slab NeoZhiSong Opt SC`
- Chinese: `等距更纱新致宋 Slab Opt SC`
- Nerd (after patch): patcher-generated `… Nerd Font` / Mono suffix

Experimental naming only; respect OFL / reserved font names if you redistribute.

## License notes

- Sarasa Gothic / IosevkaN: see upstream
- LXGW Neo ZhiSong: OFL (see upstream release)
- Nerd Fonts glyph sets / patcher: see [ryanoasis/nerd-fonts](https://github.com/ryanoasis/nerd-fonts) licenses
- Scripts & patches in this folder: MIT (same as repo root unless noted)
