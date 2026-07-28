# Build toolchain (Phase 0)

Phase 0 of the pipeline modernisation plan (KIT-263 → KIT-274). It pins the
toolchain and builds a regression net **before** any of the 14k lines get
refactored. **No build logic changed in this phase.**

## Quick start

```bash
just dev              # enter the pinned toolchain shell
just build sans       # run sans/scripts/build.sh in it, one step at a time, timed
just verify sans      # diff the products against the committed fingerprints
just fingerprint sans # rewrite the baseline (only when a change is intended)
just timings sans     # per-step wall-clock from the last build
```

`nix` needs flakes enabled. The `just` recipes pass
`--extra-experimental-features 'nix-command flakes'` themselves, so a fresh
checkout works without editing `nix.conf` first.

## What the devShell pins

Everything the build previously discovered with `need_cmd`, or just called and
hoped for. Before this, a build's correctness depended on what happened to be
installed on the machine running it.

| | |
| --- | --- |
| system | `curl` `git` `quilt` `unzip` `zip` `p7zip` `fontforge` `ttfautohint` `nodejs` `harfbuzz` `afdko` `just` `jq` |
| python | `fonttools` `brotli` `skia-pathops` `Pillow` `freetype-py` `numpy` `uharfbuzz` `wcwidth` |

Three things worth knowing:

- **`afdko` was never in any `need_cmd` list.** Sarasa's `verdafile.mjs` calls
  `otc2otf` and `otf2ttf` during source prep, and its own `check-env.mjs` only
  `console.error`s when they are missing. serif built at all because the
  maintainer's machine happened to have AFDKO installed.
- **`hb-view` needs a harfbuzz override.** nixpkgs hard-disables cairo in
  harfbuzz, which drops `hb-view` — the one harfbuzz binary
  `pixel/scripts/preview.sh` calls. Without the override in `flake.nix` the
  shell silently falls through to the host's `hb-view` (homebrew's, on the
  maintainer's Mac), which is exactly the failure this phase exists to remove.
- **`FONTKIT_PYTHON`.** The devShell exports it, and each family's `common.sh`
  uses it instead of building a venv and `pip install`-ing. Outside the shell
  the old venv path is unchanged, so nothing breaks for someone not using Nix.

nixpkgs is pinned to the `nixos-25.11` release rather than unstable — this is a
toolchain pin, not a place to chase upstream, and unstable currently carries an
unbuilt nodejs that would make every cold shell compile Node from source.

## warn-then-continue → hard failure

Three places logged a warning and carried on, producing a build that "succeeded"
with wrong or missing products:

| where | was | now |
| --- | --- | --- |
| `serif/scripts/04-build.sh` | `ttfautohint` missing → warning | `need_cmd ttfautohint` |
| Sarasa `check-env.mjs` | `otc2otf`/`otf2ttf` missing → `console.error` | `need_cmd otc2otf` / `need_cmd otf2ttf` as a preflight in `04-build.sh`, before Sarasa is invoked |
| `*/scripts/common.sh` ×5 | Pillow / freetype-py fail to install → warning, sample render skipped | `die` |

The AFDKO check lives in our `04-build.sh` rather than as a quilt patch against
Sarasa's `check-env.mjs`: it fails earlier, and it does not drift when the
pinned Sarasa commit moves.

One related soft-skip is **not** fixed here, because it is outside this issue's
scope: `serif/scripts/05-nerd-patch.sh` silently skips the family rename when it
cannot resolve a Python interpreter. Under the devShell `FONTKIT_PYTHON` is
always set, so the branch cannot be taken — but the branch is still there.

## Fingerprints: the regression net

`out/**/*.ttf` hashes are useless as a baseline — fontforge embeds timestamps
and is not byte-reproducible, so a raw hash would go red on rebuilds and get
ignored within a week. `tools/fingerprint.py` instead dumps a normalised view
and drops everything that carries a clock (`head.created`, `head.modified`,
`head.checkSumAdjustment`).

Baselines live in `fingerprints/<family>/`, one `.fp` per product plus an
`INDEX`, and cover:

- `name` table in full — every record, sorted
- **per-glyph advances in full**, plus an advance histogram. This is what the
  refactor actually moves (2:1 cell widths, EAW corrections, centring), so a
  regression here has to be locatable by glyph name.
- `head` / `hhea` / `OS/2` / `post` / `maxp` metric and flag fields
- `GSUB` / `GPOS` / `GDEF` structure: scripts, langsys, feature tags, lookup
  types and counts
- `cmap` and glyph outlines as **digests** — full detail would add megabytes per
  font to the repo. When a digest goes red, re-run both sides with `--full` to
  find which codepoint or glyph moved. CI uploads every run's products, so the
  "before" side exists for any recent build.

`SOURCE_DATE_EPOCH=0` is exported during builds. fontTools honours it for
`head.modified`; fontforge ignores it, which is why the net does not depend on
byte reproducibility in the first place.

### Why they are committed as text

They are build products, so the obvious move is to store them as binary and stop
GitHub rendering a diff on every update. That was measured and rejected:
compressed streams do not delta-compress, so five successive baseline updates
grow the repo **472K as `.fp.gz` versus 200K as text**. Storing them binary
hides the diff at 2.4x the long-term cost, and makes the baseline unreadable
even locally.

`.gitattributes` marks `fingerprints/**` as `linguist-generated` instead: GitHub
collapses them in the diff view (expandable on click) and drops them from the
language stats, while `git diff`, `git blame` and delta compression all keep
working. To hide them outright rather than collapse, change that line to
`fingerprints/** -diff` — at the cost of not being able to review an intentional
baseline change, which is what the normalised text format exists for.

### Baseline provenance: CI is the only authority

The first CI run answered the open question, and the answer was no: **the build
is not reproducible across platforms.** All seven families built cleanly on
`x86_64-linux`, and all seven products differed from baselines generated on
`aarch64-darwin`.

`pixel` localises it. Its fontTools-only intermediate is identical on both
platforms; its fontforge-patched product is not — Linux emits **46661 glyphs
against darwin's 46552**, from the same pinned fontforge, the same pinned
`FontPatcher.zip`, the same arguments and the same input font. `casual` and
`handwriting` have no fontforge step and still differed, so fontforge is not the
only source; `skia-pathops` is the obvious suspect for the CJK embolden, though
that is inferred from which families failed rather than diagnosed.

So the toolchain pin buys reproducibility *on* a platform, not *across* them,
and a baseline is only meaningful relative to the platform that produced it.
`x86_64-linux` on GitHub Actions is the canonical one. Baselines are bootstrapped
from the `fingerprints-<family>` artifact, which every run uploads regardless of
verdict — see [`../fingerprints/README.md`](../fingerprints/README.md).

Each `fingerprints/<family>/PROVENANCE` records the system and nixpkgs revision
its baseline came from, so a mismatched platform is visible rather than
mysterious.

Which platform is *correct* is unresolved. Linux produces the more complete Nerd
set for `pixel`, which points at darwin's patch being the deficient one — and
therefore at a Mac maintainer's local builds not matching what gets released.
That predates Phase 0; Phase 0 only made it visible.

## CI

`.github/workflows/build-matrix.yml` builds all seven families from source on
every push and PR. Before this, `release-nfm.yml` was the only workflow: serif
only, and it does not build from source — it downloads the previous tag's
products and post-processes them. Six families had no automated verification.

Every step is timed, per family, into the job summary and an artifact. Those
numbers are the input KIT-265 needs: the plan currently has no measured
wall-clock data, only script reading.

Binary cache and GHA cache layering are deliberately **not** here. That is
KIT-265, and it needs these timings before it can pick a strategy against GHA
cache's 10 GB / 7-day limits.
