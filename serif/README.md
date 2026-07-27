# serif — SarasaNZSSlab NFM (Nerd Font Mono)

Coding mono: **Slab Latin (IosevkaNSlab)** + **霞鹜新致宋 Opt** + **Nerd icons**, strict **2:1** dual-width.

| Component | Source |
| --- | --- |
| Latin | Sarasa `IosevkaNSlab` (MonoSlab) |
| CJK | [LXGW Neo ZhiSong Plus](https://github.com/lxgw/LxgwNeoZhiSong) `v1.066` |
| Grid | 2:1 mono (`A=500` / `中=1000`) |
| Weight match | pathops embolden **s=14** (Regular) / **s=32** (Bold) |
| **Product** | **Nerd Font Mono** → `out/nerd/SarasaNZSSlabNFM-{Regular,Bold}.ttf` |
| Metrics gate | `scripts/verify-2to1.py --check-nerd` (after Nerd patch) |

Upstream is **not forked permanently**. Scripts clone a **pinned** [be5invis/Sarasa-Gothic](https://github.com/be5invis/Sarasa-Gothic) ref and apply **quilt** patches.

## Pins

See `pins.env`: Sarasa / LXGW / embolden strengths / `NERD_FONTS_TAG` + docker digest.

## Layout

```
serif/
  pins.env
  patches/                 # quilt series
  tools/embolden_cjk.py
  scripts/
    build.sh               # one-shot → Nerd product
    01…04-*.sh             # intermediate Sarasa build
    05-nerd-patch.sh       # Nerd patch + 2:1 --check-nerd
    package-release.sh     # zip out/nerd for GitHub Release
    verify-2to1.py
    rename_nerd_family.py
    render-coding-sample.py
  samples/
  work/                    # gitignored
  out/                     # intermediate pre-Nerd TTFs (gitignored)
  out/nerd/                # **product** (gitignored)
  dist/                    # release zips (gitignored)
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
```

### Patcher policy

- `--complete` + **`--single-width-glyphs`** (icons = 1 cell)
- **Never** `--mono` / `-s` — that forces *all* glyphs (incl. CJK) to 1 cell and breaks 2:1

## Verify

```bash
python3 scripts/verify-2to1.py --check-nerd out/nerd/*.ttf
```

| Set | Expected |
| --- | --- |
| `A` / half ASCII, box drawing, halfwidth kana | half unit (usually 500) |
| `中` / fullwidth / CJK samples | 2× half |
| Nerd/PUA icons present | half unit |

Epsilon default **0**. Exit `1` on failure with codepoint report.

Known non-gated mixes: geometric / arrows / misc symbols.

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
