# Fingerprint baselines

One directory per family, holding the normalised regression baseline for that
family's build products. Written by `just fingerprint <family>`, checked by
`just verify <family>`. See [`../docs/build-toolchain.md`](../docs/build-toolchain.md).

> ⚠️ **Do not merge this branch as it stands.** These baselines were produced by
> the **docker** Nerd Fonts patcher, not by the pinned `FontPatcher.zip` — see
> [Which patcher built these](#which-patcher-built-these). Adopting them would
> make the gate demand output the repo cannot reproduce from its own pins.

**Adopted from run
[30343032975](https://github.com/AkaraChen/font/actions/runs/30343032975)**, the
`x86_64-linux` build of `3ed3ee4` — seven families green, 22 products.

## Which patcher built these

Phase 0 read the darwin/linux product difference as a **platform** difference,
and wrote that down here:

> Same pinned fontforge, same pinned `FontPatcher.zip`, same arguments, same
> input font — and Linux emits 109 more glyphs […] So the toolchain pin makes
> the build reproducible *on a platform*, not *across* platforms.

**That diagnosis is wrong.** It was not the platform. It was two different
patchers, chosen at runtime by what happened to be installed:

| | patcher actually used | `pixel` nerd glyphs |
| --- | --- | --- |
| CI, `x86_64-linux` | **docker** `nerdfonts/patcher@sha256:4e820b…` | 46661 |
| laptop, `aarch64-darwin` | pinned `FontPatcher.zip` v3.4.0 + nixpkgs fontforge | 46552 |

`NERD_PATCH_METHOD=auto` in `pins.env` picked docker whenever docker was
installed. GitHub's runners have docker, so **every CI-built product in this
repo's history came out of that container** — and the container's tag was
explicitly documented as floating. The maintainer's Mac has docker too, but the
image is broken on `arm64` (`/bin/sh: fontforge: not found`), so it silently
fell back to the pinned local patcher. Two platforms, two patchers, one
conclusion drawn about platforms.

Evidence, from the run these baselines come from
([pixel job log](https://github.com/AkaraChen/font/actions/runs/30343032975)):

```
==> pulling/using docker image nerdfonts/patcher@sha256:4e820b…
==> docker patch → /home/runner/work/font/font/pixel/out/nerd
```

with no fallback line after it. Building the same commit's products with docker
removed changes every Nerd family and nothing else — `casual` and `handwriting`
have no patch step and are byte-identical, as are all the pre-patch `Dual`
intermediates.

## Baselines still belong to CI, not to a laptop

The conclusion survives its broken premise, for a smaller reason: the build is
pinned per platform, not across them, and `PROVENANCE` records which one a
baseline came from. Whether anything *besides* the patcher choice differs across
platforms is now an open question rather than a settled fact — the evidence that
looked like proof was measuring the patcher fork.

Committing a laptop's baselines would still be wrong: `x86_64-linux` is what
ships releases.

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

**Which patcher is correct**, now that the choice is no longer accidental. The
container emitted more icons than the pinned `FontPatcher.zip` v3.4.0 — 109 more
for `pixel` and `serif`, 365 more for `rounded`, `sans` and `typewriter`. So
dropping docker (KIT-277) makes the build match its own pin, and costs icons the
released fonts used to carry.

Two ways to close it, and it is a product decision, not a build one:

1. **Accept the pin.** Fewer icons, and the products become reproducible from
   what the repo declares.
2. **Bump `NERD_FONTS_TAG`** to the version the container was shipping, which
   recovers the icons *and* keeps reproducibility. Deliberate pin change, moves
   fingerprints again, and needs someone to establish which version that was —
   the image digest is pinned but its patcher version was never recorded.

Until it is decided, the baselines to adopt are whichever run reflects the
decision. These do not: they are the container's output.
