# Build toolchain

Phases 0-3 of the pipeline modernisation plan (KIT-263). Phase 0 (KIT-274)
pinned the toolchain and built a regression net **before** any of the 14k lines
got refactored; it changed no build logic. Phase 1 (KIT-275) moved source
fetching into Nix and fixed the derivation granularity later phases build on.
Phase 2 (KIT-276) then collapsed the 17 duplicated per-family scripts into
[`lib/fontkit`](#fontkit-the-shared-build-steps), with every per-family
behavioural difference expressed as a flag so the products do not move.
Phase 3 (KIT-277) turned each remaining build step into its own derivation and
deleted the shell orchestration — see
[The build graph](#the-build-graph).

## Quick start

```bash
just dev              # enter the pinned toolchain shell
just build sans       # nix build .#sans, materialised into sans/out
just gate sans        # the family's own 2:1 / EAW / Nerd / feature gate
just release sans     # the release zip (depends on the gate passing)
just verify sans      # diff the products against the committed fingerprints
just fingerprint sans # rewrite the baseline (only when a change is intended)
just steps sans       # the build steps this family has
just step sans merged-Bold   # build one step in isolation
just test             # fontkit unit tests — seconds, no font build
just sources          # realise every pinned upstream input (Phase 1)
just graph            # what makes each build step rebuild (Phase 1)
```

Source fetching, derivation granularity and the layered CI cache have their own
document: [`caching.md`](caching.md).

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
- **`FONTKIT_PYTHON`.** Only serif reads it now — its `common.sh` uses it
  instead of building a venv. The six derivation families never ask the
  question: their interpreter is a build input
  (`nix/families/support.nix`), which is also why the devShell's wider set
  (Pillow, uharfbuzz, numpy — for the diagnostics) cannot leak into a product.

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

The first CI run looked like it answered the open question — all seven families
built cleanly on `x86_64-linux` and all seven products differed from baselines
generated on `aarch64-darwin`, so the conclusion recorded here was "the build is
not reproducible across platforms". `pixel` was cited: **46661 glyphs on Linux
against darwin's 46552**, from the same pinned fontforge and the same pinned
`FontPatcher.zip`.

**That was the wrong conclusion, and it was not measuring platforms.** It was
measuring two patchers. `pins.env` set `NERD_PATCH_METHOD=auto`, which picks the
`nerdfonts/patcher` container whenever docker is present; GitHub runners have
docker and the maintainer's Mac has it too, but the image is broken on `arm64`
and fell back to the pinned local patcher there. So Linux was patched by the
container (font-patcher 4.26.0, built from master) and darwin by
`FontPatcher.zip` v3.4.0 (font-patcher 4.20.3) — 15 months of glyph additions
apart.

Pinning the commit the container was built from closes it: the same `pixel`
product built on darwin from that pin has **46661 glyphs**, matching the number
that was attributed to Linux, with identical `glyphorder`, `cmap` and advances.
What is left between the two is `head.flags` / `lowestRecPPEM` — which the
container was *failing* to copy, because it bind-mounts its input `/in:ro` and
hits exactly the `PermissionError` described under [One thing the sandbox
changed](#one-thing-the-sandbox-changed) — and a two-point `maxp.maxPoints`
difference in the outlines.

So the toolchain pin buys more than this document used to claim. What remains
genuinely open is that last outline delta; a baseline is still only meaningful
relative to the platform that produced it, and
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

## fontkit: the shared build steps

Five scripts existed in 17 copies under `<family>/scripts/`. Most copies were
byte-identical; serif's and pixel's had drifted, so a fix landed in one copy and
the other three kept the bug. They now live once, in `lib/fontkit/`, and run as
`python3 -m fontkit.<module>`:

| module | replaces | families |
| --- | --- | --- |
| `fontkit.fix_nerd_widths` | `fix-nerd-widths.py` ×4 | pixel rounded sans typewriter |
| `fontkit.fix_terminal_metrics` | `fix-terminal-metrics.py` ×5 | + serif |
| `fontkit.verify2to1` | `verify-2to1.py` ×4 | all seven |
| `fontkit.narrow_symbol_widths` | `narrow-symbol-widths.py` ×4 | rounded sans serif typewriter |
| `fontkit.rename_nerd_family` | `rename_nerd_family.py` ×4 | pixel rounded sans serif typewriter |
| `fontkit.measure` / `fontkit.embolden` | `serif/tools/*` | six families imported them by hardcoded path |

`nix/fontkit.nix` packages the tree as a `buildPythonPackage`, which is what the
per-step derivations depend on — they have no checkout to point at. It also
installs a `fontkit` console script, so a step is `fontkit merge …` rather than
`"${PY}" -m fontkit.merge_radon_wenkai …` with 30 lines above it working out
what `PY` should be. Both spellings work; the module form is what the unit tests
call.

Phase 3 added four more modules and promoted three that were still family-local:

| module | replaces | note |
| --- | --- | --- |
| `fontkit.nerd_patch` | `0N-nerd-patch.sh` ×4 | 130-141 lines each, differing only in an input glob |
| `fontkit.package` | `package-release.sh` ×6 | deterministic zip; the README body is rendered by Nix from the same pins the build read |
| `fontkit.cli` | `common.sh` ×7 | the dispatch table those 104-line files were building up to |
| `fontkit.prepare_cjk` | `handwriting/scripts/prepare_cjk.py` | casual reached across for it |
| `fontkit.merge_radon_wenkai` | `handwriting/scripts/merge_radon_wenkai.py` | casual reached across for it |
| `fontkit.expand_ligatures` | `serif/scripts/expand-default-ligatures.py` | handwriting reached across for it |

### The differences that survived as flags

Phase 2's completion criterion is that all seven fingerprints stay put, so the
drifted copies could not simply be dropped in favour of the majority. Three
genuine behaviour differences became flags:

| flag | who passes it | what it does |
| --- | --- | --- |
| `narrow_symbol_widths --protect-ambiguous` | serif | never narrows an outline also reachable from an `EAW=A` codepoint |
| `narrow_symbol_widths --widen-shared skip` | serif | leaves a shared `W`/half outline alone instead of forking a full-width copy |
| `verify2to1 --profile dense` | serif handwriting casual | denser CJK sampling, four more bracket marks, Nerd-range (not whole-PUA) icon scan, no `xAvgCharWidth` check |

There was a fourth, `fix_terminal_metrics --keep-bbox`, and its history is worth
keeping: serif rewrote `head.xMin/xMax` from half/full-advance glyphs only, and
disabled `TTFont.recalcBBoxes` so the value survived the save. The other four
families ran the same computation and let fontTools overwrite it — a value
computed and discarded on every build.

**Both sides are now gone (KIT-284).** The bbox was a workaround for a "large
empty band on the right of the terminal" report that turned out to be a terminal
bug, not a font one, and the table it wrote is non-conformant: OpenType says
`head`'s bbox covers *all* glyphs. Deleting it removes the dead computation from
four families and one non-conformant table from serif's products —
`test_head_bbox_still_covers_every_glyph` fails if it comes back. Do not
reintroduce it without a font-side reproduction.

`lib/tests/` pins each of these against synthetic fonts; `just test` runs them
in about a second, and `nix flake check` runs them again against the installed
package.

### The interpreter's Unicode version is a build input

Every narrow/widen decision reads `unicodedata.east_asian_width`, and
`unicodedata` ships **with the interpreter**. A nixpkgs bump therefore moves the
Unicode version under the build: U+2630 ☰ is `EAW=N` through Unicode 15.1 and
`W` from 16.0, so the same source font gains or loses a full-cell glyph
depending on which Python built it. This is a second, less obvious reason the
devShell pins `python3` — and `just update` is a deliberate act that must be
followed by a rebuild and a fingerprint diff.

`lib/tests/test_eaw_assumptions.py` asserts the width class of every codepoint
the fixtures rely on, so a pin bump that moves one fails with the version in the
message instead of as a confusing behavioural assertion.

## The build graph

Phase 3 (KIT-277). Every step of every family except serif is a derivation, and
the shell that used to sequence them is gone: 6 × `common.sh`, 6 × `build.sh`,
6 × `package-release.sh`, the numbered step scripts and `tools/build-family.sh` —
about 2,900 lines. `tools/src-cache.sh` stays for serif alone, which still curls
its own inputs; see [`caching.md`](caching.md).

### What a step is

`nix/granularity.nix` (Phase 1) already said what the steps are and which axes
each may depend on. Phase 3 builds against it rather than beside it:
`granularity.mkStep` names the derivation from the contract and refuses an axis
the step did not declare, so `latin-prepared` cannot quietly acquire a `region`
and stop being shared. The resulting names are the cache keys, and they are
greppable:

```
src-latin-sans-Bold
cjk-prepared-sans-sc-Bold
merged-sans-coding-sc-Bold
nerd-sans-sc-Bold
packaged-sans-coding-sc-Regular-ttf
```

`just steps sans` lists them; `just step sans merged-Bold` builds one.

### Which family has which steps

Not every family uses every step, and that is the point of a vocabulary rather
than a fixed pipeline:

| | src-latin | src-cjk | latin-prepared | cjk-prepared | merged | nerd | packaged |
| --- | --- | --- | --- | --- | --- | --- | --- |
| casual | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ |
| handwriting | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ |
| pixel | | ✓ | | | ✓ | ✓ | ✓ |
| rounded | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ |
| sans | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ |
| typewriter | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ |

handwriting and casual carry their Nerd icons in the upstream Latin face, so
they have no `nerd` step. pixel's Latin and CJK arrive in the same upstream
file, so it has no Latin side to prepare separately. sans, rounded and
typewriter scale their Latin inside the merge engine — Phase 5 is where that
gets pulled apart.

### The merge runs once per weight

The merge engines write both faces from both input pairs in a single pass, so
each weight's derivation runs the merge and keeps its own face. That costs a
second merge and buys a per-weight cache entry: a Bold-only pin change stops
rebuilding Regular. A step that took both weights would have had to declare no
`weight` axis at all, which is a false statement about what makes it rebuild.

### The coupling that stopped being possible

A derivation sees only what it was given. These are the reaches Phase 3 removed,
and none of them needs a CI grep to stay removed:

```
sans/scripts/02-merge.sh             → ${REPO_ROOT}/serif/tools/embolden_cjk.py
rounded/scripts/02-prepare-cjk.sh    → same
typewriter/scripts/02-prepare-cjk.sh → same
handwriting/scripts/06-verify.sh     → ${REPO_ROOT}/serif/scripts/verify-2to1.py
casual/scripts/common.sh             → SERIF_TOOLS + HANDWRITING_SCRIPTS
sans/scripts/04-verify.sh:48         → sys.path.insert(0, os.environ["SERIF_TOOLS"])
casual/scripts/05-verify.sh          → if [[ -f serif/… ]] elif [[ -f rounded/… ]]
```

That last one is the shape worth remembering: a build step doing filesystem
archaeology at runtime to find a script it was not given.

### The docker path is gone

Four families patched Nerd icons through `NERD_FONTS_DOCKER_IMAGE` when docker
happened to be installed, and through local fontforge when it was not — chosen
at runtime, per machine, per run, with `NERD_PATCH_METHOD=auto` as the default.
Two runners could therefore produce two different fonts and nothing in the
pipeline would say so, which is precisely what the fingerprint net exists to
catch. fontforge comes from nixpkgs now and a build sandbox cannot reach a
docker socket anyway. serif's copy went with them even though serif is otherwise
untouched. What is left in the tree is prose: this section, one note in
`pixel/README.md` and the module docstring of `fontkit.nerd_patch`. Deleting the
explanation too is how the branch grows back.

The same reasoning removed the other "look around and hope" branches: the
`7zz` → `7z` → `py7zr` ladder, `uv` → `python -m venv` → `pip`, and
`find … | head -1` for an archive whose layout is pinned by its hash.

### One thing the sandbox changed

`font-patcher` reopens its **source** file read-write near the end of a run, to
copy `head.flags`, `head.lowestRecPPEM` and `OS/2.xAvgCharWidth` across to the
patched output. Patching straight out of a store path makes that raise, and the
patcher swallows it as `ERROR: Can not handle font flags (PermissionError…)` and
carries on with those three fields unset — two of which are in the fingerprint.
`fontkit.nerd_patch` therefore stages its input into a writable directory first,
which is what the old shell got for free by patching a file in `<family>/out`.

It is worth noting where that error surfaced: the products still built, the gate
still passed, and only a fingerprint diff against the pre-change build named it.

### Verification is a build input

Each family's gate is a `<family>-verify` derivation that reads the products and
writes nothing, and `packaged` depends on it. A release archive whose gate is
red does not exist, rather than existing next to a check somebody was supposed
to run. The gates are deliberately **not** in `nix flake check`: `just check` is
the seconds-long gate a contributor runs before pushing, and six font builds
inside it would stop anyone running it.

## CI

`.github/workflows/build-matrix.yml` runs the fontkit unit tests first — the
shared steps are the one thing that can break all seven families at once, and a
three-hour font build is not a feedback loop for that — then builds all seven
families from source on every push and PR. Before this, `release-nfm.yml` was the only workflow: serif
only, and it does not build from source — it downloads the previous tag's
products and post-processes them. Six families had no automated verification.

Per-step wall-clock used to be collected by `tools/build-family.sh` into a TSV
and summarised in a job. That job is gone: `nix build -L` prints per-derivation
timing already, and — more to the point — Nix skips the steps a change did not
touch, so a table of "how long every step took" no longer describes what a run
actually does. What a run does is now visible in which derivations it built.

Cache layering has its own document: [`caching.md`](caching.md).
