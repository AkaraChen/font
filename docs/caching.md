# Caching

Two decisions govern every build in this repo, and they are unrelated to each
other:

1. **What a derivation is allowed to see** — decides what gets *reused*.
2. **What CI keeps between runs** — decides what gets *re-downloaded and rebuilt*.

The first is `nix/granularity.nix`. The second is the layered GitHub Actions
cache in `.github/workflows/build-matrix.yml`. This document covers both, with
the numbers they were sized against.

**There is no binary cache.** Neither cachix nor attic. That was decided rather
than deferred: the repo's inputs are big and its products are few, the store is
already reproducible from pins, and a hosted cache adds an account, a secret and
a bill for a benefit the GHA cache covers. If that changes, this file is where
the decision gets rewritten.

---

## 1. Derivation granularity

Nix caches per derivation. A derivation rebuilds when any of its inputs change,
so **the parameters a step takes are its cache key** — there is no other lever.

The whole point of splitting one build into named steps is that some of them do
not vary along every axis:

| step | family | profile | region | weight | format |
| --- | :-: | :-: | :-: | :-: | :-: |
| `src-latin` | ● | | | ● | |
| `src-cjk` | ● | | ● | ● | |
| `latin-prepared` | ● | ● | | ● | |
| `cjk-prepared` | ● | | ● | ● | |
| `merged` | ● | ● | ● | ● | |
| `nerd` | ● | | ● | ● | |
| `packaged` | ● | ● | ● | ● | ● |

Two blanks in that table are the reason the phase exists:

* **`latin-prepared` has no region.** Scaling, narrowing and grid work on the
  Latin face depend on the product grid — a profile property. A Simplified build
  and a Japanese build want byte-identical Latin. With the region axis added in
  Phase 7 that is one Latin preparation instead of five.
* **`cjk-prepared` has no profile.** Optical stroke matching is about ink weight.
  It does not change because the font will be used for prose instead of code, so
  the coding and text profiles share it.

`nerd` has no profile axis either, for a different reason: Nerd patching only
exists in the coding profile. A text-profile `nerd` derivation is a bug, not a
cache miss.

### The contract is enforced, not documented

A comment saying "don't pass region here" rots. `nix/granularity.nix` rejects it:

```
$ nix eval --expr '(import ./nix/granularity.nix { inherit lib; }).mkName
    "latin-prepared" { family = "sans"; profile = "coding"; region = "tc";
                       weight = "Bold"; }'
error: granularity: latin-prepared may not depend on region — widening its cache
key would rebuild it once per region. Declared axes: family, profile, weight.
```

Note that it *errors* rather than dropping the extra argument. Silently ignoring
`region` would produce the right cache key by accident while the caller went on
believing it had built a per-region Latin.

`nix flake check` covers this — see `nix/checks.nix`. All of those checks are
pure evaluation, so they run offline in about a second.

Phase 3 (KIT-277) builds the real derivations on top of `mkStep`. Phase 1 fixes
the shape so Phase 3 cannot quietly widen a key.

Inspect it any time with `just graph`.

---

## 2. Sources

Everything pinned in a `font.toml` is now a Nix derivation (`nix/sources/`).
Nix reads those same files — it does not carry a second copy of any URL or hash
(`nix/lib/pins.nix`).

A store path is keyed by `(url, hash)`, which is what makes the headline case
work: **five families pin the same font-patcher commit, so there is one
derivation and one fetch**, where before there were five, one per
`<family>/work/downloads/`. `nix/checks.nix` asserts it, and
`nix/sources/default.nix` fails evaluation if a family drifts its patcher pin.

Two inputs are not plain `fetchurl`:

* **Monaspace** (handwriting) ships its Nerd Font builds only inside a 315 MiB
  zip holding two ~2.3 MiB OTFs. `fetch_zip_member.py` already pulled just those
  members with HTTP range requests; standard Nix fetchers cannot do partial
  downloads, so it runs inside a fixed-output derivation, which has network
  access in the sandbox. Without a binary cache this matters *more*, not less —
  it is 315 MiB saved on every cold run. The FOD's output hash is the member
  sha256 that was already in `font.toml`, so nothing new has to be kept in sync.
* **Sarasa Gothic** (serif) was a `git clone --depth 1`; it is now
  `fetchFromGitHub` at `SARASA_COMMIT`, hash-pinned by `SARASA_SRC_HASH`. The
  clone verified the commit id, which pins history but not the bytes delivered
  for it.

Three artifacts had **no integrity check at all** before this phase and now do:
`FontPatcher.zip` (five families), `LXGWNeoZhiSongPlus.ttf` and the Sarasa Term
donor archive (serif). The patcher is a commit-pinned sparse checkout now rather
than a release zip — sparse because the nerd-fonts repo is 27 GB.

### How the build steps consume it

Directly. Each family's `src-*` derivation takes the pinned artifact as a build
input, so there is nothing to look up and nothing to fall back to:

```nix
sources.perFamily.sans."Lilex.zip"   # a store path, already fetched and hashed
```

Phase 1 had to bridge this with a lookup by sha256, because every consumer was a
shell script that curled its own inputs — `tools/src-cache.sh` checked
`$FONTKIT_SRC_CACHE/by-sha256/` first and fell back to curl.

**That bridge still exists, for serif and nothing else**, until its Sarasa
toolchain moves into Nix. `just build serif` realises `.#source-cache` and
exports the variable; `FONTKIT_SRC_CACHE=off` falls back to curl, still
hash-gated, at the cost of re-downloading 300 MiB of Sarasa.

For the other six the fallback is gone, and so is what it was for. "Load-bearing
— a laptop with no Nix still builds" was true of a shell pipeline and is no
longer the deal: those families are derivations, so Nix is the requirement
rather than the accelerant.

`nix build .#source-cache` still produces the by-name / by-sha256 view:

```
by-sha256/<hex>            the bytes
by-name/<family>/<file>    the same bytes, human-navigable
manifest.tsv               sha256, kind, families, filename
sizes.tsv                  bytes per artifact
```

It is the GC root the CI source layer keeps, and it is how you find out what a
pin actually resolved to. It is no longer on any build path.

---

## 3. CI cache layering

GitHub Actions cache has two hard limits that decide the whole design:

* **10 GB per repository.** Not per workflow, not per branch.
* **7 days without a read and an entry is evicted.**

Eviction is oldest-first and silent. The symptom is not an error; it is a build
that quietly got slow again. So the strategy is layered by change rate, and
every run publishes its own numbers.

### Layers

| layer | key | measured size | why separate |
| --- | --- | --- | --- |
| sources | `hashFiles('*/font.toml')` | 447 MiB + 304 MiB Sarasa | biggest, changes least |
| toolchain | `hashFiles('flake.lock', 'flake.nix')` | measured per run | changes on flake bumps only |
| products | — | not cached yet | see below |

Sizes above are closure sizes measured with `nix path-info -S` on
aarch64-darwin. They are downloads, so they carry across platforms; the
toolchain closure does not, which is why the runner measures itself every run
(`tools/cache-report.sh`) and prints the result into the job summary. The number
that actually counts against the 10 GB ceiling is `/nix/store` on disk, not the
sum of the layers — `nix build` drags build dependencies in too — so that is
reported alongside.

`flake.nix` is in the toolchain key as well as `flake.lock`, because the
harfbuzz-with-cairo override lives in `flake.nix` and editing it rebuilds the
shell without moving the lock.

### Only the warmers save

Two small jobs (`sources`, `toolchain`) save. The seven family jobs restore both
layers and save nothing.

This is the single most important line in the workflow. Seven family jobs each
writing its own multi-gigabyte store snapshot would exhaust the repository
budget on one push and evict the layers that pay for themselves.

### What is deliberately not cached

**The products layer.** Phase 1 deferred this because the families built into
`<family>/work/` with shell scripts, and caching a work directory is exactly the
output-hash caching this repo must not do (§4). Phase 3 removed that objection —
every step is a derivation now, so a products layer would be store-shaped and
legitimate.

It is still not here, for a different and smaller reason: the six families'
closures do not fit the remaining budget alongside the source and toolchain
layers, and the numbers to decide what does fit come from the first green
seven-family run on this graph. Deciding before measuring is what produced the
"seven jobs each saving a snapshot" design this document exists to argue
against. When the numbers land, the natural cut is per-step rather than
per-family: `latin-prepared` is shared across regions and `cjk-prepared` across
profiles, so those two are worth far more per byte than a `packaged` zip.

**Prefix fallback on the source layer.** A partial source set from an older pin
list is worse than a clean fetch: it gets carried forward, counted against the
budget and never read.

The `cache-budget` job prints every cache entry, its size, and the total as a
percentage of 10 GiB, and warns above 80 %.

---

## 4. Cache by input hash, never by output hash

fontforge does not produce byte-reproducible output. It embeds its own
timestamps, and skia-pathops results differ across platforms. Nix's default
model — a derivation is identified by its *inputs* — is therefore the correct
one and the only safe one here.

**Do not enable content-addressed derivations for these packages.** Under CA
derivations Nix identifies outputs by their hash to decide what can be skipped
downstream; with a non-deterministic fontforge that produces spurious rebuilds at
best and an inconsistent store at worst.

This is also why the regression net (`tools/fingerprint.py`, Phase 0) compares
normalised advance/name/feature dumps rather than TTF sha256s.
