# handwriting — RadonWenKai NFM

Handwriting-flavoured coding mono: **Monaspace Radon** Latin + **霞鹜文楷 LXGW WenKai** CJK,
strict **2:1** dual width, **Nerd icons**, ligatures **on by default**, and a CJK side sheared
to Radon's own lean.

![sample](samples/rendered/sample-dark.png)

| Component | Source | Pin |
| --- | --- | --- |
| Latin / icons | [Monaspace Radon **NF**](https://github.com/githubnext/monaspace) (pre-patched Nerd build) | **v1.400** |
| CJK | [LXGW WenKai 霞鹜文楷](https://github.com/lxgw/LxgwWenKai) Medium | **v1.522** |
| Grid | EN cell / CJK cell | **500 / 1000** (UPM 1000) |
| CJK slant | measured from Radon's stems | **7.5°** |
| Weight match | measured stems, Latin vs CJK | Regular: WenKai **Medium**, no embolden · Bold: Medium **+ s=15** |
| Ligatures | Radon `liga` + `calt` **+ ss01–ss10 folded into calt** | on by default |
| Product | Regular + Bold | `out/RadonWenKaiNFM-{Regular,Bold}.ttf` |

```bash
cd handwriting && ./scripts/build.sh
# → out/RadonWenKaiNFM-{Regular,Bold}.ttf   (~3.5 min, ~330 MiB of upstream never downloaded)
```

## The four things this build actually had to solve

### 1. 2:1 on a font whose cell is 0.62 em

Monaspace draws a **1240/2000** em cell. Pair that with a 1 em Han glyph and you get a choice
between gappy CJK (ink filling 62 % of its two cells) or a brutal Latin squeeze. The recipe
here is the one [LXGW Bright Code](https://github.com/lxgw/LxgwBright-Code) uses for
Argon × WenKai: **x-narrow 1240 → 1111**, then scale the whole Latin face to **90 %**. The cell
lands on exactly 1000/2000 em = **0.5 em**, and WenKai is used at its native 1000 advance,
untouched horizontally.

Net Latin transform: `x × 0.4032`, `y × 0.45` into a 1000 UPM box → cap height 679, x-height 483,
Han ink ≈ 854 tall. CJK ink / Latin cap ≈ **1.26**, which is the comfortable band for mixed text.

### 2. Slant: Radon leans, and `italicAngle` lies

`post.italicAngle` is **0** for upright Radon — but it is a handwriting design and its stems
actually lean right. `scripts/measure-slant.py` regresses the ink-centre axis of the
straight-stem letters and reports the median:

| Face | I | H | T | k | E | **median** | round letters (o a d, excluded) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Radon Regular | 7.91° | 7.52° | 7.52° | 7.63° | 4.91° | **7.52°** | 23.7° / 23.5° / 25.4° |
| Radon Bold | 9.21° | 8.10° | 7.50° | 8.70° | 4.46° | **8.10°** | 24.0° / 21.9° / 26.2° |

Round and asymmetric letters read several degrees high (their widest point is not at
mid-height), so they are measured but not used. WenKai is sheared by the pinned
`CJK_SLANT_DEG=7.5` — one angle for the whole family, so mixed-weight text stays coherent —
about `y = 375` (≈ half the Han ink height) so glyphs stay centred in their cell instead of
drifting right at the top. For reference, Radon *Italic* measures ~18°, i.e. its declared
`-11°` on top of the 7.5° the upright already has.

### 3. Weight: Monaspace runs heavy, WenKai has no Bold

Stem widths are measured, not eyeballed — scanline vertical-stem medians at UPM 1000
(`scripts/calibrate_cjk_weight.py`, sharing `fontkit.measure`):

| CJK candidate | v-stem | Δ vs Radon Regular (73.3) | Δ vs Radon Bold (107.2) |
| --- | ---: | ---: | ---: |
| WenKai Light | 55.3 | −18.1 | −51.9 |
| WenKai Regular | 65.8 | −7.5 | −41.4 |
| **WenKai Medium** | 77.6 | **+4.3** | −29.6 |
| WenKai Medium + embolden s=15 | 107.7 | — | **+0.5** |

So **Radon Regular pairs with WenKai Medium**, not Regular — the same mapping LXGW Bright Code
documents. Regular ships **unstroked**: WenKai Regular + `s=4` would match verticals exactly
(+0.5) but leaves horizontals 9 units light and rounds off the brush entries and exits, and a
real design weight beats a stroked one. Bold has no choice — WenKai ships nothing heavier than
Medium — so it is emboldened to `s=15`.

Kai horizontals stay thinner than Latin by design (68–75 vs 78 in Regular); that contrast is the
typeface, not a defect. Verticals are what carry optical weight in mixed CN/EN mono text.

### 4. Ligatures that are actually on

Monaspace parks nearly every coding ligature in **stylistic sets**, not in `liga`/`calt` —
default `calt` does texture healing, and `liga` carries almost nothing. Editors that only flip
"font ligatures" (= `calt`) therefore show a Radon with ligatures apparently off. Probing each
set (shape a battery, diff the glyph run) gives:

| Set | Ligates |
| --- | --- |
| `ss01` | `=` family — `==` `===` `!=` `!==` |
| `ss02` | `<=` `>=` |
| `ss03` | arrows — `->` `<-` `<!--` |
| `ss04` | markup — `</>` |
| `ss05` | pipes — `\|>` |
| `ss06` | repeats — `+++` `###` `___` |
| `ss07` | `::` |
| `ss08` | raised-dot ranges — `..=` `..<` |
| `ss09` | `=>` |
| `ss10` | nothing in the probe battery (folded for completeness) |

`05-expand-ligatures.sh` unions those lookups into every `calt` feature record (reusing
`serif/scripts/expand-default-ligatures.py`, which does the same job for Iosevka's `dlig`).
The `ss**` features stay intact for anyone toggling them individually.

The gate for this is a **shaping** test, not a tag check: `verify-features.py` runs HarfBuzz over
`== === != -> <- => <= >= :: |>` with only `liga`+`calt` on and fails if any sequence comes back
as its plain glyphs. Before the fold it scores 1/10; after, 10/10.

## Nerd icons

The product is a **Nerd Font Mono**: every icon sits on one cell. That comes for free from the
upstream `MonaspaceRadonNF-*` build, where all 12 697 glyphs — 2 320 PUA icons included — share
the single 1240 cell, so the same 0.4032 x-scale that makes ASCII 500 makes the icons 500. No
patcher, no FontForge, no Docker in this tree (unlike `serif/`).

The 315 MiB `monaspace-nerdfonts-*.zip` is never downloaded: `fetch_zip_member.py` reads the
zip's central directory with two ranged GETs and inflates just the two OTFs it needs (~2.3 MiB
each), checked against both the zip's CRC-32 and a pinned sha256.

## Character policy

| Source | Role |
| --- | --- |
| **Radon** (base font, kept whole) | ASCII, Latin, Greek/Cyrillic, programming symbols, box drawing, **Nerd icons**, **all layout tables** |
| **WenKai** (imported, sheared) | Han, CJK punctuation, fullwidth forms, kana, bopomofo, every East_Asian_Width W/F codepoint, and anything Radon lacks |

Radon stays the **base** font, which is why `GSUB`/`GDEF` never has to be merged and the
ligatures survive at all. Imported advances follow **East_Asian_Width**, because that is what a
terminal sizes cells by (it never asks the font): `W`/`F` → full cell, everything else → half
cell, with proportional fallbacks x-compressed to fit (1 121 glyphs). Glyphs WenKai already
draws for their cell keep their designed side bearings — no recentring, since CJK bearings are
deliberately asymmetric and sheared outlines are *meant* to overhang slightly.

Two subtleties the gate caught:

- WenKai maps several codepoints to one outline even when Unicode disagrees about their width
  (`U+205A ⁚` shares its glyph with a fullwidth colon). Such a glyph is **forked** per cell, or
  the last import silently wins the advance.
- 42 EAW-wide codepoints (`⚡ ⏩ 🕐 〈 〉 …`) exist only in Radon at one cell, while terminals
  give them two. Their advance moves to the full cell and the outline is centred — the same call
  `fontkit.narrow_symbol_widths` makes for this case.

## Layout

```
handwriting/
  pins.env                 # upstream refs, grid, slant, weight-match, naming
  licenses/                # OFL-Monaspace.txt · OFL-LXGWWenKai.txt (refreshed by 01-)
  scripts/
    build.sh               # one-shot 01 → 06
    01-fetch-sources.sh    # ranged zip member fetch + WenKai TTFs + OFLs
    02-prepare-latin.sh    → prepare_latin.py      # CFF→glyf, narrow+scale to the half cell
    03-prepare-cjk.sh      → prepare_cjk.py        # embolden (measured) then shear
    04-merge.sh            → merge_radon_wenkai.py # import by EAW, keep Radon layout
    05-expand-ligatures.sh # fold ss01–ss10 into default calt
    06-verify.sh           # 2:1 + EAW + Nerd cells, features, stroke report
    calibrate-stroke.sh    → calibrate_cjk_weight.py + measure-slant.py
    fetch_zip_member.py    # HTTP-range single-member zip extraction
    verify-features.py     # feature + HarfBuzz shaping gate
    render-sample.py       # HarfBuzz + FreeType sample (Pillow cannot shape)
    package-release.sh
  samples/coding-mixed.txt · samples/rendered/
  work/ out/ dist/         # gitignored
```

Shared rather than duplicated, from [`../lib/fontkit/`](../lib/fontkit/):
`fontkit.measure`, `fontkit.embolden`, `fontkit.verify2to1`,
`serif/scripts/expand-default-ligatures.py`.

## Dependencies

- `bash`, `curl` (must support `Range`), `zip`
- Python 3.10+ (`uv` or `venv`) → `fonttools`, `skia-pathops`, `uharfbuzz`
- optional, sample render only: `Pillow`, `freetype-py`, `numpy`

No FontForge, no Docker, no Node — the whole build is Python over two OFL fonts.

## Verify

```bash
./scripts/06-verify.sh
# or individually:
python3 -m fontkit.verify2to1 --profile dense --check-nerd --check-eaw out/RadonWenKaiNFM-*.ttf
python3 scripts/verify-features.py --expect-half 500 out/RadonWenKaiNFM-*.ttf
```

| Check | Expected |
| --- | --- |
| ASCII / box drawing / halfwidth kana | 500 |
| Han / fullwidth / CJK punctuation | 1000 |
| every `EAW` `W`/`F` codepoint | 1000 |
| every `EAW` `N`/`Na`/`H` codepoint | 500 |
| Nerd / PUA icons (9 164 checked) | 500 |
| `post.isFixedPitch` / PANOSE `bProportion` | 1 / 9 (hosts' "is this mono?" flags) |
| `liga` `calt` `ccmp` `locl` + ss/cv sets | present |
| `== === != -> <- => <= >= :: \|>` under `liga`+`calt` only | all ligate (10/10) |

`--check-eaw` is the gate that matters for terminal alignment: a terminal sizes each cell from
Unicode's EAW table via `wcwidth()`, never from the font.

## Re-deriving the pins

```bash
./scripts/calibrate-stroke.sh
# → slant table (CJK_SLANT_DEG), weight survey (WENKAI_FOR_*), embolden sweep (CJK_EMBOLDEN_*)
```

Nothing in `pins.env` is a guess; every number above came out of that script. Change pins in a
dedicated commit with the new measurement in the message.

## Sample render

```bash
work/venv/bin/python scripts/render-sample.py --font out/RadonWenKaiNFM-Regular.ttf
# → samples/rendered/sample-{dark,light}.png
```

Pillow only shapes text when built with libraqm, which would render `!=` as two glyphs and make
a ligature font look broken in its own screenshot — so the sample shapes with HarfBuzz and
rasterises glyph outlines with FreeType.

## Release package

```bash
./scripts/package-release.sh 0.1.0
# → dist/RadonWenKaiNFM-0.1.0.zip
```

## Family / license

- **Product family:** `RadonWenKai NFM` (Regular / Bold), PostScript `RadonWenKaiNFM-*`
- Upstream is **SIL OFL 1.1** on both sides; `licenses/` copies travel with the product
- ⚠ **Reserved font names.** Monaspace reserves `Monaspace` **and its subfamily names, including
  `Radon`**; WenKai reserves 霞鹜 / 霞鶩 / 落霞孤鹜 / 落霞孤鶩 / `LXGW` (the Latin "WenKai" is not
  listed). `RadonWenKai NFM` is a project source-encoding label in the same style as
  `LilexSansSC Dual` — fine for local use, but **rename before any public redistribution**.
  WenKai's OFL also carries an additional permission worth reading if you plan to ship this.
- Build scripts here: MIT (repo root) unless noted

## Known limits

1. WenKai's own `GSUB`/`GPOS` is not merged (no CJK `locl` / vertical forms; `vmtx`/`vhea` dropped)
2. No Italic face — Radon Italic (−11° on top of the intrinsic lean) is a future weight pair
3. No hinting: WenKai's `prep`/`gasp` are dropped with the outline transform and Radon NF ships none
4. Regular's CJK verticals run ~6 % heavier than the Latin's (real design weights land where they land)
5. `ss10`'s contents are unidentified — folded into `calt` on the assumption it is a ligature set
6. Ambiguous-width (`EAW=A`) codepoints are left at whatever the source gives; terminals let
   users choose 1 or 2 cells for those
