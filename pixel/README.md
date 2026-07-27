# pixel — FusionPixel12 NFM

Coding product: **Fusion Pixel 12px monospaced** + **hand-drawn programming ligatures** + **Nerd Font Mono**.

| Component | Source | Notes |
| --- | --- | --- |
| Base | [Fusion Pixel Font](https://github.com/TakWolf/fusion-pixel-font) 12px mono `zh_hans` | dual-width EN 600 / CJK 1200 (1px = 100 U) |
| Ligatures | [`ligatures/ligatures.txt`](ligatures/ligatures.txt) | **hand-drawn** pixel art; `calt` type-4 GSUB |
| Icons | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) patcher | shipped as-is; single-cell icons |
| Product | Regular | `out/nerd/FusionPixel12NFM-Regular.ttf` |
| Family | Windows-safe ≤31 | **FusionPixel12 NFM** |

## Pipeline

```
01-fetch-sources    → pin-fetch Fusion 12px mono zip
02-add-ligatures    → draw ligatures/ligatures.txt into the base + calt GSUB
03-narrow-ambiguous → EAW=Ambiguous punctuation → 1 cell (donor: latin flavor)
04-nerd-patch       → Nerd complete + --single-width-glyphs (no --mono)
05-verify           → advances / calt / EAW / Nerd PUA gates
preview             → HarfBuzz render sheets (not part of build.sh)
```

```bash
cd pixel
./scripts/build.sh
# → out/nerd/FusionPixel12NFM-Regular.ttf
```

## Ligatures

Every ligature is **drawn by hand** on Fusion's own 12-row pixel grid, in
[`ligatures/ligatures.txt`](ligatures/ligatures.txt). Nothing is traced, scaled
or rasterized from a donor font — what is in the art file is exactly what ships.

```
@ ->
............
............
............
.......#....
........#...
.........#..
###########.
.........#..
........#...
.......#....
............
............
```

- 12 rows (`ascent 1000`, `descent -200`, 100 units per pixel).
- 6 columns per character cell; an N-character ligature is `6N` columns and
  advances `N × 600`, so columns never shift when a ligature fires.
- `#` becomes one square contour; `.` is empty.
- `build_ligatures.py` **hard-fails** on a wrong row count, a wrong row width or
  a stray character. A drawing that looks wrong is fixed by editing its picture.

### Shipped set (31)

| Cells | Sequences |
| --- | --- |
| 2 | `==` `!=` `<=` `>=` `=>` `->` `<-` `<>` `\|>` `<\|` `++` `--` `//` `/*` `*/` `:=` `::` |
| 3 | `===` `!==` `<=>` `<->` `-->` `<--` `==>` `<==` `...` `///` `/**` `**/` `::=` |
| 4 | `<!--` |

Deliberately **not** drawn: `&&`, `||`, `**`. Fusion's `&`, `|` and `*` are
already 5 columns wide, so pulling a pair closer than the 6-column pitch just
collides their arms into a blob. They stay legible as plain characters.

Longest match wins inside each first-glyph bucket, so `<!--` beats `<--` beats
`<-`, and `-->` beats `--`.

### Adding or fixing one

1. Edit the picture in `ligatures/ligatures.txt`.
2. `./scripts/02-add-ligatures.sh`
3. `./scripts/preview.sh` and **look at it**.

### Previewing

Use `scripts/preview.sh` (HarfBuzz `hb-view` + FreeType). Do **not** hand-roll a
previewer: a naive "fill each contour with squares" renderer cannot handle
Fusion's multi-contour glyphs with counters (`t`, `f`, `e`, quotes) and paints
them as solid blocks, which reads as a font bug that isn't there.

```bash
./scripts/preview.sh                 # newest product in out/
./scripts/preview.sh path/to/x.ttf   # → out/preview/*.png + sheet.png
```

## Ambiguous-width punctuation

A terminal never asks the font how wide a character is — it sizes the cell from
wcwidth, and `EAW=Ambiguous` codepoints get **one** cell everywhere by default.
Fusion's `zh_hans` flavor draws these nine at **1200** (two cells) with the ink
parked in the right half, so `“心` paints the quote straight on top of the
following character:

| | `“` `”` `‘` `’` | `…` `·` `‥` `․` `‧` |
| --- | --- | --- |
| Fusion `zh_hans` (base) | 1200 | 1200 |
| Fusion `latin` / `ja` / `ko` | 600 | 600 |
| **Product** | **600** | **600** |

`03-narrow-ambiguous.sh` transplants the half-width drawings from the `latin`
flavor of the **same release** (`FUSION_TTF_HALFWIDTH_DONOR` in `pins.env`) —
same 12px grid, same hand, nothing scaled or redrawn. Targets are derived by
comparing the two flavors, not hard-coded, and a donor glyph whose ink escapes
`[0, 600]` is a hard failure. `05-verify.sh --check-eaw` gates the result.

Same class of bug — and same remedy — as `serif/scripts/06-narrow-symbols.sh`,
which pulls 1-cell symbols from Sarasa **Term**.

## Patcher policy

- `--complete` + **`--single-width-glyphs`** (icons = 1 cell)
- **Never** `--mono` / `-s` — that would force CJK to 1 cell and break 2:1
- Pin: `NERD_FONTS_TAG` in `pins.env` (currently **v3.4.0**)

> **Known upstream breakage:** the pinned `nerdfonts/patcher` image (and its
> current `latest`, same digest) ships **without fontforge**, so the Docker path
> fails with `/bin/sh: fontforge: not found`. Use the local path until upstream
> republishes: `brew install fontforge`, then
> `NERD_PATCH_METHOD=fontforge ./scripts/04-nerd-patch.sh`.

## Pins

See [`pins.env`](pins.env). Do not bump casually.

## Dependencies

- `bash`, `curl`, `unzip`, `zip`
- Python 3.10+ via `uv` or `venv` → `fonttools`
- **Nerd patch** — `fontforge` (see the note above), or Docker once fixed
- **Preview** (optional) — `harfbuzz` (`hb-view`), `imagemagick` to stack sheets

## Verify

```bash
./scripts/05-verify.sh
# or:
work/venv/bin/python scripts/verify.py \
  --half 600 --full 1200 --check-nerd --check-ligatures --check-eaw \
  out/nerd/*.ttf
```

| Check | Expected |
| --- | --- |
| `A` / ASCII | advance **600** |
| `中` | advance **1200** |
| `post.isFixedPitch` | **1** |
| GSUB `calt` + `liga_u*` glyphs | present (hand-drawn) |
| Nerd sample PUA | present @ half advance |
| `“ ” ‘ ’ … · ‥ ․ ‧` | advance **600**, ink inside the cell |

## License notes

- Fusion Pixel Font: OFL (`licenses/OFL-Fusion-Pixel.txt`)
- Ligature drawings in `ligatures/ligatures.txt`: original work, MIT (repo root)
- Nerd Fonts glyphs / patcher: [ryanoasis/nerd-fonts](https://github.com/ryanoasis/nerd-fonts)
- Scripts here: MIT (repo root) unless noted

Product family name is a project source-encoding label; review RFN before public OFL redistribution.
