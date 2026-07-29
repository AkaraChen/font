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

### Pending re-adoption (KIT-297)

**The committed set above is stale and CI will say so.** KIT-297 changed the
product and the dump on purpose, in two places:

* `fontkit.embolden` now sorts contours, so every product of `sans`,
  `typewriter`, `casual` and `handwriting` Bold has its outlines written in a
  different order (the same outlines — see [source B](#source-b--skia-pathops-contour-order-fixed))
* `fingerprint.py`'s `script` lines now name each feature by tag *and* lookup
  signature rather than tag alone

Same situation as the Phase 7 rename, and the same remedy: re-adopt all 43 from
a green `x86_64-linux` run, per [Bootstrapping](#bootstrapping). Do **not**
take them from a laptop.

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
That was the open question for a long time; KIT-297 answered it, and the answer
is [below](#what-differs-across-platforms-and-why).

The rule survives the answer: `x86_64-linux` is what ships releases,
`PROVENANCE` records what produced a baseline, and the one residual difference
— FontForge redrawing the icons it imports — is enough to make a
darwin-authored baseline turn CI red.

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

## What differs across platforms, and why

Answered by KIT-297. The method is worth stating because it is cheap and
repeatable: rather than building seven families twice, run each *step* on both
platforms over byte-identical inputs and compare the outlines. The pinned
toolchain makes this possible off a laptop — `x86_64-linux` in a container with
the same `flake.lock`, `aarch64-darwin` in `nix develop`.

`just toolchain-fingerprint` prints the table both sides have to agree on; CI
prints the same one in every build job's *Toolchain fingerprint* step.

### What it is not

Three plausible explanations were measured and are all **wrong**:

* **Not two implementations.** nixpkgs builds fontTools 4.60.1 with no Cython
  on either platform — no `cython` in `nativeBuildInputs`, no
  `FONTTOOLS_WITH_CYTHON`, and the two derivations differ only in `stdenv`.
  Both sides run pure-Python `cu2qu`. (A PyPI wheel *does* ship the compiled
  twin, which is why the probe reports it: an accidental `pip install` would be
  a real difference.)
* **Not the shear.** `fontkit.prepare_cjk` is pure Python around one
  `math.tan`, and `tan(radians(7.5))` is bit-identical on both platforms
  — `3fc0d9fd31c98bf8` — as are `sin`, `cos`, `sqrt`, `atan`, `log` and `exp`.
  A 179k-point synthetic shear digests the same on both.
* **Not cu2qu, nearly.** `handwriting`'s text donor converts bit-identically:
  743k points over 12690 glyphs, same digest. See the residual below for the
  one place it does not.

### Source A — FontForge, in the Nerd patch (unfixable here)

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

This lives inside FontForge's compiled outline code and is not fixable from
this repo. It is the reason the rule at the top of this file stands.

**FeatureRecord order** — the other half of what a Nerd diff used to show — was
not FontForge being non-deterministic in a way that mattered. A font carries one
`locl` per script, `fingerprint.py` sorted `FeatureRecord`s by tag alone, and a
tag is not a unique key: ties fell back to the record's position in the
`FeatureList`, which FontForge is free to permute (and does, remapping every
`LangSys` `FeatureIndex` to match). The dump now sorts on the tag *and* the
feature's lookup signature, and each `script` line names which instance its
`LangSys` selected instead of just the tag — strictly more sensitive than
before, and no longer sensitive to a permutation that changes nothing.

### Source B — skia-pathops contour order (fixed)

`OpBuilder.resolve` does not promise an emission order for the contours it
produces, and does not deliver one: on `LXGWWenKai-Medium` at strength 5, one
glyph in 3265 came back permuted — `uni2FF3`, 30 contours, numbers 12 and 13
swapped, **every coordinate equal as a set**. Not floating point at all.

Contour order carries no meaning in `glyf` — TrueType fills by the non-zero
winding rule — so `fontkit.embolden.path_to_glyph` now sorts contours before
drawing them, never reaching inside one (that would rotate the start point and
reverse the winding). With the sort, the emboldened output of the same input is
byte-identical on both platforms.

This is why `sans`, `typewriter`, `casual` and `handwriting` Bold drifted at the
`Dual` stage and `rounded` did not: `rounded` pins `embolden = 0`, so its CJK
master is copied and never enters skia-pathops at all.

### The residual — one ULP of `hypot`, in cu2qu

`handwriting`'s *coding* donor (`MonaspaceRadonNF-Regular.otf`, icons included)
does not convert identically: **3 glyphs in 12690**, two coordinates one font
unit apart, and one glyph split into 67 quadratics instead of 66.

cu2qu decides whether to split by comparing `abs(complex)` against a tolerance,
and `abs()` on a complex is CPython's `_Py_c_abs`, i.e. the platform `hypot`.
Neither IEEE-754 nor C requires `hypot` to be correctly rounded, and the two
implementations take that freedom differently — over the same 50000 pairs,
glibc 2.41 is off by one ULP on **0.61%** and macOS/arm64 on **15.71%**. A
curve whose error sits within one ULP of the tolerance splits on one platform
and not the other.

Nothing in this repo can fix that without vendoring cu2qu. It is bounded, it is
one point in 743157, and it is the only genuinely floating-point difference
found.

### So what does a maintainer on a Mac see

`just verify <family>` still fails for the five families that get a Nerd patch,
on `digest` and sometimes `maxPoints` — source A, expected, explained.
`tools/fingerprint.py check` now says so in one line when it is not running on
`x86_64-linux` and everything that moved is a field this section accounts for.
It still exits 1, and the baseline still belongs to CI: the note is there so
that "CHANGED digest" reads as *this is the known FontForge difference* rather
than *you broke something*.

What changed is that a Mac build is now correct everywhere the repo's own code
runs. `Dual` intermediates for every family, including the four that embolden,
are byte-identical across platforms.
