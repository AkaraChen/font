# Fingerprint baselines

One directory per family, holding the normalised regression baseline for that
family's build products. Written by `just fingerprint <family>`, checked by
`just verify <family>`. See [`../docs/build-toolchain.md`](../docs/build-toolchain.md).

**Adopted from run
[30357631683](https://github.com/AkaraChen/font/actions/runs/30357631683)**, the
`x86_64-linux` build of the font-patcher 4.26.0 pin — seven families green, 22
products. Every family is gated for real from here: drift fails the build
instead of printing a warning.

## Baselines belong to CI, not to a laptop

This used to be justified by a finding that has since been retired. Phase 0
observed that all seven products differed between `x86_64-linux` and
`aarch64-darwin` and concluded the build was not reproducible across platforms,
citing `pixel`: 46661 glyphs on Linux against darwin's 46552.

**That was measuring two patchers, not two platforms.** `NERD_PATCH_METHOD=auto`
picked the `nerdfonts/patcher` container whenever docker was installed — always,
on GitHub runners — while the same image is broken on `arm64` and fell back to
the pinned local patcher on the maintainer's Mac. KIT-277 deleted the fork and
the follow-up pinned the commit the container was built from; `pixel` on darwin
now produces 46661 glyphs, with `glyphorder`, `cmap` and every advance matching
the Linux product.

What genuinely differs across platforms, measured on the same pin, is much
smaller: `maxp.maxPoints` by two, and the outline digest that follows from it.
Real, unexplained, and the current open question.

The rule survives anyway, for a plainer reason: `x86_64-linux` is what ships
releases, `PROVENANCE` records what produced a baseline, and one unexplained
outline delta is enough to make a darwin-authored baseline turn CI red.

## Bootstrapping

`x86_64-linux` on GitHub Actions is the canonical platform. When a family has no
baseline, the workflow warns instead of failing, and uploads what that run
produced as the `fingerprints-<family>` artifact. To land them:

```bash
gh run download <run-id> -n fingerprints-<family> -D fingerprints/<family>
git add fingerprints/<family> && git commit -m "chore: adopt <family> fingerprint baseline from CI"
```

After that the family is gated for real: any later drift fails the build.

### A family that gains a new product

Same situation, one product at a time. Phase 6 (KIT-281) gave handwriting three
`text` products next to its two `coding` ones; those three have nothing to be
compared against, and adopting a darwin-authored baseline for them is exactly
what the section above says not to do.

So `check` reports a product with no baseline entry as `NEW` and exits **3**,
the same "adopt one from CI" code an empty directory produces. It cannot mask a
regression, which is the only thing that would make this a loophole:

| | verdict |
| --- | --- |
| a baselined product changed | `CHANGED`, exit **1** |
| a baselined product disappeared | `MISSING`, exit **1** |
| a product with no baseline | `NEW`, exit **3** |

Phase 6's own completion criterion — *"coding 版指纹不变"* — is checked by the
first row, not weakened by the third.

## Open question

Which platform is *correct* is not settled. Linux produces the more complete
Nerd glyph set for `pixel`, which suggests darwin's patch is the deficient one —
but that is an inference, not a diagnosis, and it means the fonts a maintainer
builds locally on a Mac are not the fonts that get released. Worth its own
issue; it is a pre-existing property of the repo that Phase 0 surfaced rather
than introduced.
