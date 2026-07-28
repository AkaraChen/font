# Hyperlegible dual-width experiments (KIT-291)

Preview-only Latin **hyperlegible mono** × CJK sans pairings for accessibility
bake-off. **Not** a product pipeline (no outline merge ship, no Nerd patch,
no fingerprints).

Render method: dual FreeType faces on a forced **2:1** cell grid
(`render_dual.py`). CJK side uses system Noto Sans CJK SC (design-identical to
Source Han Sans SC) or LXGW Neo XiHei.

| # | Latin | CJK | Role |
| --- | --- | --- | --- |
| **HL-1** | Atkinson Hyperlegible Mono Regular | Noto Sans CJK SC | 标杆 |
| **HL-2** | Atkinson Hyperlegible Mono Regular | LXGW Neo XiHei `v1.304` | 双清晰 |
| **HL-4** | JetBrains Mono `2.304` Regular | Noto Sans CJK SC | 常规可读对照条 |

HL-3（阿里巴巴普惠体）skipped this run — CDN 403.

## Reproduce

```bash
# put faces under sources/ (gitignored):
#   AtkinsonHyperlegibleMono-Regular.ttf
#   JetBrainsMono-Regular.ttf
#   LXGWNeoXiHei.ttf
# Noto: /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc face 2

python3 render_dual.py --mode pair \
  --latin sources/AtkinsonHyperlegibleMono-Regular.ttf \
  --cjk /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc --cjk-index 2 \
  --body-file samples/coding-mixed-hl.txt \
  --title "HL-1 …" --out samples/rendered/HL-1-atkinson-noto-sc-dark.png
```

## Pins / license notes

| Face | Source | License |
| --- | --- | --- |
| Atkinson Hyperlegible Mono | [googlefonts/atkinson-hyperlegible-next-mono](https://github.com/googlefonts/atkinson-hyperlegible-next-mono) | **OFL 1.1** (RFN check before rename) · Braille Institute free-font page: https://www.brailleinstitute.org/freefont/ |
| Noto Sans CJK SC | Google / Adobe Source Han Sans | OFL |
| LXGW Neo XiHei | [lxgw/LxgwNeoXiHei](https://github.com/lxgw/LxgwNeoXiHei) | OFL |
| JetBrains Mono | [JetBrains/JetBrainsMono](https://github.com/JetBrains/JetBrainsMono) | OFL |
