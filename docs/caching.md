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
(`nix/lib/manifest.nix`).

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

**That bridge is gone (KIT-280)**, along with `tools/src-cache.sh`,
`FONTKIT_SRC_CACHE` and serif's shell pipeline — its last user. All seven
families take their inputs as build inputs.

With it goes what it was for. "Load-bearing — a laptop with no Nix still builds"
was true of a shell pipeline and is no longer the deal: every family is a
derivation, so Nix is the requirement rather than the accelerant.

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

| layer | key | measured size (x86_64-linux runner) | why separate |
| --- | --- | ---: | --- |
| sources | digest of `tools/sources-cache-key.py` | **770 MB** closure / **~1.3 GB** store on disk (GHA entry ~715 MiB) | biggest, changes least |
| toolchain | `hashFiles('flake.lock', 'flake.nix')` | **1.7 GB** closure / **~2.1 GB** store (GHA entry ~612 MiB) | changes on flake bumps only |
| intermediates | digest of `tools/intermediates-cache-key.py` | measured every run (see job summary) | selective shared steps |
| products | — | not cached | see below |

Sources + toolchain numbers from run `30430655485` (2026-07-29), via
`tools/cache-report.sh`. The number that counts against the 10 GB ceiling is
what GHA stores (compressed), not the sum of closures — but `/nix/store` on disk
is what the action uploads, so both are reported.

`flake.nix` is in the toolchain key as well as `flake.lock`, because the
harfbuzz-with-cairo override lives in `flake.nix` and editing it rebuilds the
shell without moving the lock.

### Sources key is a projection, not `hashFiles('*/font.toml')`

A pure metadata bump of `[naming] version` across seven manifests used to
invalidate the entire sources layer (v1.0.0-beta.1 release: wall clock jumped
from ~14 m warm to ~25 m cold for the matrix, ~31 m for the release run). The
fetched bytes had not changed — only the key had.

`tools/sources-cache-key.py` projects only what the source layer realises:

* every `[sources.*]` table
* every `[nerd]` table (font-patcher pin)
* the fetchers themselves (`nix/sources/`, `nix/lib/manifest.nix`,
  `nix/source-cache.nix`, `tools/fetch_zip_member.py`)

CI hashes that projection into `nix-src-…`. A version-only bump leaves it — and
the ~715 MiB layer — untouched. (`hashFiles` is fixed at job start, so the
digest is computed in a step rather than via `hashFiles` on a generated file.)

### Only the warmers save

Three small jobs save: `sources`, `toolchain`, `intermediates`. The matrix cell
jobs restore all three and save nothing.

This is the single most important line in the workflow. Fourteen cell jobs each
writing its own multi-gigabyte store snapshot would exhaust the repository
budget on one push and evict the layers that pay for themselves.

**The release workflow restores too, and also saves nothing** (Phase 8,
KIT-283; simplified to a single tag-driven flow). `release-on-tag.yml` builds
from source, so it takes the same three layers with the same keys and the same
`CACHE_EPOCH` as `build-matrix.yml` — both must be bumped together or a release
silently misses. A cold release simply takes longer, which is the correct trade
for the rarer event.

### Layer 3 — selective intermediates (KIT-304)

Nix already skips untouched steps *inside* a run. Across runs the store was
empty every time, because family jobs save nothing. The full products layer does
not fit next to sources + toolchain; the cut that does is per-step, not
per-family:

| step | cold cost (measured) | closure | why cache |
| --- | ---: | ---: | --- |
| `latin-prepared-*` (casual × 2, handwriting × 5) | ~1 s each | a few MB of TTF | region-independent; one face serves every region cell |
| `serif-sarasa` (`nix build .#serif-sarasa`) | multi-minute on cold; serif job wall ~10–17 m | two TTFs (+ build-time npm deps GC'd after save) | only rebuilds when Sarasa pin / patches / CJK prep inputs move |

`nix build .#ci-intermediates` is the single GC root the warmer keeps
(`nix/intermediates.nix`). Its GHA key is the digest of
`tools/intermediates-cache-key.py`, which hashes the *real* inputs of those
steps (`sources` / `grid` / `calibration` / `options` / `build` from the three
manifests, the family nix files, prepare scripts, serif patches, flake pins) and
deliberately **omits** `[naming]` and `[merge]` so a version stamp does not
evict a multi-minute Sarasa build.

On a hit, cell jobs restore the store paths and `nix build` is a no-op for
those steps. On a miss, the intermediates job pays once; the cell jobs still
do not write.

**Steady-state budget estimate** (one entry per layer, GHA compressed sizes):

| layer | ~GHA size |
| --- | ---: |
| sources | 715 MiB |
| toolchain | 612 MiB |
| intermediates | ≪ 500 MiB (outputs are small; `gc-max-store-size-linux: 1.5G`) |
| **total** | **≲ 2 GiB** of the 10 GiB ceiling |

The 99 % reading on 2026-07-29 was not three full layers — it was **many
duplicate `nix-src-v1-*` / `nix-tool-v1-*` keys** left by pin bumps and PR
scopes. `CACHE_EPOCH: v2` starts a clean prefix; the cache-budget job also drops
orphan `v1` entries so they stop competing for the ceiling.

### What is deliberately not cached

**The products layer** (merged / nerd / packaged faces). Closures of the seven
families do not fit the remaining budget, and a `packaged` zip is worth far less
per byte than a shared intermediate: it is only reused by that one family on an
identical input set. Candidates that *might* join layer 3 later, once the
intermediates job prints their sizes:

* `cjk-prepared` for families that share it across profiles
* nothing else without a measured table

**Final product closures stay out** unless a future measurement shows they fit
without crowding sources + toolchain + intermediates.

**The region axis barely touches the source layer.** KIT-282 added three IBM
Plex Sans masters (TC / JP / KR, ~14 MiB each hinted) for sans, and nothing at
all for pixel — its four regional flavours are members of the archive it already
pulls. The `gc-max-store-size-linux: 3G` cap on the source layer is unchanged.

**Region / profile as matrix dimensions (KIT-305).** After Phase 7 the region
axis lived *inside* a family job: sans serially built sc/tc/jp/kr and was the
critical path at ~14.1 m. The CI matrix is now one job per
`(family, profile, region)` cell (14 jobs from `.#lib.matrix`), so those regions
run in parallel. That only stays free if the region-independent work is not
recomputed per job — which is why the intermediates layer (KIT-304) has to land
first: `latin-prepared` and `serif-sarasa` are warmed once, cell jobs restore
them. Weight is deliberately *not* a matrix axis: same-region weights share
Latin prep, and splitting them would amplify total CPU for almost no wall-clock
gain.

| path | before (family matrix) | after (cell matrix) |
| --- | ---: | ---: |
| critical path | sans ~14.1 m (4 regions serial) | serif ~10.2 m (Sarasa; lower with mid hit) |
| cell jobs | 7 | 14 |
| timeout | 300 m (no measured number) | 60 m |

Cell jobs still save no cache; the wall-clock win is parallelism, not a new
layer.

**Prefix fallback on the source layer.** A partial source set from an older pin
list is worse than a clean fetch: it gets carried forward, counted against the
budget and never read.

The `cache-budget` job prints every cache entry, its size, and the total as a
percentage of 10 GiB, and warns above 80 %.

### Binary cache tradeoff (not implemented)

GHA's 10 GB ceiling is what forced "family jobs save nothing" in the first
place. Selective intermediates reclaim the wins that fit. A hosted Nix binary
cache (cachix / attic) would store *every* derivation output with no 10 GB
cap, at the cost of an account, a secret, and a bill.

| option | what you get | what it costs |
| --- | --- | --- |
| **Selective GHA layers (current)** | sources + toolchain + chosen intermediates across runs | free; 10 GB ceiling; must pick steps by size |
| **Binary cache** | every store path, including `merged` / `nerd` / `packaged` | hosted service + secret in CI; ongoing storage/bandwidth |

**Decision: stay on selective GHA layers for now.** The measured steady state is
under ~2 GiB with layer 3 in place. Revisit binary cache only if a future
measurement shows a step that is both (a) multi-minute cold and (b) too large
or too numerous to fit the remaining budget — write the numbers here before
wiring anything up.

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
