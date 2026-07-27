# radon — RadonWenKai Dual / NFM

Coding dual-width face: **Monaspace Radon** (Latin / programming, coding ligatures) + **霞鹜文楷 LXGW WenKai** (CJK), strict **2:1** grid, optional **Nerd Font Mono** patch.

| Component | Source | Pin |
| --- | --- | --- |
| Latin / mono | [Monaspace Radon Frozen](https://github.com/githubnext/monaspace) | `v1.400` |
| CJK | [LXGW WenKai Medium](https://github.com/lxgw/LxgwWenKai) | `v1.522` |
| Grid | EN cell / CJK cell @ UPM 1000 | **620 / 1240** |
| CJK lean | mild pseudo-oblique | **8°** (Radon Italic is −11°) |
| CJK weight | pathops embolden vs measured Radon stems | Regular `s=12`, Bold `s=30` |
| Product | Dual + NFM | `out/RadonWenKaiDual-*.ttf`, `out/nerd/RadonWenKaiNFM-*.ttf` |

Inspired by [LXGW Bright Code](https://github.com/lxgw/LxgwBright-Code) (Argon × WenKai) and this repo’s `sans/` merge + `serif/` Nerd/stroke tooling.

## Why these metrics

- Monaspace native: **UPM 2000**, mono advance **1240** → after `scale_upem(1000)`: **EN 620**.
- No X-crush on Radon outlines (unlike Plex 600→550). CJK cell = **2 × 620 = 1240** (outline unscaled; advance expanded & centred).
- Weight pairing follows Bright Code: product **Regular** = Radon Regular + WenKai **Medium** (closer stems than WenKai Regular).

### Stroke-width comparison (UPM 1000, scanline median)

| Face | stroke_median (approx.) |
| --- | ---: |
| Radon Regular Latin | ~90.7 |
| Radon Bold Latin | ~130.5 |
| WenKai Regular CJK | ~62.9 |
| WenKai Medium CJK (raw) | ~74.8 |
| Medium + embolden s=12 | ≈ Radon Regular (中 v≈101 vs Latin v≈91) |
| Medium + embolden s=30 | ≈ Radon Bold (中 v≈137 vs Latin v≈134) |

Re-measure / re-calibrate:

```bash
./scripts/01-fetch-sources.sh
./scripts/calibrate-stroke.sh   # slow: full-font embolden sweep
# then edit CJK_EMBOLDEN_REGULAR / CJK_EMBOLDEN_BOLD in pins.env
```

## Name recipe

| Token | Meaning |
| --- | --- |
| **Radon** | Monaspace Radon (Latin) |
| **WenKai** | 霞鹜文楷 (CJK) |
| **Dual** | dual-width 2:1 base product |
| **NFM** | Nerd Font Mono (icons 1-cell; CJK stays 2-cell) |

- Family (Dual): `RadonWenKai Dual`
- Family (Nerd): `RadonWenKai NFM`
- Not an official GitHub Next / lxgw face. Upstream OFL reserved names apply to redistributed derivatives.

## Ligatures

Frozen Radon ships coding ligatures under **`calt` / `dlig` / `rlig`** (TrueType). Static Monaspace OTFs also expose `liga` + `ss01`–`ss10` but are CFF; this build stays on Frozen TTF so merge + Nerd patch stay in the TrueType pipeline.

Enable **contextual alternates / discretionary ligatures** in your editor for `=>`, `!=`, `<=`, etc.

## Layout

```
radon/
  pins.env
  licenses/
  scripts/
    build.sh              # fetch → prepare → merge → verify → nerd
    01-fetch-sources.sh
    02-prepare-cjk.sh     # embolden + oblique
    03-merge.sh
    04-verify.sh
    05-nerd-patch.sh
    merge_radon.py
    oblique_cjk.py
    calibrate-stroke.sh
    render-sample.py
    package-release.sh
  tools/
    measure_stroke_width.py
    embolden_cjk.py
  samples/
  work/   # gitignored
  out/    # gitignored
  dist/   # gitignored
```

## Dependencies

- `bash`, `curl`, `unzip`, `zip`
- Python 3.10+ → `fonttools`, `skia-pathops`, optional `Pillow`
- Nerd patch: **docker** (`nerdfonts/patcher`) or **fontforge**

```bash
# Debian/Ubuntu example
sudo apt install curl unzip zip python3-venv
# optional: docker or fontforge for Nerd patch
```

## Build

```bash
cd radon
./scripts/build.sh
# → out/RadonWenKaiDual-Regular.ttf
# → out/RadonWenKaiDual-Bold.ttf
# → out/nerd/RadonWenKaiNFM-*.ttf   (if docker/fontforge available)
```

### Sample render

```bash
work/venv/bin/python scripts/render-sample.py \
  --font out/RadonWenKaiDual-Regular.ttf \
  --title "RadonWenKai Dual · EN 620 / CJK 1240"
# → samples/rendered/sample-{dark,light}.png
```

### Release package

```bash
./scripts/package-release.sh 0.1.0
# → dist/RadonWenKai-0.1.0.zip
```

## Character policy

| Source | Role |
| --- | --- |
| **Monaspace Radon** (UPM→1000, cell 620) | ASCII, Latin, digits, programming symbols, Greek/Cyrillic Radon ships, coding ligatures |
| **WenKai Medium** (emboldened + 8° oblique, advance 1240) | Han, CJK punctuation / symbols, fullwidth forms, and any codepoint Radon lacks |

## Verify

```bash
python3 scripts/verify-2to1.py --expect-half 620 out/RadonWenKaiDual-*.ttf
```

| Set | Expected |
| --- | --- |
| `A` / printable ASCII | **620** |
| `中` / sample Han / fullwidth | **1240** (= 2× EN) |
| `post.isFixedPitch` | **1** (fixed 2:1 grid) |
| GSUB | at least one of `calt` / `dlig` / `liga` / `rlig` |

## License

- Monaspace: SIL OFL 1.1 (see `licenses/LICENSE-Monaspace.txt`)
- LXGW WenKai: SIL OFL 1.1 (see `licenses/OFL-LXGW-WenKai.txt`)
- Build scripts in this folder: MIT (repo root) unless noted

## Upstream links

- Monaspace: <https://github.com/githubnext/monaspace>
- Monaspace site (Radon): <https://monaspace.githubnext.com/>
- LXGW WenKai: <https://github.com/lxgw/LxgwWenKai>
- LXGW Bright Code (Argon reference): <https://github.com/lxgw/LxgwBright-Code>
