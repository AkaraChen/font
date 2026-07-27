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
    fix-terminal-metrics.py
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
- Pin: `NERD_FONTS_TAG` in `pins.env` (currently **v3.4.0**, current upstream latest)
- After rename: `fix-terminal-metrics.py` sets `OS/2.xAvgCharWidth` to the half-cell and recomputes `head` bbox from half/full glyphs only (see Troubleshooting)

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

## Troubleshooting (terminal alignment / Nerd icons)

Measured on **v0.1.0** `SarasaNZSSlabNFM-Regular.ttf` (and re-checked after metric fix):

| Observation | Cause | What to do |
| --- | --- | --- |
| Nerd PUA icons (Powerline `U+E0B0`/`E0B2`, FA, Material, …) | Advances are **half** (500). `verify-2to1.py --check-nerd` gates this. | Nothing — patch path is correct (`--single-width-glyphs`, not `--mono`). |
| Unicode triangles `▲▶▼◀` (`U+25B2`…`25C0`) look “fullwidth” | These are **not** Nerd glyphs. Base **Mono** CJK design sets advance **1000** (2 cells). Same for most arrows / geometric / ★ / ✓ / `…` / `—`. | Prefer Powerline / Nerd codepoints in prompts (`\ue0b0`), or switch the Sarasa family to **Term**/**Fixed** if you want more ambiguous symbols half-cell (product trade-off). |
| “Nerd symbols look ugly / squashed” | `--single-width-glyphs` forces icons into **1** cell; many source icons were drawn for ~1.5–2 cells. Patcher is **v3.4.0** (not an ancient script). | Expected for NFM; try fewer glyph sets (drop `--complete`) or accept Nerd Font **Propo** only outside strict grids. |
| Large empty band on the **right** of the terminal after selecting this font | Dual-width font: ~33k glyphs @1000 + ~18k @500 → raw `OS/2.xAvgCharWidth≈832`. Some hosts treat that average (or a huge `head.xMax` from multi-em dashes) as the monospaced cell width. Also `post.isFixedPitch=0` (correct for 2:1). | Rebuild with current `05-nerd-patch.sh` (runs `fix-terminal-metrics.py`: `xAvgCharWidth=half`, tighter head bbox). Confirm terminal uses font advances / wcwidth, not average width. |
| Mixed CN/EN column drift | Half vs full advances are intentional 2:1 (`A=500`, `中=1000`). Drift usually comes from **full-width punctuation/symbols** in the line (see non-gated set above), not from broken CJK metrics. | Use the coding sample ruler in `samples/coding-mixed.txt`; avoid fullwidth ASCII (`ＵＴＦ`) in code. |

```bash
# Re-apply metric hygiene only (on already-patched TTFs):
python3 scripts/fix-terminal-metrics.py out/nerd/*.ttf
python3 scripts/verify-2to1.py --check-nerd out/nerd/*.ttf
```

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
