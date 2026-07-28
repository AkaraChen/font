# Fingerprint baselines

One directory per family, holding the normalised regression baseline for that
family's build products. Written by `just fingerprint <family>`, checked by
`just verify <family>`. See [`../docs/build-toolchain.md`](../docs/build-toolchain.md).

**Empty on purpose right now.** The first CI run bootstraps them — see below.

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

## Bootstrapping

`x86_64-linux` on GitHub Actions is the canonical platform. When a family has no
baseline, the workflow warns instead of failing, and uploads what that run
produced as the `fingerprints-<family>` artifact. To land them:

```bash
gh run download <run-id> -n fingerprints-<family> -D fingerprints/<family>
git add fingerprints/<family> && git commit -m "chore: adopt <family> fingerprint baseline from CI"
```

After that the family is gated for real: any later drift fails the build.

## Open question

Which platform is *correct* is not settled. Linux produces the more complete
Nerd glyph set for `pixel`, which suggests darwin's patch is the deficient one —
but that is an inference, not a diagnosis, and it means the fonts a maintainer
builds locally on a Mac are not the fonts that get released. Worth its own
issue; it is a pre-existing property of the repo that Phase 0 surfaced rather
than introduced.
