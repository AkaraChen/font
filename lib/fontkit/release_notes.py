#!/usr/bin/env python3
"""Release notes for one (family, profile, region) cell, from `font.toml`.

The old `release-nfm.yml` wrote its notes as a heredoc: a hand-maintained
markdown table of file names, a hand-typed pin list, and a "Changes" section
about a ligature fix from three releases earlier. Every fact in it was a second
copy of something `font.toml` already stated, and the copies had drifted — the
pins it advertised were not the pins the products were built from, because it
did not build the products at all.

So these notes are generated from the same manifest the build reads. Four
sections earn their place:

* **What is in the release** — the family name, the weights, the formats, and
  what each format actually is. TTF and WOFF2 are the same outlines; OTF is not,
  and a reader deciding which file to install should be told that in the notes
  rather than in a commit message.
* **The grid** — a 2:1 dual-width coding face is a promise about terminal cells,
  and it is the promise people pick these fonts for.
* **Where it comes from** — after the AKR rename the family name carries no
  donor's name, so the release notes are the main place attribution is visible.
  The OFL asks for the credit; this is where it goes.
* **Migration** — the rename broke every editor config that named an old family
  (KIT-282). A release that ships a renamed product and does not say so reads to
  its users as "the font stopped working".

Usage
  fontkit release-notes --manifest sans/font.toml --profile coding \\
      --region sc --version 0.2.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontkit.manifest import Manifest, load_manifest, naming_for

REPO = "https://github.com/AkaraChen/font"

# What each format *is*, in the reader's terms rather than the build's. The
# distinction is not pedantry: an OTF of these products is unhinted and its
# outlines are a refit, so someone installing one for a terminal should know
# they are not getting the file the family was designed as.
FORMAT_NOTES = {
    "ttf": "TrueType outlines, hinting intact. The product the family is designed as — install this one unless you have a reason not to.",
    "woff2": "The same TrueType outlines in a Brotli container, for `@font-face` on the web. Byte-identical glyf data to the TTF; verified per release (`fontkit verify-formats`).",
    "otf": "PostScript/CFF outlines, converted from the TrueType ones with qu2cu. The curves are refit within 1 font unit and TrueType hinting is dropped, so this is the same design and not the same file — for print and desktop publishing workflows that want CFF.",
    "woff": "The same TrueType outlines in the older WOFF container.",
}

ROLE_LABEL = {
    "latin": "Latin",
    "cjk": "CJK",
    "donor": "donor",
    "tool": "tool",
}


def _pin(source) -> str:
    """The most specific thing the manifest pinned, spelled for a human."""
    if source.commit:
        short = source.commit[:12]
        return f"`{source.ref or source.version or short}` ({short})" if (
            source.ref or source.version
        ) else f"`{short}`"
    return f"`{source.ref or source.version}`"


def _sources_section(manifest: Manifest) -> list[str]:
    lines = [
        "## Where it comes from",
        "",
        manifest.naming.rfn_note,
        "",
        "| role | upstream | pin |",
        "| --- | --- | --- |",
    ]
    for name, source in manifest.sources.items():
        lines.append(
            f"| {ROLE_LABEL.get(source.role, source.role)} | "
            f"[{name}]({source.repository}) | {_pin(source)} |"
        )
    if manifest.nerd:
        lines.append(
            f"| icons | [nerd-fonts](https://github.com/ryanoasis/nerd-fonts) | "
            f"`{manifest.nerd.version}` ({manifest.nerd.commit[:12]}) |"
        )
    lines += [
        "",
        "Donors are credited in name ID 5 and name ID 10 of every product, in the "
        "bundled `README.txt`, and here. Redistributed under the SIL OFL 1.1.",
        "",
    ]
    return lines


def _migration_section(manifest: Manifest, names, region: str) -> list[str]:
    former = names.former_family
    if not former:
        return [
            "## Migration",
            "",
            f"Nothing to migrate: the `{region.upper()}` product has never shipped "
            "under another name.",
            "",
        ]
    return [
        "## Migration — the family was renamed",
        "",
        f"**`{former}` → `{names.family}`.** This is a breaking change with no "
        "in-font compatibility alias. An editor, terminal or CSS rule configured "
        f"with `{former}` will not find this font; it will silently fall back to "
        "your default monospace, which looks like the font broke rather than like "
        "it was renamed.",
        "",
        f"* Update your config to `{names.family}`.",
        f"* File stems follow: `{former.replace(' ', '')}-Bold.ttf` → "
        f"`{names.stem}-Bold.ttf`.",
        "* **Uninstall the old family.** Nothing stops both from being installed, "
        "and while they coexist a font picker shows two entries that draw the "
        "same outlines.",
        "",
        "The old names carried upstream Reserved Font Names in name ID 1, which "
        "the OFL does not permit a redistributed derivative to do. Attribution "
        "moved to name IDs 5 and 10 — see the table above. Full note: "
        f"[docs/naming-migration.md]({REPO}/blob/main/docs/naming-migration.md).",
        "",
    ]


def render(
    manifest: Manifest,
    profile: str,
    region: str,
    version: str,
    weights: list[str],
    formats: list[str],
) -> str:
    names = naming_for(manifest, profile, region)
    grid = manifest.grid
    version = version.lstrip("v")

    lines = [
        f"## {names.family} v{version}",
        "",
        f"Built from source at this commit — `nix build .#{manifest.family}-{profile}-{region}-release`.",
        "",
        "## What is in the release",
        "",
        "| | |",
        "| --- | --- |",
        f"| family | `{names.family}` |",
        f"| PostScript / file stem | `{names.stem}` |",
        f"| profile | `{profile}` — "
        + (
            "terminal and editor face: strict dual-width cell, Nerd icons"
            if profile == "coding"
            else "reading face: no terminal cell claim, no Nerd icons"
        )
        + " |",
        f"| region | `{region.upper()}` |",
        f"| weights | {', '.join(w.capitalize() for w in weights)} |",
        f"| formats | {', '.join(f'`{f}`' for f in formats)} |",
        "",
    ]

    lines += ["### Formats", ""]
    for fmt in formats:
        lines.append(f"* **`.{fmt}`** — {FORMAT_NOTES.get(fmt, 'see font.toml')}")
    lines += [
        "",
        f"The `{names.stem}-{version}.zip` carries every file above plus the "
        "licences and a `README.txt`.",
        "",
        "## Grid",
        "",
        f"* Latin advance **{grid.en_adv}** / CJK advance **{grid.cjk_adv}** at "
        f"UPM **{grid.upm}**"
        + (" — strict 2:1, so terminal cells line up" if profile == "coding" else ""),
    ]
    metrics = manifest.metrics.get(profile)
    if metrics:
        lines.append(
            f"* Line box: hhea {metrics.hhea_ascent} / {metrics.hhea_descent}"
            + (
                f", typo {metrics.os2_typo_ascender} / {metrics.os2_typo_descender}"
                if metrics.os2_typo_ascender is not None
                else ""
            )
        )
    lines.append("")

    lines += _sources_section(manifest)
    lines += _migration_section(manifest, names, region)

    unsupported = [
        f"* `{entry.axis}` = {', '.join(entry.values)} — {entry.reason}"
        for entry in manifest.build.unsupported
    ]
    if unsupported:
        lines += [
            "## Not in this release, on purpose",
            "",
            *unsupported,
            "",
        ]

    lines += [
        "## Verify",
        "",
        "```",
        f"nix build .#{manifest.family}-verify   # the family's own gate: cell, EAW, icons, features",
        f"just verify {manifest.family}          # products vs the committed fingerprint baseline",
        "```",
        "",
        f"Pins, grid and matrix: [`{manifest.family}/font.toml`]"
        f"({REPO}/blob/main/{manifest.family}/font.toml).",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--region", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument(
        "--weights",
        help="comma-separated override; defaults to the matrix entry for this cell",
    )
    ap.add_argument("--formats", help="comma-separated override; same default")
    ap.add_argument("--out", type=Path, help="write here instead of stdout")
    args = ap.parse_args(argv)

    manifest = load_manifest(args.manifest)
    entries = [
        entry
        for entry in manifest.build.matrix
        if entry.profile == args.profile and args.region in entry.regions
    ]
    if not entries:
        print(
            f"error: {manifest.family} declares no ({args.profile}, {args.region}) "
            f"cell in [[build.matrix]]",
            file=sys.stderr,
        )
        return 2
    entry = entries[0]

    weights = args.weights.split(",") if args.weights else list(entry.weights)
    formats = args.formats.split(",") if args.formats else list(entry.formats)
    for name, requested, declared in (
        ("weights", weights, entry.weights),
        ("formats", formats, entry.formats),
    ):
        unknown = sorted(set(requested) - set(declared))
        if unknown:
            print(
                f"error: {name} {unknown} are not declared for this cell "
                f"(declared: {sorted(declared)})",
                file=sys.stderr,
            )
            return 2

    text = render(manifest, args.profile, args.region, args.version, weights, formats)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(args.out)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
