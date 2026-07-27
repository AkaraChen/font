#!/usr/bin/env python3
"""Verify FusionPixel12 product: 2:1 advances, calt ligatures, optional Nerd PUA."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

# Sample Nerd / Powerline codepoints (private use)
NERD_SAMPLES = (
    0xE0A0,  # version control branch (Powerline)
    0xE0B0,  # powerline left arrow
    0xE0B2,  # powerline right arrow
    0xF013,  # gear (Font Awesome in many Nerd sets)
    0xF120,  # terminal
)

# Sequences we expect to ligate under calt (subset of what we inject)
LIGA_SAMPLES = ("==", "!=", "===", "=>", "->", "<=", ">=", "++", "--", ":=", "&&", "||")


def check_advances(font: TTFont, half: int, full: int) -> list[str]:
    errs: list[str] = []
    cmap = font.getBestCmap() or {}
    samples = {
        "A": half,
        "i": half,
        "=": half,
        "中": full,
        "　": full,  # ideographic space if present
    }
    hmtx = font["hmtx"]
    for ch, expect in samples.items():
        name = cmap.get(ord(ch))
        if not name:
            if ch in ("中", "　"):
                continue
            errs.append(f"missing cmap for {ch!r}")
            continue
        adv = hmtx[name][0]
        if adv != expect:
            errs.append(f"advance({ch!r})={adv} expected {expect}")
    return errs


def check_fixed_pitch(font: TTFont) -> list[str]:
    errs: list[str] = []
    if font["post"].isFixedPitch != 1:
        errs.append(f"post.isFixedPitch={font['post'].isFixedPitch} expected 1")
    return errs


def check_ligatures(font: TTFont) -> list[str]:
    errs: list[str] = []
    if "GSUB" not in font:
        return ["no GSUB table"]
    gsub = font["GSUB"].table
    tags = [fr.FeatureTag for fr in gsub.FeatureList.FeatureRecord]
    if "calt" not in tags:
        errs.append(f"no calt feature (have {tags})")
        return errs

    # Collect type-4 ligature products
    liga_glyphs: set[str] = set()
    n_rules = 0
    for lookup in gsub.LookupList.Lookup:
        subs = []
        for st in lookup.SubTable:
            if lookup.LookupType == 7 and hasattr(st, "ExtSubTable"):
                st = st.ExtSubTable
            if hasattr(st, "ligatures"):
                subs.append(st)
        for st in subs:
            for first, ligset in st.ligatures.items():
                for lig in ligset:
                    n_rules += 1
                    liga_glyphs.add(lig.LigGlyph)

    if n_rules < 10:
        errs.append(f"too few ligature rules: {n_rules}")
    # Ensure sample sequences have a matching liga_ glyph installed
    cmap = font.getBestCmap() or {}
    hmtx = font["hmtx"]
    glyf = font["glyf"]
    for seq in LIGA_SAMPLES:
        expected = "liga_" + "_".join(f"u{ord(c):04X}" for c in seq)
        if expected not in hmtx.metrics:
            # not fatal for every sample if donor lacked it — warn
            errs.append(f"missing liga glyph for {seq!r} ({expected})")
            continue
        g = glyf.get(expected)
        if g is None or getattr(g, "numberOfContours", 0) == 0:
            errs.append(f"empty outline for {seq!r}")
        # advance should be n * half
        half = hmtx[cmap[ord("A")]][0]
        adv = hmtx[expected][0]
        if adv != half * len(seq):
            errs.append(f"liga advance({seq!r})={adv} expected {half * len(seq)}")
    if not errs:
        print(f"  calt ok: {n_rules} ligature rules, samples present")
    return errs


def check_nerd(font: TTFont, half: int) -> list[str]:
    errs: list[str] = []
    cmap = font.getBestCmap() or {}
    hmtx = font["hmtx"]
    found = 0
    for cp in NERD_SAMPLES:
        name = cmap.get(cp)
        if not name:
            continue
        found += 1
        adv = hmtx[name][0]
        if adv != half:
            errs.append(f"Nerd U+{cp:04X} advance={adv} expected half={half}")
    if found == 0:
        errs.append("no sample Nerd/PUA codepoints found (patch missing?)")
    else:
        print(f"  nerd ok: {found}/{len(NERD_SAMPLES)} sample PUA present @ half={half}")
    return errs


def verify_one(
    path: Path,
    *,
    half: int,
    full: int,
    check_nerd_flag: bool,
    check_liga_flag: bool,
) -> int:
    print(f"verify {path}")
    font = TTFont(path)
    try:
        errs: list[str] = []
        # auto-detect half if 0
        h = half
        if h <= 0:
            cmap = font.getBestCmap() or {}
            h = font["hmtx"][cmap[ord("A")]][0]
        f = full if full > 0 else h * 2
        errs += check_advances(font, h, f)
        errs += check_fixed_pitch(font)
        if check_liga_flag:
            errs += check_ligatures(font)
        if check_nerd_flag:
            errs += check_nerd(font, h)
        if errs:
            for e in errs:
                print(f"  FAIL: {e}")
            return 1
        print(f"  ok half={h} full={f}")
        return 0
    finally:
        font.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument("--half", type=int, default=600)
    ap.add_argument("--full", type=int, default=1200)
    ap.add_argument("--check-nerd", action="store_true")
    ap.add_argument("--check-ligatures", action="store_true")
    args = ap.parse_args()
    rc = 0
    for path in args.fonts:
        rc |= verify_one(
            path,
            half=args.half,
            full=args.full,
            check_nerd_flag=args.check_nerd,
            check_liga_flag=args.check_ligatures,
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
