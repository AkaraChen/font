# Experiment: Geometric mono × CJK (KIT-288)

Experimental dual-width pairings for **Geometric / 构造几何无衬线** coding style.
Not a product family — preview merges only (no Nerd patch / fingerprint / release).

## Combos

| ID | Latin | CJK | Metrics |
| --- | --- | --- | --- |
| **GE-1** | Fira Code 6.2 | Noto Sans SC (Source Han design) | EN 550 / CJK 1100 |
| **GE-2** | Geist Mono 1.7.2 | Noto Sans SC | EN 550 / CJK 1100 |
| **GE-3** | Space Mono | Noto Sans SC | EN 550 / CJK 1100 |

CJK note: Noto Sans SC = Google packaging of the Source Han Sans design (OFL).
Used fontsource subset TTF for fast experiment merges.

## Reproduce

```bash
# sources already under downloads/ + extract/ after fetch
python3 scripts/merge_dual.py \
  --latin-regular extract/fira/ttf/FiraCode-Regular.ttf \
  --sc-regular downloads/NotoSansSC-Regular.ttf \
  --out-dir out --family-ps GE1-FiraCodeNotoSC \
  --family "GE1 FiraCode NotoSC Dual" --latin-src-adv 1200

# Fira UPM=1950 → use --size 29 so cell px ≈ Geist/Space at size 15
python3 scripts/render-sample.py \
  --font out/GE1-FiraCodeNotoSC-Regular.ttf \
  --prefix GE-1 --themes dark --size 29 \
  --title "GE-1 · Fira Code + Noto Sans SC"
```

Outputs: `out/*.ttf`, `samples/rendered/GE-*-dark.png`.

## Observations (brief)

See issue KIT-288 final comment for the product-line recommendation.
