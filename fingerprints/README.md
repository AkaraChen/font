# Fingerprint baselines

One directory per family, holding the normalised regression baseline for that
family's build products. Written by `just fingerprint <family>`, checked by
`just verify <family>`. See [`../docs/build-toolchain.md`](../docs/build-toolchain.md).

**Adopted from run
[30343032975](https://github.com/AkaraChen/font/actions/runs/30343032975)**, the
`x86_64-linux` build of `3ed3ee4` — seven families green, 22 products. Every
family is gated for real from here: any later drift fails the build instead of
printing a warning.

## Baselines belong to CI, not to a laptop

The build is **not** architecture-independent. The first CI run of this workflow
proved it: all seven families built cleanly on `x86_64-linux`, and all seven
products differed from baselines generated on `aarch64-darwin`.

The one family that was diagnosed in detail, `pixel`, localises it:

| product | how it is built | darwin vs linux |
| --- | --- | --- |
| `FusionPixel12Mono-Regular.ttf` | fontTools only | **identical** |
| `nerd/FusionPixel12NFM-Regular.ttf` | + `fontforge -script font-patcher` | **46552 vs 46661 glyphs** |

Same pinned fontforge, same pinned `FontPatcher.zip`, same arguments, same input
font — and Linux emits 109 more glyphs, with different `head.flags`,
`lowestRecPPEM` and `maxp.maxPoints`. So the toolchain pin makes the build
reproducible *on a platform*, not *across* platforms.

`casual` and `handwriting` have no fontforge patch step at all and still
differed, so fontforge is not the only source — `skia-pathops` (a compiled Skia)
is the obvious suspect for the CJK embolden step, but that has **not** been
confirmed, only inferred from which families failed.

Committing a laptop's baselines would therefore make CI permanently red, and a
permanently red gate is worse than no gate.

This also sets what a local build can and cannot prove. Building a family both
ways on one machine and diffing the two fingerprints is valid evidence that a
refactor moved nothing — the platform difference is on both sides and cancels.
Comparing a local build against *this* directory is not.

## Adopting a new baseline

`x86_64-linux` on GitHub Actions is the canonical platform, and
`PROVENANCE` records which one a baseline came from — it is checked by eye, not
by the tooling, so a laptop-authored baseline is caught in review rather than by
a red build three PRs later.

When a family has no baseline the workflow warns instead of failing, and always
uploads what the run produced as the `fingerprints-<family>` artifact — whatever
the verdict. So a **drift** is diagnosed from the same artifact a bootstrap is
adopted from:

```bash
gh run download <run-id> -n fingerprints-<family> -D /tmp/fp-new
diff -ru fingerprints/<family> /tmp/fp-new
```

Adopting one is the same command pointed at the tracked directory:

```bash
gh run download <run-id> -n fingerprints-<family> -D fingerprints/<family>
git add fingerprints/<family>
```

**Do this only when the change is intended and understood.** Re-adopting a
baseline to turn a gate green is the one move that makes the gate worthless —
and worse than worthless when two changes are in flight, because it silently
attributes one change's regression to the other. Diff the two sides and say in
the commit message which glyphs or tables moved and why.

`just fingerprint <family>` writes a baseline from a local build. That is for
inspecting the format, not for landing: on darwin it produces a baseline that
makes CI permanently red, for the reasons above.

## Open question

Which platform is *correct* is not settled. Linux produces the more complete
Nerd glyph set for `pixel`, which suggests darwin's patch is the deficient one —
but that is an inference, not a diagnosis, and it means the fonts a maintainer
builds locally on a Mac are not the fonts that get released. Worth its own
issue; it is a pre-existing property of the repo that Phase 0 surfaced rather
than introduced.
