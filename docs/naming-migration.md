# Migrating to the AKR family names

**This is a breaking change with no in-font compatibility alias.**

Since Phase 8 (KIT-283) the release notes carry this automatically: each
family's `[naming.former]` table records what that cell shipped as before the
rename, and `fontkit release-notes` emits the migration section for a product
that really had a predecessor — and a "this one is new" line for `TC` / `JP` /
`KR`, which never existed under another name. The table below is the source it
was transcribed from and the long-form explanation.

Every family was renamed in one go (KIT-282). An editor, terminal or CSS rule
configured with an old family name will not find the new font — it will silently
fall back to your default monospace, which usually looks like "the font stopped
working" rather than like a name change.

## What to change

| old family | new family |
| --- | --- |
| `SarasaNZSSlab NFM` | `AKR Slab SC NFM` |
| `LilexSansSC NFM` | `AKR Sans SC NFM` |
| `IosevkaCurlyRHR NFM` | `AKR Round SC NFM` |
| `CourierPrimeZhuque NFM` | `AKR Type SC NFM` |
| `FusionPixel12 NFM` | `AKR Pixel SC NFM` |
| `RadonWenKai NFM` | `AKR Hand SC NFM` |
| `RadonWenKai Text` | `AKR Hand SC Text` |
| `RecursiveYozai Dual` | `AKR Casual SC Dual` |

PostScript names and file stems follow the family with the spaces removed:
`LilexSansSCNFM-Bold.ttf` → `AKRSansSCNFM-Bold.ttf`.

**Uninstall the old fonts.** Nothing prevents both from being installed at once,
and while they coexist a picker will show two entries that draw the same
outlines.

## Why

The old names carried upstream **Reserved Font Names** — Iosevka, Monaspace,
Radon, Lilex, Plex, Recursive, Yozai, LXGW, Sarasa, Courier Prime, Zhuque,
Fusion Pixel — in name ID 1. The SIL OFL 1.1 does not permit a redistributed
derivative to use its donors' reserved names, so these products could not have
been published as they were. Attribution is not lost: it moved to name ID 5
(version string), name ID 10 (description), each family's README and these
notes, which is where the OFL expects it.

The scheme is **`AKR <Style> <Region> <Variant> [<Weight>]`**, and the region
segment is the other half of the change: the same build now produces
`AKR Sans SC NFM`, `AKR Sans TC NFM`, `AKR Sans JP NFM` and `AKR Sans KR NFM`
from four CJK masters and one Latin build.

## Old releases are not rewritten

Every tag published before this one keeps its old assets under their old names.
Pinning an old tag is a supported way to stay put; there is just no upgrade path
that leaves a font configuration untouched.

## If you use a three-weight family

`AKR Hand SC Text` ships Light / Regular / Bold. Windows' legacy name ID 2 only
understands `Regular` / `Italic` / `Bold` / `Bold Italic`, so the Light is
grouped through name IDs 16/17 and appears to name-ID-1/2-only consumers as a
separate family called `AKR Hand SC Text Light`. That is the standard
arrangement and is deliberate — see the naming section of the root
[`README.md`](../README.md).
