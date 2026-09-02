# work — AKR Work SC NFM

Coding dual-width face: **CaskaydiaCove Nerd Font Mono** (Cascadia Code Latin +
Nerd icons, Nerd Fonts v3.5.1) × **阿里巴巴普惠体 3.0** (CJK, Level 1+2),
strict **2:1**, **three weights** (Light / Regular / Bold), upright only.

The Latin donor is the pre-patched zip the family pins — there is no second
`font-patcher` pass. The CJK donor is **not OFL**; see
[`licenses/Alibaba-PuHuiTi.txt`](licenses/Alibaba-PuHuiTi.txt).

| Component | Source | Pin |
| --- | --- | --- |
| Latin / icons | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) `CascadiaCode.zip` Mono members | **v3.5.1** |
| CJK | [阿里巴巴普惠体 3.0](https://www.alibabafonts.com) Level 1+2 TTF | **3.01** Light / Regular / SemiBold |
| Grid | EN cell / CJK cell | **500 / 1000** (UPM 1000) |
| Weight match | measured vertical stems | Light: 45 Light **s=0** · Regular: 55 Regular **s=4** · Bold: 75 SemiBold **s=3** |
| Product | Light + Regular + Bold | `out/AKRWorkSCNFM-{Light,Regular,Bold}.ttf` |

```bash
just build work
# → out/AKRWorkSCNFM-{Light,Regular,Bold}.{ttf,woff2}
```

## Why this pairing

Cascadia Code is a ligature-bearing coding mono (Windows Terminal / VS Code).
PuHuiTi is a modern 黑体. Together they are a workhorse Latin×CJK coding face,
distinct from `sans/` (Lilex × Plex Sans).

## What the build solves

### 1. 2:1 from a 2048 UPM mono cell

CaskaydiaCove's cell is **1200/2048**. `scale_upem` to 1000 leaves **586**, and
hints have to be dropped (same Courier Prime trap: bytecode still measures in
2048). An X-scale lands ASCII on **500**; PuHuiTi Han (native advance **984**)
is placed on **1000**.

### 2. Stroke weight (measured, not guessed)

Scanline vertical-stem medians @ UPM 1000 after Latin is on the product grid:

| Face | v-stem | Match |
| --- | ---: | --- |
| Cascadia Light @ 500 | **55.0** | target |
| PuHuiTi 45 Light | 57.5 | Δ +2.5 → **s=0** |
| Cascadia Regular @ 500 | **87.5** | target |
| PuHuiTi 55 Regular | 79.5 | Δ −8.0 |
| **PuHuiTi Regular + s=4** | **87.5** | **Δ 0** |
| Cascadia Bold @ 500 | **110.0** | target |
| PuHuiTi 85 Bold | 118.5 | Δ +8.5 too heavy |
| PuHuiTi 75 SemiBold | 104.5 | Δ −5.5 |
| **PuHuiTi SemiBold + s=3** | **110.5** | **Δ +0.5** |

### 3. Three-weight RIBBI

Windows name ID 2 only understands Regular / Bold / Italic / Bold Italic. Light
moves into name ID 1 (`AKR Work SC NFM Light`) and ID 2 stays `Regular`. IDs
16/17 carry the real grouping.

## Name recipe

| Token | Meaning |
| --- | --- |
| **AKR** | this repository's house name |
| **Work** | Cascadia Code Latin × 阿里巴巴普惠体 CJK |
| **SC** | Simplified Chinese CJK master (Level 1+2) |
| **NFM** | Nerd Font Mono product (icons at one cell, from the zip) |

- Family (name ID 16): `AKR Work SC NFM`
- Light name ID 1: `AKR Work SC NFM Light` (20 chars, Windows ≤ 31)
- PostScript / file stem: `AKRWorkSCNFM`
- Not an official Cascadia / Nerd Fonts / Alibaba face.

## Licence

- Latin / Nerd: SIL OFL 1.1 ([`licenses/OFL-CascadiaCode.txt`](licenses/OFL-CascadiaCode.txt)). Reserved Font Name **Cascadia Code**.
- CJK: Alibaba's own notice ([`licenses/Alibaba-PuHuiTi.txt`](licenses/Alibaba-PuHuiTi.txt)). **Not OFL.** The merge is a modification of that font software.

## Pins

Everything reproducible lives in [`font.toml`](font.toml).
