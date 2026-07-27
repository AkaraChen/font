# serif — MonoSlab × 霞鹜新致宋 Opt

Stable rebuild of the **KIT-234** experiment:

| Component | Source |
| --- | --- |
| Latin | Sarasa `IosevkaNSlab` (MonoSlab) |
| CJK | [LXGW Neo ZhiSong Plus](https://github.com/lxgw/LxgwNeoZhiSong) `v1.066` |
| Grid | 2:1 mono (`A=500` / `中=1000` after merge) |
| Weight match | pathops embolden **s=14** (Regular) / **s=32** (Bold) |
| Output | Unhinted TTF SC Regular + Bold |

Upstream tree is **not forked permanently**. Build scripts clone a **pinned ref** of [be5invis/Sarasa-Gothic](https://github.com/be5invis/Sarasa-Gothic) and apply **quilt** patches from `patches/`.

## Pins

See `pins.env`:

- `SARASA_REF=v1.0.40` / `SARASA_COMMIT=4b908c7…`
- `LXGW_TAG=v1.066`
- embolden strengths

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
    build.sh               # one-shot
    01-clone-sarasa.sh
    02-apply-quilt.sh
    03-prepare-cjk.sh
    04-build.sh
  work/                    # gitignored build tree
  out/                     # gitignored products
```

## Dependencies

- `git`, `curl`, `quilt`, `node` (≥ 20), `npm`
- `ttfautohint` (Sarasa latin prep)
- Python 3.10+ (`python3 -m venv` **or** `uv`) for `fonttools` + `skia-pathops`

AFDKO `otc2otf` is **not** required for this drop-in TTF path.

```bash
# Debian/Ubuntu example
sudo apt install git curl quilt nodejs npm ttfautohint python3-venv
# or: brew install quilt node ttfautohint
```

## Build

```bash
cd serif
./scripts/build.sh
# → out/SarasaMonoSlabNeoZhiSongSC-Opt-{Regular,Bold}.ttf
```

Step by step:

```bash
./scripts/01-clone-sarasa.sh   # clone pinned Sarasa
./scripts/02-apply-quilt.sh    # quilt push -a
./scripts/03-prepare-cjk.sh    # download LXGW, scale UPM, embolden
./scripts/04-build.sh          # npm run build ttf-unhinted
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

Experimental naming only; respect OFL / reserved font names if you redistribute.

## License notes

- Sarasa Gothic / IosevkaN: see upstream
- LXGW Neo ZhiSong: OFL (see upstream release)
- Scripts & patches in this folder: MIT (same as repo root unless noted)
