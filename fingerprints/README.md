# Fingerprint baselines

One directory per family, holding the normalised regression baseline for that
family's build products. Written by `just fingerprint <family>`, checked by
`just verify <family>`. See [`../docs/build-toolchain.md`](../docs/build-toolchain.md).

## ⚠️ Retired by the AKR rename (KIT-282) — currently empty

The 22 baselines here were adopted from run
[30357631683](https://github.com/AkaraChen/font/actions/runs/30357631683), the
`x86_64-linux` build of the font-patcher 4.26.0 pin. Phase 7 renamed every
family (`LilexSansSC NFM` → `AKR Sans SC NFM`, and six more), which moves the
name table, which is *in* the fingerprint. So all 22 went stale at once, and
none of them describes a product this repo still builds.

**This is the sanctioned direction of the rule below, not an exception to it.**
The rule is: never re-adopt a baseline to make a red gate green when the product
changed unexpectedly. Here the product changed *by design* — the whole phase is
a deliberate, maintainer-approved breaking rename — and the baselines are being
re-taken from a green CI run, on the canonical platform, exactly as bootstrapping
prescribes.

Three things also changed shape, so the new set is not a renamed copy of the old:

* **sans and pixel gained the region axis.** Four regions each instead of one,
  so 22 products becomes 40.
* **Phase 6's products were never baselined at all.** handwriting's three `text`
  faces and its Light have had no entry since KIT-281; they are adopted with the
  rest rather than left as a standing `NEW`.
* **The intermediates were renamed too.** serif's `SarasaMonoSlabNeoZhiSongSC-Opt`
  is `AKRSlabSCDual` now — it ships in `serif/out/` and carried three upstream
  reserved names in one file stem.

Until they are re-adopted, `just verify <family>` and the CI fingerprint step
report every product as `NEW` and exit **3** — a warning with an artifact, not a
pass. Follow [Bootstrapping](#bootstrapping) below, once per family, from a green
run of the PR that renamed them.

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
