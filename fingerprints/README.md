# Fingerprint baselines

One directory per family, holding the normalised regression baseline for that
family's build products. Written by `just fingerprint <family>`, checked by
`just verify <family>`. See [`../docs/build-toolchain.md`](../docs/build-toolchain.md).

## Current baselines — AKR rename (KIT-282)

Re-adopted from run
[30420407248](https://github.com/AkaraChen/font/actions/runs/30420407248)
(`x86_64-linux`, PR #41). **43** product fingerprints across seven families.

The previous 22 baselines (from
[30357631683](https://github.com/AkaraChen/font/actions/runs/30357631683)) went
stale at once: Phase 7 renamed every family (`LilexSansSC NFM` → `AKR Sans SC
NFM`, and six more), which moves the name table, which is *in* the fingerprint.

**This was the sanctioned direction of the rule below, not an exception to it.**
The product changed *by design* — a deliberate, maintainer-approved breaking
rename — so the baselines were re-taken from a green CI run on the canonical
platform, exactly as bootstrapping prescribes. The new set is not a renamed copy
of the old:

* **sans and pixel gained the region axis** (four regions each instead of one)
* **Phase 6's products were never baselined** (handwriting's three `text` faces
  and Light) — adopted with the rest
* **Intermediates were renamed** (`SarasaMonoSlabNeoZhiSongSC-Opt` →
  `AKRSlabSCDual`)

## Fonts are built on Linux

Decided in KIT-297, after the question below was answered. `x86_64-linux` builds
and ships the fonts; `aarch64-linux` is allowed; darwin is not a build platform.

This is enforced rather than documented: `flake.nix` does not offer the family
attributes off Linux, `just build` (and `step` / `gate` / `release` /
`fingerprint` / `verify`) refuses with the reason, and
`tools/fingerprint.py write` will not author a baseline into
`fingerprints/<family>/` off Linux.

A Mac is still a first-class machine to *work* on. `nix develop`, `just test`,
`just dump`, `just fmt`, `just toolchain-fingerprint` and everything under
`tools/` are unchanged — none of them produce a shipped byte.

The point is not that a darwin build fails. It is that it **succeeds, and
produces a different font** — see below — so the only thing it can buy is three
hours and a `just verify` failure that is nobody's bug.

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
That was unexplained for a long time; [it is not any
more](#what-differed-across-platforms-and-why), and the answer is why darwin is
no longer a build platform at all.

The rule stands on its own regardless: `x86_64-linux` is what ships releases,
and `PROVENANCE` records what produced a baseline.

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

### A family that gains a new *format* (Phase 8, KIT-283)

Same mechanism, and worth spelling out because the three formats are not
equivalent:

| format | baseline | why |
| --- | --- | --- |
| `.ttf` | yes | the product |
| `.otf` | **its own**, separate from the TTF's | CFF charstrings are a different curve representation; qu2cu refits every outline within a tolerance. Diffing it against the TTF baseline would go red for being correct |
| `.woff2` | none | byte-identical `glyf` to its TTF by construction, and `fontkit verify-formats` gates exactly that. A baseline would be a second copy of the TTF's |

`tools/fingerprint.py` already reads CFF (`_dump_outlines` branches on `glyf` vs
`CFF `) and already walks `.otf`, so handwriting's three text OTFs appear as
`NEW` on the first run that builds them and are adopted from CI like any other
new product — which, since KIT-297, is the only way they can be adopted at all.

## What differed across platforms, and why

Answered by KIT-297. The method is worth stating because it is cheap and
repeatable: rather than building seven families twice, run each *step* on both
platforms over byte-identical inputs and compare the outlines. The pinned
toolchain makes that possible off a laptop — `x86_64-linux` in a container on
the same `flake.lock`, `aarch64-darwin` in `nix develop`.

`just toolchain-fingerprint` prints the table both sides have to agree on; CI
prints the same one in the toolchain job and in every family job.

### It is all FontForge, and only the icons

Running `fontkit.nerd_patch` on both platforms over the same input:
**272 of 13797 glyphs differ, and not one of them is a glyph of the base
font.** Every one is an icon that `font-patcher` imported and rescaled.

| how they differ | glyphs |
| --- | ---: |
| different point count (simplify / overlap removal took another branch) | 156 |
| same points, ≤ 2 font units apart (rounding) | 109 |
| larger | 7 |

That is the whole of the `maxp.maxPoints` mystery: `maxp` records the largest
glyph, the largest glyph is an imported icon, and 156 icons came out with a
different number of points. The base font passes through the patcher untouched,
which is exactly why `rounded`'s pre-patch `Dual` was always identical across
platforms while its Nerd product was not.

This lives inside FontForge's compiled outline code. It is not a bug we can fix
and not a bug anyone upstream is likely to call a bug — it is what happens when
the same C rounds on two architectures. Hence the decision above: don't build
there.

### What it is not

Four plausible explanations were measured and are all **wrong**. Recorded
because each one is the obvious next guess, and re-deriving them costs a day:

* **Not two implementations of cu2qu.** nixpkgs builds fontTools 4.60.1 with no
  Cython on either platform — no `cython` in `nativeBuildInputs`, no
  `FONTTOOLS_WITH_CYTHON`, and the two derivations differ only in `stdenv`.
  Both sides run pure Python. (A PyPI wheel *does* ship the compiled twin,
  which is why `toolchain-fingerprint` reports it: a stray `pip install` would
  be a real difference.)
* **Not the CJK shear.** `fontkit.prepare_cjk` is pure Python around one
  `math.tan`, and `tan(radians(7.5))` is bit-identical on both platforms —
  `3fc0d9fd31c98bf8` — as are `sin`, `cos`, `sqrt`, `atan`, `log` and `exp`. A
  179k-point synthetic shear digests the same on both.
* **Not skia-pathops arithmetic.** The emboldened output of the same master
  differs in exactly one glyph in 3265, and there the two sides hold the *same
  30 contours with the same coordinates* — `uni2FF3`, numbers 12 and 13 swapped.
  `OpBuilder.resolve` promises no emission order. Contour order carries no
  meaning in `glyf` (non-zero winding), so this changes no rendered shape; it
  would only ever have mattered for comparing a darwin build against a Linux
  one, which is no longer a thing that happens.
* **Not FeatureRecord order.** A Nerd diff used to show two `feature locl`
  lines swapping. That was this tool, not the font: a font carries one `locl`
  per script, `_dump_layout` sorts FeatureRecords by tag, and a tag is not a
  unique key — ties fell through to FeatureList position, which FontForge
  permutes while remapping every `LangSys` `FeatureIndex` to match. Same
  situation: visible only when diffing two platforms.

### The residual, for the record

`handwriting`'s *coding* Latin donor does not convert identically through
cu2qu: 3 glyphs in 12690, two coordinates one font unit apart, one glyph split
into 67 quadratics instead of 66. cu2qu decides whether to split by comparing
`abs(complex)` against a tolerance, and `abs()` on a complex is CPython's
`_Py_c_abs`, i.e. the platform `hypot` — which neither IEEE-754 nor C requires
to be correctly rounded. Over the same 50000 pairs, glibc 2.41 is off by one
ULP on **0.61%** and macOS/arm64 on **15.71%**.

The *text* donor converts bit-identically (743157 points, 12690 glyphs), so
this is a rare boundary case rather than a systematic difference. Bounded at
one point in 743157, and the only genuinely floating-point difference found.
