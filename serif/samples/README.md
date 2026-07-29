# Coding samples

Human-facing reference for **editor-size** CN/EN mono alignment (not a reading proof).

| File | Purpose |
| --- | --- |
| `coding-mixed.txt` | Source sample: mixed CN/EN, comments, box drawing, Nerd placeholders |
| `rendered/*.png` | Optional; generate after build (gitignored if large — re-render locally) |

## Render

```bash
cd serif
# after ./scripts/build.sh  → product is out/nerd/
python3 scripts/render-coding-sample.py \
  --font out/nerd/AKRSlabSCNFM-Regular.ttf \
  --sizes 12,14,16
```

Inspect the ruler lines:

```
# 0123456789012345678901234567890123456789
# |.........|.........|.........|.........|
# 中文中文中文中文中文中文中文中文中文中文
```

Each CJK cell should span **two** half-width columns.
