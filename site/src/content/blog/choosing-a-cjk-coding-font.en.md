---
title: "Choosing a CJK coding font: check the grid before the glyphs"
description: What actually decides whether a CJK monospace font works is the 2:1 grid, symbol widths and icon cells — not how the glyphs look. Here is what to check, and what each upstream (LXGW WenKai, Iosevka, IBM Plex Sans SC and others) is good for once merged.
lang: en
date: 2026-07-31
pair: choosing-a-cjk-coding-font
---

Writing Chinese comments in a terminal and reading Chinese docs in an editor, most people hit the same wall: they pick a beautiful CJK face, and then tables drift, the cursor lands in the wrong column, and prompt icons eat a character. The problem is almost never the glyphs. It is the **grid**.

## 1. Confirm the 2:1

For a mixed CJK/Latin monospace font, one thing cannot be negotiated: one CJK character must be exactly twice the width of one Latin character. Miss that, and every `|`-drawn table, every aligned comment and every `tree` output goes crooked.

Testing it is easy — type these two lines in your terminal and see whether the bars line up:

```
|--------|--------|
|中文占位|abcdefgh|
```

If they do not, either the CJK is not exactly double width, or your terminal is recomputing widths by its own rules.

Across the eight AKR fonts, every coding face is built to a strict 2:1 and re-gated on each build (`verify2to1`). The reading face, AKR Hand SC Text, *deliberately* drops the monospace declaration — it is not meant for a terminal.

## 2. Then check symbol widths

Subtler than the 2:1 is East_Asian_Width. Characters like `…`, `—` and `≠` are marked Ambiguous or Wide in Unicode, and terminals disagree about how much room to give them. If the font does not explicitly make those glyphs half- or full-width, the cursor position stops matching the rendered width — which you experience as "I deleted one character and the cursor moved by two".

You cannot eyeball this one. You have to know whether the font handled EAW at all.

## 3. Icons come last

Nerd Font patching has two modes: `--complete` produces double-width icons, while `--single-width-glyphs` (the NFM, Nerd Font Mono, build) squeezes them into one cell. Double-width icons in a shell prompt will push the following text out by a column.

**For terminal use, take the Mono / NFM build.**

## 4. Which upstream, and what it becomes

Here is how several common open Chinese faces behave once merged into a coding font:

| Upstream | Character | Good for |
| --- | --- | --- |
| [LXGW WenKai](/en/upstream/lxgw-wenkai) | Kai, handwritten stroke ends | Pleasant for comments and docs; a little light for all-day code |
| [LXGW NeoZhiSong](/en/upstream/lxgw-neozhisong) | Song, high stroke contrast | Highly distinguishable glyphs, good for long sessions |
| [IBM Plex Sans SC](/en/upstream/ibm-plex-sans-sc) | Neutral sans | The least opinionated; the default when a team standardises |
| [Resource Han Rounded](/en/upstream/resource-han-rounded) | Rounded | The friendliest in screenshots and demos |
| [Zhuque Fangsong](/en/upstream/zhuque-fangsong) | Fangsong, thin slanted strokes | Typewriter texture; be careful at small sizes |
| [Fusion Pixel](/en/upstream/fusion-pixel) | 12px bitmap | Retro terminals — use integer multiples of 12 |
| [Yozai](/en/upstream/yozai) | Soft and casual | Between a gothic and handwriting |

The Latin side has just as much character: Iosevka is narrow, Lilex neutral with ligatures, Monaspace Radon leans like handwriting, Courier Prime is a typewriter. **Both halves should lean the same way** — otherwise two personalities fight inside one line. That is exactly why AKR Hand shears its CJK by 7.5° to match Radon.

## 5. Try it yourself

None of the above beats pasting your own code in and looking at it. The [preview](/en/preview) carries all eight; size, line height and ligatures are adjustable, and the link is shareable.

Every font ships under SIL OFL 1.1 and is free for commercial use — [license and credits](/en/license).
