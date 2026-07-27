# pixel — FusionPixel12 NFM

Coding product: **Fusion Pixel 12px monospaced** + **pixelized programming ligatures** + **Nerd Font Mono**.

| Component | Source | Notes |
| --- | --- | --- |
| Base | [Fusion Pixel Font](https://github.com/TakWolf/fusion-pixel-font) 12px mono `zh_hans` | dual-width EN 600 / CJK 1200 (1px = 100 U) |
| Ligatures | [Lilex](https://github.com/mishamyrt/Lilex) `.liga` outlines | **pixelized** onto the 12px grid; `calt` type-4 GSUB |
| Icons | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) patcher | **not** pixelized; single-cell icons |
| Product | Regular | `out/nerd/FusionPixel12NFM-Regular.ttf` |
| Family | Windows-safe ≤31 | **FusionPixel12 NFM** |

## Pipeline

```
01-fetch-sources   → pin-fetch Fusion 12px mono zip + Lilex zip
02-add-ligatures   → pixelize donor .liga (+ a few synth: => -> <- <=>)
03-nerd-patch      → Nerd complete + --single-width-glyphs (no --mono)
04-verify          → advances / calt / Nerd PUA gates
```

```bash
cd pixel
./scripts/build.sh
# → out/nerd/FusionPixel12NFM-Regular.ttf
```

### Ligature pixelization

Donor ligatures (Lilex) are mono **1-cell** drawings. We:

1. Stretch each outline across **N half-cells** (N = character count) so column alignment stays stable when ligatures fire.
2. Rasterize onto a **12 × (6N)** pixel grid (Fusion metrics: ascent 1000 / descent −200 / 100 U per pixel).
3. Rebuild square contours and install under `calt` as GSUB ligature substitutions.

Nerd / PUA icons are applied **after** this step and left as the patcher ships them.

### Patcher policy

- `--complete` + **`--single-width-glyphs`** (icons = 1 cell)
- **Never** `--mono` / `-s` — that would force CJK to 1 cell and break 2:1
- Pin: `NERD_FONTS_TAG` in `pins.env` (currently **v3.4.0**)

## Pins

See [`pins.env`](pins.env). Do not bump casually.

## Dependencies

- `bash`, `curl`, `unzip`, `zip`
- Python 3.10+ via `uv` or `venv` → `fonttools`, `Pillow`
- **Nerd patch** — one of:
  1. **Docker** (preferred): image in `pins.env`
  2. **Local**: `fontforge` + FontPatcher.zip

## Verify

```bash
./scripts/04-verify.sh
# or:
work/venv/bin/python scripts/verify.py \
  --half 600 --full 1200 --check-nerd --check-ligatures \
  out/nerd/*.ttf
```

| Check | Expected |
| --- | --- |
| `A` / ASCII | advance **600** |
| `中` | advance **1200** |
| `post.isFixedPitch` | **1** |
| GSUB `calt` + `liga_u*` glyphs | present (pixelized) |
| Nerd sample PUA | present @ half advance |

## License notes

- Fusion Pixel Font: OFL (`licenses/OFL-Fusion-Pixel.txt`)
- Lilex (ligature donor shapes): OFL (`licenses/OFL-Lilex.txt`) — RFN **“Lilex”**
- Nerd Fonts glyphs / patcher: [ryanoasis/nerd-fonts](https://github.com/ryanoasis/nerd-fonts)
- Scripts here: MIT (repo root) unless noted

Product family name is a project source-encoding label; review RFN before public OFL redistribution.
